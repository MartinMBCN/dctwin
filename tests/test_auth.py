from __future__ import annotations

from datetime import UTC, datetime, timedelta
from zoneinfo import ZoneInfo

import pytest

from dctwin.auth import (
    LocalAccountRepository,
    collect_email_candidates,
    expires_at_for_duration,
    normalize_email,
)
from dctwin.io import load_json


def test_collect_email_candidates_normalizes_and_deduplicates() -> None:
    documents = [
        {
            "candidates": [
                {"type": "email", "value": "Alex@Example.COM"},
                {"type": "email", "value": "alex@example.com"},
            ]
        },
        {"candidates": [{"type": "email", "value": "other@example.com"}]},
    ]

    assert collect_email_candidates(documents) == [
        "alex@example.com",
        "other@example.com",
    ]


def test_login_code_is_hashed_single_use_and_creates_user(tmp_path) -> None:
    repo = LocalAccountRepository(tmp_path / "accounts.json")
    now = datetime(2026, 7, 7, 9, 0, tzinfo=UTC)

    delivery = repo.request_login_code(
        email="USER@Example.com",
        ip_address="127.0.0.1",
        now=now,
    )
    state = load_json(tmp_path / "accounts.json")

    assert delivery.email == "user@example.com"
    assert delivery.code not in (tmp_path / "accounts.json").read_text()
    assert state["login_codes"][0]["code_hash"]
    assert state["login_codes"][0]["used_at"] is None

    user = repo.verify_login_code(
        email="user@example.com",
        code=delivery.code,
        now=now + timedelta(minutes=1),
    )

    assert user["email"] == "user@example.com"
    with pytest.raises(ValueError, match="already been used"):
        repo.verify_login_code(
            email="user@example.com",
            code=delivery.code,
            now=now + timedelta(minutes=2),
        )


def test_only_most_recent_code_is_accepted(tmp_path) -> None:
    repo = LocalAccountRepository(tmp_path / "accounts.json")
    now = datetime(2026, 7, 7, 9, 0, tzinfo=UTC)

    first = repo.request_login_code(
        email="user@example.com",
        ip_address="127.0.0.1",
        now=now,
    )
    second = repo.request_login_code(
        email="user@example.com",
        ip_address="127.0.0.1",
        now=now + timedelta(minutes=1),
    )

    with pytest.raises(ValueError, match="incorrect"):
        repo.verify_login_code(
            email="user@example.com",
            code=first.code,
            now=now + timedelta(minutes=2),
        )

    user = repo.verify_login_code(
        email="user@example.com",
        code=second.code,
        now=now + timedelta(minutes=2),
    )
    assert user["email"] == "user@example.com"


def test_login_code_expiry_and_rate_limit(tmp_path) -> None:
    repo = LocalAccountRepository(tmp_path / "accounts.json")
    now = datetime(2026, 7, 7, 9, 0, tzinfo=UTC)

    delivery = repo.request_login_code(
        email="user@example.com",
        ip_address="127.0.0.1",
        now=now,
    )
    with pytest.raises(ValueError, match="expired"):
        repo.verify_login_code(
            email="user@example.com",
            code=delivery.code,
            now=now + timedelta(minutes=61),
        )

    for offset in range(1, 5):
        repo.request_login_code(
            email=f"user{offset}@example.com",
            ip_address="127.0.0.1",
            now=now + timedelta(minutes=offset),
        )
    with pytest.raises(ValueError, match="Too many"):
        repo.request_login_code(
            email="another@example.com",
            ip_address="127.0.0.1",
            now=now + timedelta(minutes=6),
        )


def test_session_expiry_uses_user_midnight_and_revocation(tmp_path) -> None:
    repo = LocalAccountRepository(tmp_path / "accounts.json")
    now = datetime(2026, 7, 7, 21, 30, tzinfo=UTC)
    delivery = repo.request_login_code(
        email="user@example.com",
        ip_address="127.0.0.1",
        now=now,
    )
    user = repo.verify_login_code(
        email="user@example.com",
        code=delivery.code,
        now=now + timedelta(minutes=1),
    )

    session = repo.create_session(
        user_id=user["id"],
        duration="midnight",
        timezone="Europe/Madrid",
        now=now,
    )

    expires_at = datetime.fromisoformat(session["expires_at"])
    assert expires_at.astimezone(ZoneInfo("Europe/Madrid")).hour == 0
    assert repo.get_session(session["id"], now=now + timedelta(minutes=5))

    repo.revoke_session(session["id"], now=now + timedelta(minutes=6))
    assert repo.get_session(session["id"], now=now + timedelta(minutes=7)) is None


def test_persistent_twin_can_be_saved_loaded_and_deleted(tmp_path) -> None:
    repo = LocalAccountRepository(tmp_path / "accounts.json")
    now = datetime(2026, 7, 7, 9, 0, tzinfo=UTC)
    delivery = repo.request_login_code(
        email="user@example.com",
        ip_address="127.0.0.1",
        now=now,
    )
    user = repo.verify_login_code(
        email="user@example.com",
        code=delivery.code,
        now=now + timedelta(minutes=1),
    )
    twin = {"schema_version": "0.2.0", "twin_id": "twin_example"}

    repo.save_persistent_twin(
        user_id=user["id"],
        twin=twin,
        source_documents=[{"source_id": "src_example"}],
        enrollment_documents=[{"source_id": "src_example", "candidates": []}],
        now=now + timedelta(minutes=2),
    )

    record = repo.load_persistent_twin(user_id=user["id"])
    assert record is not None
    assert record["twin"] == twin

    repo.delete_account(user_id=user["id"])
    with pytest.raises(ValueError, match="Unknown user_id"):
        repo.load_persistent_twin(user_id=user["id"])


def test_normalize_email_rejects_invalid_values() -> None:
    with pytest.raises(ValueError):
        normalize_email("not-an-email")


def test_fixed_duration_expiry_values() -> None:
    now = datetime(2026, 7, 7, 9, 0, tzinfo=UTC)

    assert expires_at_for_duration("7_days", now=now) == now + timedelta(days=7)
    assert expires_at_for_duration("1_month", now=now) == now + timedelta(days=30)
