from __future__ import annotations

import argparse
import json
import os
import tempfile
from datetime import datetime
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from time import perf_counter
from typing import Any
from urllib.parse import unquote
from zoneinfo import ZoneInfo

from dctwin.adapters import AdapterRegistry, DocxCvAdapter, PdfCvAdapter, adapt_cv_text
from dctwin.agent import SourceAdapterAgent
from dctwin.foundry import FoundryTwinProvider
from dctwin.io import load_json, write_json
from dctwin.reconciliation import ReconciliationAgent
from dctwin.validation import validate_source_document, validate_twin


MAX_UPLOAD_BYTES = 15 * 1024 * 1024
MAX_TEXT_BYTES = 1 * 1024 * 1024
SESSION_DIR = ".dctwin-local"
SESSION_FILE = "session-state.json"


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


def _manual_cv_label() -> str:
    now = datetime.now(ZoneInfo("Europe/Madrid"))
    return (
        f"Manually entered CV, {now.strftime('%B')} {now.day} {now.year}, "
        f"{now.hour}:{now.minute:02d} {now.tzname()}"
    )


def _timing_mark(timings: list[dict[str, Any]], event: str, start: float) -> None:
    timings.append({"event": event, "elapsed_ms": round((perf_counter() - start) * 1000, 1)})


def _append_source_document(
    source_documents: list[dict[str, Any]],
    source_document: dict[str, Any],
) -> list[dict[str, Any]]:
    if any(item.get("source_id") == source_document.get("source_id") for item in source_documents):
        return source_documents
    return [*source_documents, source_document]


def _provider() -> FoundryTwinProvider:
    from azure.identity import AzureDeveloperCliCredential

    return FoundryTwinProvider.from_files(
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
            self._send_json(
                HTTPStatus.OK,
                {
                    "status": "ok",
                    "mode": "local",
                    "formats": ["pdf", "docx", "pasted_text"],
                    "foundry": "ready" if _foundry_configured() else "not_configured",
                },
            )
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
            self._send_json(HTTPStatus.OK, {"status": "reset"})
        else:
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "Not found"})
            return

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
                {"error": "Create or load a Twin before adding an achievement"},
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
            _save_session(session)
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
                    filename="Added achievement",
                    reconciliation=reconciliation.as_dict(),
                    timings=timings,
                    message="The achievement was added to the session Twin and validated.",
                ),
            )
        except Exception as exc:
            self._send_json(
                HTTPStatus.UNPROCESSABLE_ENTITY,
                {"error": f"The achievement could not be added: {exc}"},
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

        session = _load_session()
        reconciliation_agent = ReconciliationAgent()
        updated, reconciliation = reconciliation_agent.reconcile(
            existing_twin=session.get("twin"),
            candidate_twin=run.candidate_twin,
        )
        source_documents = _append_source_document(
            session.get("source_documents", []), run.source_document
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
        session.setdefault("enrollment_documents", []).append(run.enrollment_document)
        _save_session(session)
        return self._response_payload(
            source_document=run.source_document,
            enrollment_document=run.enrollment_document,
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
