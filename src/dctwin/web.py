from __future__ import annotations

import argparse
import json
import os
import shutil
import tempfile
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from time import perf_counter
from typing import Any
from urllib.parse import unquote
from zoneinfo import ZoneInfo

from dctwin import __version__
from dctwin.adapters import AdapterRegistry, DocxCvAdapter, PdfCvAdapter, adapt_cv_text
from dctwin.agent import SourceAdapterAgent
from dctwin.auth import LocalAccountRepository, collect_email_candidates, normalize_email
from dctwin.foundry import FoundryExtractionTwinProvider, FoundryTwinProvider
from dctwin.io import load_json, write_json
from dctwin.reconciliation import ReconciliationAgent
from dctwin.validation import validate_source_document, validate_twin


MAX_UPLOAD_BYTES = 15 * 1024 * 1024
MAX_TEXT_BYTES = 1 * 1024 * 1024
SESSION_DIR = ".dctwin-local"
SESSION_FILE = "session-state.json"
CACHE_DIR = "cache"
ACCOUNT_FILE = "accounts.json"
LOG_DIR = "logs"
CACHE_CONTRACT_VERSION = "cv_extraction_v8"


def _project_root() -> Path:
    for candidate in [Path.cwd(), *Path(__file__).resolve().parents]:
        if (candidate / "src/web/index.html").is_file():
            return candidate
    raise RuntimeError("Run the local UI from the repository root")


def _foundry_configured() -> bool:
    return bool(
        os.environ.get("FOUNDRY_PROJECT_ENDPOINT")
        and os.environ.get("DCTWIN_MODEL_DEPLOYMENT")
    )


def _health_payload() -> dict[str, Any]:
    return {
        "status": "ok",
        "app_version": __version__,
        "mode": "local",
        "formats": ["pdf", "docx", "pasted_text"],
        "foundry": "ready" if _foundry_configured() else "not_configured",
        "model_path": os.environ.get("DCTWIN_MODEL_PATH", "staged_extraction"),
    }


def _contracts() -> dict[str, dict[str, Any]]:
    root = _project_root()
    return {
        "source": load_json(root / "schemas/source_document.schema.json"),
        "enrollment": load_json(root / "schemas/enrollment_candidates.schema.json"),
        "twin": load_json(root / "schemas/digital_career_twin.schema.json"),
        "catalog": load_json(root / "catalogs/tag_catalog.json"),
    }


def _session_path() -> Path:
    return _project_root() / SESSION_DIR / SESSION_FILE


def _local_state_path() -> Path:
    return _project_root() / SESSION_DIR


def _persistent_state_path() -> Path:
    configured = os.environ.get("DCTWIN_STATE_DIR")
    if configured:
        return Path(configured).expanduser()
    return Path.home() / ".dctwin"


def _account_repository() -> LocalAccountRepository:
    return LocalAccountRepository(_persistent_state_path() / ACCOUNT_FILE)


def _load_session() -> dict[str, Any]:
    path = _session_path()
    if not path.is_file():
        return {"twin": None, "source_documents": [], "enrollment_documents": []}
    return load_json(path)


def _save_session(session: dict[str, Any]) -> None:
    path = _session_path()
    path.parent.mkdir(parents=True, exist_ok=True)
    write_json(session, path)


def _reset_session() -> None:
    _session_path().unlink(missing_ok=True)
    shutil.rmtree(_local_state_path() / CACHE_DIR, ignore_errors=True)


def _reset_session_twin_only() -> None:
    session = _load_session()
    session["twin"] = None
    session["source_documents"] = []
    session["enrollment_documents"] = []
    _save_session(session)


def _manual_cv_label() -> str:
    now = datetime.now(ZoneInfo("Europe/Madrid"))
    return (
        f"Manually entered CV, {now.strftime('%B')} {now.day} {now.year}, "
        f"{now.hour}:{now.minute:02d} {now.tzname()}"
    )


def _timing_mark(timings: list[dict[str, Any]], event: str, start: float) -> None:
    timings.append({"event": event, "elapsed_ms": round((perf_counter() - start) * 1000, 1)})


def _write_timing_log(
    *,
    operation: str,
    filename: str,
    source_id: str | None,
    timings: list[dict[str, Any]],
) -> Path:
    path = _local_state_path() / LOG_DIR / "timings.jsonl"
    path.parent.mkdir(parents=True, exist_ok=True)
    record = {
        "created_at": datetime.now(ZoneInfo("UTC")).isoformat(),
        "operation": operation,
        "filename": filename,
        "source_id": source_id,
        "timings": timings,
    }
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(record, ensure_ascii=False) + "\n")
    return path


def _append_source_document(
    source_documents: list[dict[str, Any]],
    source_document: dict[str, Any],
) -> list[dict[str, Any]]:
    if any(item.get("source_id") == source_document.get("source_id") for item in source_documents):
        return source_documents
    return [*source_documents, source_document]


def _auth_candidates_payload() -> dict[str, Any]:
    session = _load_session()
    return {
        "candidates": collect_email_candidates(session.get("enrollment_documents", [])),
        "has_session_twin": bool(session.get("twin")),
    }


def _request_code_payload(
    *,
    email: str,
    ip_address: str,
    purpose: str = "create_account",
) -> dict[str, Any]:
    repo = _account_repository()
    normalized_email = normalize_email(email)
    if purpose == "sign_in":
        user = repo.get_user_by_email(email=normalized_email)
        if user is None:
            raise ValueError("No account found for this email")
        persistent = repo.load_persistent_twin(user_id=user["id"])
        if persistent is None:
            raise ValueError("No saved Digital Career Twin was found for this email")
    elif purpose == "create_account":
        if not _load_session().get("twin"):
            raise ValueError("Create a Digital Career Twin before creating an account")
        if repo.get_user_by_email(email=normalized_email) is not None:
            raise ValueError(
                "An account with this email address already exists. "
                "Please try logging in instead."
            )
    else:
        raise ValueError("Choose create_account or sign_in")

    delivery = repo.request_login_code(
        email=normalized_email,
        ip_address=ip_address,
    )
    return {
        "email": delivery.email,
        "expires_at": delivery.expires_at,
        "delivery_mode": delivery.delivery_mode,
        "simulated_code": delivery.code,
        "purpose": purpose,
    }


def _verify_code_payload(
    *,
    email: str,
    code: str,
    duration: str,
    timezone: str,
    purpose: str = "create_account",
    merge_strategy: str | None = None,
) -> tuple[HTTPStatus, dict[str, Any]]:
    if purpose == "create_account" and not _load_session().get("twin"):
        raise ValueError("Create a Digital Career Twin before creating an account")
    if purpose not in {"create_account", "sign_in"}:
        raise ValueError("Choose create_account or sign_in")
    repo = _account_repository()
    user = repo.verify_login_code(
        email=email,
        code=code,
        create_user=purpose == "create_account",
    )
    if purpose == "sign_in" and repo.load_persistent_twin(user_id=user["id"]) is None:
        raise ValueError("No saved Digital Career Twin was found for this email")
    auth_session = repo.create_session(
        user_id=user["id"],
        duration=_session_duration(duration),
        timezone=timezone or "UTC",
    )
    return _post_auth_payload(
        repo=repo,
        user=user,
        auth_session=auth_session,
        merge_strategy=merge_strategy,
    )


def _auth_session_payload(session_id: str | None) -> dict[str, Any]:
    if not session_id:
        return {"authenticated": False}
    repo = _account_repository()
    auth_session = repo.get_session(session_id)
    if auth_session is None:
        return {"authenticated": False}
    user = repo.get_user(user_id=auth_session["user_id"])
    if user is None:
        return {"authenticated": False}
    persistent = repo.load_persistent_twin(user_id=user["id"])
    return {
        "authenticated": True,
        "session": _public_auth_session(auth_session),
        "user": _public_user(user),
        "account": repo.account_metadata(user_id=user["id"]),
        "has_persistent_twin": persistent is not None,
        "persistent_twin_saved_at": persistent.get("saved_at") if persistent else None,
    }


def _logout_payload(session_id: str | None) -> dict[str, Any]:
    if session_id:
        _account_repository().revoke_session(session_id)
    _reset_session()
    return {
        "authenticated": False,
        "status": "logged_out",
        "cleared": ["session", "source_cache"],
    }


def _resolve_merge_payload(
    *,
    session_id: str | None,
    merge_strategy: str,
) -> tuple[HTTPStatus, dict[str, Any]]:
    if not session_id:
        return HTTPStatus.UNAUTHORIZED, {"error": "Sign in before resolving Twin merge"}
    repo = _account_repository()
    auth_session = repo.get_session(session_id)
    if auth_session is None:
        return HTTPStatus.UNAUTHORIZED, {"error": "Session expired; sign in again"}
    user = repo.get_user(user_id=auth_session["user_id"])
    if user is None:
        return HTTPStatus.UNAUTHORIZED, {"error": "Account no longer exists"}
    return _post_auth_payload(
        repo=repo,
        user=user,
        auth_session=auth_session,
        merge_strategy=merge_strategy,
    )


def _delete_account_payload(
    *,
    session_id: str | None,
    confirmation: str,
) -> tuple[HTTPStatus, dict[str, Any]]:
    expected = (
        "Are you sure? Your digital twin will be deleted and cannot be recovered. "
        "You will have to rebuild the Twin if you come back later."
    )
    if confirmation != expected:
        return HTTPStatus.BAD_REQUEST, {"error": "Account deletion confirmation did not match"}
    repo = _account_repository()
    if not session_id:
        return HTTPStatus.UNAUTHORIZED, {"error": "Sign in before deleting your account"}
    auth_session = repo.get_session(session_id)
    if auth_session is None:
        return HTTPStatus.UNAUTHORIZED, {"error": "Session expired; sign in again"}
    repo.delete_account(user_id=auth_session["user_id"])
    _reset_session_twin_only()
    return HTTPStatus.OK, {"status": "deleted"}


def _post_auth_payload(
    *,
    repo: LocalAccountRepository,
    user: dict[str, Any],
    auth_session: dict[str, Any],
    merge_strategy: str | None,
) -> tuple[HTTPStatus, dict[str, Any]]:
    if merge_strategy not in {None, "merge_session", "discard_session"}:
        raise ValueError("Choose merge_session or discard_session")
    local_session = _load_session()
    persistent = repo.load_persistent_twin(user_id=user["id"])
    has_session_twin = bool(local_session.get("twin"))
    if has_session_twin and persistent is not None and merge_strategy is None:
        return HTTPStatus.CONFLICT, {
            "status": "merge_decision_required",
            "message": "Choose whether to merge this session Twin into your saved Twin.",
            "session": _public_auth_session(auth_session),
            "user": _public_user(user),
            "options": ["merge_session", "discard_session"],
        }

    if has_session_twin and (persistent is None or merge_strategy == "merge_session"):
        record = _persistent_record_from_session(
            repo=repo,
            user_id=user["id"],
            local_session=local_session,
            existing=persistent,
        )
    elif persistent is not None:
        record = persistent
        _save_session(
            {
                "twin": persistent["twin"],
                "source_documents": persistent.get("source_documents", []),
                "enrollment_documents": persistent.get("enrollment_documents", []),
            }
        )
    else:
        record = None

    return HTTPStatus.OK, {
        "authenticated": True,
        "session": _public_auth_session(auth_session),
        "user": _public_user(user),
        "account": repo.account_metadata(user_id=user["id"]),
        "has_persistent_twin": record is not None,
        "persistent_twin_saved_at": record.get("saved_at") if record else None,
    }


def _save_authenticated_session_twin(session_id: str | None) -> dict[str, Any] | None:
    if not session_id:
        return None
    repo = _account_repository()
    auth_session = repo.get_session(session_id)
    if auth_session is None:
        return None
    user = repo.get_user(user_id=auth_session["user_id"])
    if user is None:
        return None
    local_session = _load_session()
    if not local_session.get("twin"):
        return None
    return repo.save_persistent_twin(
        user_id=user["id"],
        twin=local_session["twin"],
        source_documents=local_session.get("source_documents", []),
        enrollment_documents=local_session.get("enrollment_documents", []),
    )


def _persistent_record_from_session(
    *,
    repo: LocalAccountRepository,
    user_id: str,
    local_session: dict[str, Any],
    existing: dict[str, Any] | None,
) -> dict[str, Any]:
    twin = local_session["twin"]
    source_documents = local_session.get("source_documents", [])
    enrollment_documents = local_session.get("enrollment_documents", [])
    if existing is not None:
        twin, _summary = ReconciliationAgent().reconcile(
            existing_twin=existing.get("twin"),
            candidate_twin=twin,
        )
        source_documents = _merge_documents(
            existing.get("source_documents", []),
            source_documents,
            key="source_id",
        )
        enrollment_documents = _merge_documents(
            existing.get("enrollment_documents", []),
            enrollment_documents,
            key="source_id",
        )
        contracts = _contracts()
        validate_twin(
            twin,
            contracts["twin"],
            contracts["catalog"],
            source_documents=source_documents,
        )
        _save_session(
            {
                "twin": twin,
                "source_documents": source_documents,
                "enrollment_documents": enrollment_documents,
            }
        )
    return repo.save_persistent_twin(
        user_id=user_id,
        twin=twin,
        source_documents=source_documents,
        enrollment_documents=enrollment_documents,
    )


def _merge_documents(
    existing: list[dict[str, Any]],
    incoming: list[dict[str, Any]],
    *,
    key: str,
) -> list[dict[str, Any]]:
    merged = list(existing)
    seen = {item.get(key) for item in merged}
    for item in incoming:
        if item.get(key) not in seen:
            merged.append(item)
            seen.add(item.get(key))
    return merged


def _public_auth_session(session: dict[str, Any]) -> dict[str, Any]:
    return {
        "id": session["id"],
        "created_at": session["created_at"],
        "expires_at": session["expires_at"],
        "last_seen_at": session["last_seen_at"],
    }


def _public_user(user: dict[str, Any]) -> dict[str, Any]:
    return {"id": user["id"], "email": user["email"]}


def _session_duration(value: str) -> Any:
    if value not in {"midnight", "7_days", "1_month"}:
        raise ValueError("Choose a session duration: midnight, 7_days or 1_month")
    return value


def _cache_path(source_document: dict[str, Any]) -> Path:
    digest = source_document["content_hash"].removeprefix("sha256:")
    filename = f"{digest}.{CACHE_CONTRACT_VERSION}.candidate.json"
    return _project_root() / SESSION_DIR / CACHE_DIR / filename


def _load_cached_candidate(source_document: dict[str, Any]) -> dict[str, Any] | None:
    path = _cache_path(source_document)
    if path.is_file():
        cached = load_json(path)
        if cached.get("cache_contract_version") == CACHE_CONTRACT_VERSION:
            return cached.get("candidate_twin")
    return None


def _save_cached_candidate(source_document: dict[str, Any], candidate: dict[str, Any]) -> None:
    path = _cache_path(source_document)
    path.parent.mkdir(parents=True, exist_ok=True)
    write_json(
        {
            "cache_contract_version": CACHE_CONTRACT_VERSION,
            "candidate_twin": candidate,
        },
        path,
    )


def _provider() -> FoundryTwinProvider:
    from azure.identity import AzureDeveloperCliCredential

    provider_class = (
        FoundryTwinProvider
        if os.environ.get("DCTWIN_MODEL_PATH") == "full"
        else FoundryExtractionTwinProvider
    )
    return provider_class.from_files(
        project_endpoint=os.environ["FOUNDRY_PROJECT_ENDPOINT"],
        model_deployment=os.environ["DCTWIN_MODEL_DEPLOYMENT"],
        credential=AzureDeveloperCliCredential(process_timeout=30),
        project_root=_project_root(),
    )


def _registry() -> AdapterRegistry:
    registry = AdapterRegistry()
    registry.register(PdfCvAdapter())
    registry.register(DocxCvAdapter())
    return registry


class LocalAppHandler(BaseHTTPRequestHandler):
    server_version = "DCTwinLocal/0.1"

    def do_GET(self) -> None:  # noqa: N802
        if self.path == "/":
            self._send_bytes(
                HTTPStatus.OK,
                (_project_root() / "src/web/index.html").read_bytes(),
                "text/html; charset=utf-8",
            )
        elif self.path == "/api/health":
            self._send_json(HTTPStatus.OK, _health_payload())
        elif self.path == "/api/state":
            session = _load_session()
            twin = session.get("twin")
            self._send_json(
                HTTPStatus.OK,
                {
                    "has_twin": bool(twin),
                    "twin": twin,
                    "roles": twin.get("roles", []) if twin else [],
                    "source_count": len(session.get("source_documents", [])),
                },
            )
        elif self.path == "/api/auth/candidates":
            self._send_json(HTTPStatus.OK, _auth_candidates_payload())
        elif self.path == "/api/auth/session":
            self._send_json(HTTPStatus.OK, _auth_session_payload(self._auth_session_id()))
        else:
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "Not found"})

    def do_POST(self) -> None:  # noqa: N802
        if self.path == "/api/adapt":
            self._handle_file_adapt()
        elif self.path == "/api/adapt-text":
            self._handle_text_adapt()
        elif self.path == "/api/manual-evidence":
            self._handle_manual_evidence()
        elif self.path == "/api/reset":
            _reset_session()
            self._send_json(
                HTTPStatus.OK,
                {"status": "reset", "cleared": ["session", "source_cache"]},
            )
        elif self.path == "/api/auth/request-code":
            self._handle_auth_request_code()
        elif self.path == "/api/auth/verify-code":
            self._handle_auth_verify_code()
        elif self.path == "/api/auth/resolve-merge":
            self._handle_auth_resolve_merge()
        elif self.path == "/api/auth/logout":
            self._send_json(HTTPStatus.OK, _logout_payload(self._auth_session_id()))
        elif self.path == "/api/account/delete":
            self._handle_account_delete()
        else:
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "Not found"})
            return

    def _handle_auth_request_code(self) -> None:
        try:
            payload = self._read_json_body(max_bytes=MAX_TEXT_BYTES)
            self._send_json(
                HTTPStatus.OK,
                _request_code_payload(
                    email=str(payload.get("email", "")),
                    ip_address=self._client_ip(),
                    purpose=str(payload.get("purpose", "create_account")),
                ),
            )
        except Exception as exc:
            self._send_json(
                HTTPStatus.BAD_REQUEST,
                {"error": f"Could not request a login code: {exc}"},
            )

    def _handle_auth_verify_code(self) -> None:
        try:
            payload = self._read_json_body(max_bytes=MAX_TEXT_BYTES)
            status, response = _verify_code_payload(
                email=str(payload.get("email", "")),
                code=str(payload.get("code", "")),
                duration=str(payload.get("duration", "7_days")),
                timezone=str(payload.get("timezone", "UTC")),
                purpose=str(payload.get("purpose", "create_account")),
                merge_strategy=payload.get("merge_strategy"),
            )
            self._send_json(status, response)
        except Exception as exc:
            self._send_json(
                HTTPStatus.BAD_REQUEST,
                {"error": f"Could not verify the login code: {exc}"},
            )

    def _handle_account_delete(self) -> None:
        try:
            payload = self._read_json_body(max_bytes=MAX_TEXT_BYTES)
            status, response = _delete_account_payload(
                session_id=self._auth_session_id(),
                confirmation=str(payload.get("confirmation", "")),
            )
            self._send_json(status, response)
        except Exception as exc:
            self._send_json(
                HTTPStatus.BAD_REQUEST,
                {"error": f"Could not delete the account: {exc}"},
            )

    def _handle_auth_resolve_merge(self) -> None:
        try:
            payload = self._read_json_body(max_bytes=MAX_TEXT_BYTES)
            status, response = _resolve_merge_payload(
                session_id=self._auth_session_id(),
                merge_strategy=str(payload.get("merge_strategy", "")),
            )
            self._send_json(status, response)
        except Exception as exc:
            self._send_json(
                HTTPStatus.BAD_REQUEST,
                {"error": f"Could not resolve the Twin merge choice: {exc}"},
            )

    def _auth_session_id(self) -> str | None:
        value = self.headers.get("X-DCTWIN-Session", "").strip()
        return value or None

    def _client_ip(self) -> str:
        host, _port = self.client_address
        return host

    def _handle_file_adapt(self) -> None:
        if self.headers.get("X-DCTWIN-Local") != "1":
            self._send_json(HTTPStatus.FORBIDDEN, {"error": "Local request header missing"})
            return

        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0
        if length <= 0:
            self._send_json(HTTPStatus.BAD_REQUEST, {"error": "Choose a CV to upload"})
            return
        if length > MAX_UPLOAD_BYTES:
            self._send_json(
                HTTPStatus.REQUEST_ENTITY_TOO_LARGE,
                {"error": "The local preview accepts files up to 15 MB"},
            )
            return

        filename = Path(unquote(self.headers.get("X-Filename", ""))).name
        suffix = Path(filename).suffix.lower()
        if suffix not in {".pdf", ".docx"}:
            self._send_json(
                HTTPStatus.UNSUPPORTED_MEDIA_TYPE,
                {"error": "Use a PDF or DOCX CV"},
            )
            return

        temporary_path: Path | None = None
        timings: list[dict[str, Any]] = []
        started = perf_counter()
        try:
            _timing_mark(timings, "upload_received", started)
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as temporary:
                temporary.write(self.rfile.read(length))
                temporary_path = Path(temporary.name)

            _timing_mark(timings, "text_extraction_started", started)
            registry = _registry()
            adapted = registry.adapt("cv", temporary_path)
            _timing_mark(timings, "text_extraction_completed", started)
            result = self._run_source_adapter_and_reconcile(
                adapted=adapted,
                filename=filename,
                timings=timings,
                started=started,
            )
            self._send_json(HTTPStatus.OK, result)
        except Exception as exc:
            self._send_json(
                HTTPStatus.UNPROCESSABLE_ENTITY,
                {"error": f"The document could not be adapted: {exc}"},
            )
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)

    def _handle_text_adapt(self) -> None:
        if self.headers.get("X-DCTWIN-Local") != "1":
            self._send_json(HTTPStatus.FORBIDDEN, {"error": "Local request header missing"})
            return
        timings: list[dict[str, Any]] = []
        started = perf_counter()
        try:
            payload = self._read_json_body(max_bytes=MAX_TEXT_BYTES)
            text = str(payload.get("text", ""))
            label = str(payload.get("label") or _manual_cv_label())
            _timing_mark(timings, "upload_received", started)
            _timing_mark(timings, "text_extraction_started", started)
            adapted = adapt_cv_text(text, label=label, content_identity=f"{label}\n{text}")
            _timing_mark(timings, "text_extraction_completed", started)
            result = self._run_source_adapter_and_reconcile(
                adapted=adapted,
                filename=label,
                timings=timings,
                started=started,
            )
            result["summary"]["filename"] = label
            self._send_json(HTTPStatus.OK, result)
        except Exception as exc:
            self._send_json(
                HTTPStatus.UNPROCESSABLE_ENTITY,
                {"error": f"The pasted CV could not be adapted: {exc}"},
            )

    def _handle_manual_evidence(self) -> None:
        if self.headers.get("X-DCTWIN-Local") != "1":
            self._send_json(HTTPStatus.FORBIDDEN, {"error": "Local request header missing"})
            return
        started = perf_counter()
        timings: list[dict[str, Any]] = []
        try:
            payload = self._read_json_body(max_bytes=MAX_TEXT_BYTES)
            session = _load_session()
            if not session.get("twin"):
                self._send_json(
                    HTTPStatus.BAD_REQUEST,
                    {"error": "Create or load a Twin before adding achievements"},
                )
                return
            _timing_mark(timings, "upload_received", started)
            contracts = _contracts()
            agent = ReconciliationAgent()
            updated, source_doc, reconciliation = agent.add_manual_evidence(
                twin=session["twin"],
                role_id=str(payload.get("role_id", "")),
                text=str(payload.get("text", "")),
                tag_catalog=contracts["catalog"],
            )
            validate_source_document(source_doc, contracts["source"])
            _timing_mark(timings, "text_extraction_completed", started)
            source_documents = _append_source_document(
                session.get("source_documents", []), source_doc
            )
            _timing_mark(timings, "json_validation_started", started)
            validate_twin(
                updated,
                contracts["twin"],
                contracts["catalog"],
                source_documents=source_documents,
            )
            _timing_mark(timings, "json_validation_completed", started)
            _timing_mark(timings, "mirror_rendered", started)
            session["twin"] = updated
            session["source_documents"] = source_documents
            session.setdefault("enrollment_documents", []).append(
                {
                    "schema_version": "0.1.0",
                    "source_id": source_doc["source_id"],
                    "candidates": [],
                }
            )
            _save_session(session)
            _save_authenticated_session_twin(self._auth_session_id())
            _write_timing_log(
                operation="manual_evidence",
                filename="Added achievements",
                source_id=source_doc["source_id"],
                timings=timings,
            )
            self._send_json(
                HTTPStatus.OK,
                self._response_payload(
                    source_document=source_doc,
                    enrollment_document={
                        "schema_version": "0.1.0",
                        "source_id": source_doc["source_id"],
                        "candidates": [],
                    },
                    twin=updated,
                    filename="Added achievements",
                    reconciliation=reconciliation.as_dict(),
                    timings=timings,
                    message="The achievements were added to the session Twin and validated.",
                ),
            )
        except Exception as exc:
            self._send_json(
                HTTPStatus.UNPROCESSABLE_ENTITY,
                {"error": f"The achievements could not be added: {exc}"},
            )

    def _run_source_adapter_and_reconcile(
        self,
        *,
        adapted: Any,
        filename: str,
        timings: list[dict[str, Any]],
        started: float,
    ) -> dict[str, Any]:
        if not _foundry_configured():
            raise RuntimeError("The local agent is not connected to a Foundry model deployment")

        contracts = _contracts()
        cached_candidate = _load_cached_candidate(adapted.model_document)
        if cached_candidate is not None:
            _timing_mark(timings, "model_cache_hit", started)
            source_document = adapted.model_document
            enrollment_document = adapted.enrollment_document
            candidate_twin = cached_candidate
        else:
            provider = _provider()
            try:
                _timing_mark(timings, "model_call_started", started)
                agent = SourceAdapterAgent(
                    registry=_registry(),
                    provider=provider,
                    source_schema=contracts["source"],
                    enrollment_schema=contracts["enrollment"],
                    twin_schema=contracts["twin"],
                    tag_catalog=contracts["catalog"],
                )
                run = agent.run_adapted(adapted)
                _timing_mark(timings, "model_call_completed", started)
            finally:
                provider.close()
            source_document = run.source_document
            enrollment_document = run.enrollment_document
            candidate_twin = run.candidate_twin
            _save_cached_candidate(source_document, candidate_twin)

        session = _load_session()
        reconciliation_agent = ReconciliationAgent()
        updated, reconciliation = reconciliation_agent.reconcile(
            existing_twin=session.get("twin"),
            candidate_twin=candidate_twin,
        )
        source_documents = _append_source_document(
            session.get("source_documents", []), source_document
        )
        _timing_mark(timings, "json_validation_started", started)
        validate_twin(
            updated,
            contracts["twin"],
            contracts["catalog"],
            source_documents=source_documents,
        )
        _timing_mark(timings, "json_validation_completed", started)
        _timing_mark(timings, "mirror_rendered", started)
        session["twin"] = updated
        session["source_documents"] = source_documents
        session.setdefault("enrollment_documents", []).append(enrollment_document)
        _save_session(session)
        _save_authenticated_session_twin(self._auth_session_id())
        _write_timing_log(
            operation="source_adaptation",
            filename=filename,
            source_id=source_document["source_id"],
            timings=timings,
        )
        return self._response_payload(
            source_document=source_document,
            enrollment_document=enrollment_document,
            twin=updated,
            filename=filename,
            reconciliation=reconciliation.as_dict(),
            timings=timings,
            message=(
                "The Source Adapter Agent generated a candidate Twin and the "
                "Reconciliation Agent merged it into the local session Twin."
            ),
        )

    @staticmethod
    def _response_payload(
        *,
        source_document: dict[str, Any],
        enrollment_document: dict[str, Any],
        twin: dict[str, Any],
        filename: str,
        reconciliation: dict[str, Any],
        timings: list[dict[str, Any]],
        message: str,
    ) -> dict[str, Any]:
        return {
            "source": source_document,
            "enrollment": enrollment_document,
            "twin": twin,
            "summary": {
                "filename": filename,
                "adapter": source_document["adapter"]["name"],
                "blocks": len(source_document["blocks"]),
                "redactions": sum(
                    len(block["redactions"]) for block in source_document["blocks"]
                ),
                "enrollment_candidates": len(enrollment_document["candidates"]),
            },
            "reconciliation": reconciliation,
            "timings": timings,
            "stages": [
                {
                    "id": "source_preview",
                    "label": "Reading your CV",
                    "status": "complete",
                    "detail": f"Normalized {len(source_document['blocks'])} source block(s).",
                },
                {
                    "id": "model_extraction",
                    "label": "Getting roles and achievements",
                    "status": "complete",
                    "detail": f"Found {len(twin.get('roles', []))} role(s) and {len(twin.get('evidence_items', []))} achievement(s).",
                },
                {
                    "id": "interpretation",
                    "label": "Inferring key skills and patterns",
                    "status": "complete",
                    "detail": f"Created {len(twin.get('inferences', []))} current hypothesis/hypotheses.",
                },
                {
                    "id": "rendering",
                    "label": "Rendering the Career Twin",
                    "status": "complete",
                    "detail": "Validated and rendered the session Twin.",
                },
            ],
            "agent": {"status": "complete", "message": message},
        }

    def _read_json_body(self, *, max_bytes: int) -> dict[str, Any]:
        try:
            length = int(self.headers.get("Content-Length", "0"))
        except ValueError:
            length = 0
        if length <= 0:
            return {}
        if length > max_bytes:
            raise ValueError("Request body is too large")
        payload = json.loads(self.rfile.read(length).decode("utf-8"))
        if not isinstance(payload, dict):
            raise ValueError("Expected a JSON object")
        return payload

    def _send_json(self, status: HTTPStatus, value: dict[str, Any]) -> None:
        self._send_bytes(
            status,
            json.dumps(value, ensure_ascii=False).encode("utf-8"),
            "application/json; charset=utf-8",
        )

    def _send_bytes(
        self, status: HTTPStatus, payload: bytes, content_type: str
    ) -> None:
        self.send_response(status)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(payload)))
        self.send_header("Cache-Control", "no-store")
        self.send_header("X-Content-Type-Options", "nosniff")
        self.send_header("Referrer-Policy", "no-referrer")
        self.send_header(
            "Content-Security-Policy",
            "default-src 'self'; style-src 'self' 'unsafe-inline'; "
            "script-src 'self' 'unsafe-inline'; img-src 'self' data:; "
            "connect-src 'self'; frame-ancestors 'none'",
        )
        self.end_headers()
        self.wfile.write(payload)

    def log_message(self, format: str, *args: object) -> None:
        # Log request metadata only. File contents and enrollment candidates stay private.
        super().log_message(format, *args)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the local DCT preview")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8765)
    return parser


def main() -> None:
    args = build_parser().parse_args()
    if args.host not in {"127.0.0.1", "localhost", "::1"}:
        raise SystemExit("The preview server may only bind to the local machine")
    server = ThreadingHTTPServer((args.host, args.port), LocalAppHandler)
    print(f"Digital Career Twin local preview: http://{args.host}:{args.port}")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
