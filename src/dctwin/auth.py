from __future__ import annotations

import hashlib
import secrets
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any, Literal
from zoneinfo import ZoneInfo

from dctwin.io import load_json, write_json


SessionDuration = Literal["midnight", "7_days", "1_month"]

CODE_TTL = timedelta(minutes=60)
MAX_CODE_REQUESTS_PER_HOUR = 5


@dataclass(frozen=True)
class LoginCodeDelivery:
    email: str
    code: str
    expires_at: str
    delivery_mode: str = "simulated"


def normalize_email(email: str) -> str:
    normalized = email.strip().lower()
    if "@" not in normalized or normalized.startswith("@") or normalized.endswith("@"):
        raise ValueError("Enter a valid email address")
    return normalized


def collect_email_candidates(
    enrollment_documents: list[dict[str, Any]],
) -> list[str]:
    emails: list[str] = []
    seen: set[str] = set()
    for document in enrollment_documents:
        for candidate in document.get("candidates", []):
            if candidate.get("type") != "email":
                continue
            email = normalize_email(str(candidate.get("value", "")))
            if email not in seen:
                emails.append(email)
                seen.add(email)
    return emails


def expires_at_for_duration(
    duration: SessionDuration,
    *,
    now: datetime | None = None,
    timezone: str = "UTC",
) -> datetime:
    current = _ensure_aware(now or datetime.now(UTC))
    if duration == "7_days":
        return current + timedelta(days=7)
    if duration == "1_month":
        return current + timedelta(days=30)
    if duration != "midnight":
        raise ValueError(f"Unknown session duration {duration!r}")

    local_now = current.astimezone(ZoneInfo(timezone))
    local_midnight = (local_now + timedelta(days=1)).replace(
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    )
    return local_midnight.astimezone(UTC)


class LocalAccountRepository:
    """File-backed Sprint 4 account/auth repository.

    This is intentionally a repository boundary, not a claim that JSON files are
    the final production store.
    """

    def __init__(self, state_path: Path):
        self.state_path = state_path

    def request_login_code(
        self,
        *,
        email: str,
        ip_address: str,
        now: datetime | None = None,
    ) -> LoginCodeDelivery:
        state = self._load()
        current = _ensure_aware(now or datetime.now(UTC))
        normalized_email = normalize_email(email)
        self._enforce_rate_limit(
            state,
            email=normalized_email,
            ip_address=ip_address,
            now=current,
        )

        code = f"{secrets.randbelow(1_000_000):06d}"
        salt = secrets.token_hex(16)
        record = {
            "id": _stable_id("code", f"{normalized_email}:{current.isoformat()}:{salt}"),
            "email": normalized_email,
            "ip_address": ip_address,
            "code_hash": _hash_code(code, salt),
            "salt": salt,
            "created_at": current.isoformat(),
            "expires_at": (current + CODE_TTL).isoformat(),
            "used_at": None,
        }
        state.setdefault("login_codes", []).append(record)
        self._save(state)
        return LoginCodeDelivery(
            email=normalized_email,
            code=code,
            expires_at=record["expires_at"],
        )

    def verify_login_code(
        self,
        *,
        email: str,
        code: str,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        state = self._load()
        current = _ensure_aware(now or datetime.now(UTC))
        normalized_email = normalize_email(email)
        latest = self._latest_code_for_email(state, normalized_email)
        if latest is None:
            raise ValueError("No active login code was requested for this email")
        if latest.get("used_at"):
            raise ValueError("Login code has already been used")
        if datetime.fromisoformat(latest["expires_at"]) <= current:
            raise ValueError("Login code has expired")
        if latest["code_hash"] != _hash_code(code, latest["salt"]):
            raise ValueError("Login code is incorrect")

        latest["used_at"] = current.isoformat()
        user = self._user_for_email(state, normalized_email)
        if user is None:
            user = {
                "id": _stable_id("usr", normalized_email),
                "email": normalized_email,
                "created_at": current.isoformat(),
                "persistent_twin": None,
            }
            state.setdefault("users", []).append(user)
        self._save(state)
        return user

    def create_session(
        self,
        *,
        user_id: str,
        duration: SessionDuration,
        timezone: str,
        now: datetime | None = None,
    ) -> dict[str, Any]:
        state = self._load()
        if self._user_for_id(state, user_id) is None:
            raise ValueError(f"Unknown user_id {user_id!r}")
        current = _ensure_aware(now or datetime.now(UTC))
        session = {
            "id": _stable_id("sess", f"{user_id}:{current.isoformat()}:{secrets.token_hex(8)}"),
            "user_id": user_id,
            "created_at": current.isoformat(),
            "expires_at": expires_at_for_duration(
                duration,
                now=current,
                timezone=timezone,
            ).isoformat(),
            "revoked_at": None,
            "last_seen_at": current.isoformat(),
        }
        state.setdefault("sessions", []).append(session)
        self._save(state)
        return session

    def get_session(
        self,
        session_id: str,
        *,
        now: datetime | None = None,
    ) -> dict[str, Any] | None:
        state = self._load()
        current = _ensure_aware(now or datetime.now(UTC))
        for session in state.get("sessions", []):
            if session.get("id") != session_id:
                continue
            if session.get("revoked_at"):
                return None
            if datetime.fromisoformat(session["expires_at"]) <= current:
                return None
            session["last_seen_at"] = current.isoformat()
            self._save(state)
            return session
        return None

    def revoke_session(
        self,
        session_id: str,
        *,
        now: datetime | None = None,
    ) -> None:
        state = self._load()
        current = _ensure_aware(now or datetime.now(UTC))
        for session in state.get("sessions", []):
            if session.get("id") == session_id:
                session["revoked_at"] = current.isoformat()
        self._save(state)

    def save_persistent_twin(
        self,
        *,
        user_id: str,
        twin: dict[str, Any],
        source_documents: list[dict[str, Any]],
        enrollment_documents: list[dict[str, Any]],
        now: datetime | None = None,
    ) -> dict[str, Any]:
        state = self._load()
        user = self._user_for_id(state, user_id)
        if user is None:
            raise ValueError(f"Unknown user_id {user_id!r}")
        current = _ensure_aware(now or datetime.now(UTC))
        record = {
            "saved_at": current.isoformat(),
            "twin": twin,
            "source_documents": source_documents,
            "enrollment_documents": enrollment_documents,
        }
        user["persistent_twin"] = record
        self._save(state)
        return record

    def load_persistent_twin(self, *, user_id: str) -> dict[str, Any] | None:
        state = self._load()
        user = self._user_for_id(state, user_id)
        if user is None:
            raise ValueError(f"Unknown user_id {user_id!r}")
        return user.get("persistent_twin")

    def delete_account(self, *, user_id: str) -> None:
        state = self._load()
        state["users"] = [
            user for user in state.get("users", []) if user.get("id") != user_id
        ]
        state["sessions"] = [
            session
            for session in state.get("sessions", [])
            if session.get("user_id") != user_id
        ]
        self._save(state)

    def _load(self) -> dict[str, Any]:
        if not self.state_path.is_file():
            return {
                "schema_version": "0.1.0",
                "users": [],
                "login_codes": [],
                "sessions": [],
            }
        return load_json(self.state_path)

    def _save(self, state: dict[str, Any]) -> None:
        write_json(state, self.state_path)

    @staticmethod
    def _latest_code_for_email(
        state: dict[str, Any],
        email: str,
    ) -> dict[str, Any] | None:
        matches = [
            record for record in state.get("login_codes", []) if record.get("email") == email
        ]
        if not matches:
            return None
        return max(matches, key=lambda record: record["created_at"])

    @staticmethod
    def _user_for_email(
        state: dict[str, Any],
        email: str,
    ) -> dict[str, Any] | None:
        for user in state.get("users", []):
            if user.get("email") == email:
                return user
        return None

    @staticmethod
    def _user_for_id(
        state: dict[str, Any],
        user_id: str,
    ) -> dict[str, Any] | None:
        for user in state.get("users", []):
            if user.get("id") == user_id:
                return user
        return None

    @staticmethod
    def _enforce_rate_limit(
        state: dict[str, Any],
        *,
        email: str,
        ip_address: str,
        now: datetime,
    ) -> None:
        window_start = now - timedelta(hours=1)
        recent = [
            record
            for record in state.get("login_codes", [])
            if datetime.fromisoformat(record["created_at"]) > window_start
            and (record.get("email") == email or record.get("ip_address") == ip_address)
        ]
        if len(recent) >= MAX_CODE_REQUESTS_PER_HOUR:
            raise ValueError("Too many login code requests; try again later")


def _hash_code(code: str, salt: str) -> str:
    return hashlib.sha256(f"{salt}:{code}".encode("utf-8")).hexdigest()


def _stable_id(prefix: str, value: str) -> str:
    digest = hashlib.sha256(value.encode("utf-8")).hexdigest()[:16]
    return f"{prefix}_{digest}"


def _ensure_aware(value: datetime) -> datetime:
    if value.tzinfo is None:
        return value.replace(tzinfo=UTC)
    return value.astimezone(UTC)
