from __future__ import annotations

import re
from http import HTTPStatus
from pathlib import Path

from dctwin import web
from dctwin.io import load_json


def test_reset_session_clears_session_and_cache(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(web, "_project_root", lambda: tmp_path)
    state_dir = tmp_path / web.SESSION_DIR
    session_file = state_dir / web.SESSION_FILE
    cache_file = state_dir / web.CACHE_DIR / "source.candidate.json"
    account_file = state_dir / web.ACCOUNT_FILE
    session_file.parent.mkdir(parents=True)
    cache_file.parent.mkdir(parents=True)
    session_file.write_text("{}", encoding="utf-8")
    cache_file.write_text("{}", encoding="utf-8")
    account_file.write_text("{}", encoding="utf-8")

    web._reset_session()

    assert not session_file.exists()
    assert not cache_file.exists()
    assert account_file.exists()


def test_health_payload_exposes_semver_app_version() -> None:
    payload = web._health_payload()

    assert payload["status"] == "ok"
    assert re.match(r"^\d+\.\d+\.\d+$", payload["app_version"])


def test_auth_candidates_collect_all_session_email_candidates(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(web, "_project_root", lambda: tmp_path)
    web._save_session(
        {
            "twin": {"twin_id": "twin_example"},
            "source_documents": [],
            "enrollment_documents": [
                {
                    "candidates": [
                        {"type": "email", "value": "Alex@Example.com"},
                        {"type": "email", "value": "alex@example.com"},
                    ]
                },
                {"candidates": [{"type": "email", "value": "other@example.com"}]},
            ],
        }
    )

    payload = web._auth_candidates_payload()

    assert payload == {
        "candidates": ["alex@example.com", "other@example.com"],
        "has_session_twin": True,
    }


def test_verify_code_promotes_session_twin_and_creates_auth_session(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(web, "_project_root", lambda: tmp_path)
    web._save_session(
        {
            "twin": {"schema_version": "0.2.0", "twin_id": "twin_session"},
            "source_documents": [{"source_id": "src_session"}],
            "enrollment_documents": [{"source_id": "src_session", "candidates": []}],
        }
    )
    delivery = web._request_code_payload(
        email="USER@example.com",
        ip_address="127.0.0.1",
    )

    status, payload = web._verify_code_payload(
        email="user@example.com",
        code=delivery["simulated_code"],
        duration="7_days",
        timezone="Europe/Madrid",
    )

    assert status == HTTPStatus.OK
    assert payload["authenticated"] is True
    assert payload["has_persistent_twin"] is True
    assert payload["user"]["email"] == "user@example.com"
    auth_session = web._auth_session_payload(payload["session"]["id"])
    assert auth_session["authenticated"] is True
    assert auth_session["has_persistent_twin"] is True
    assert auth_session["persistent_twin_saved_at"]

    state = load_json(tmp_path / web.SESSION_DIR / web.ACCOUNT_FILE)
    assert state["users"][0]["persistent_twin"]["twin"]["twin_id"] == "twin_session"


def test_logout_clears_session_and_cache_but_preserves_account(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(web, "_project_root", lambda: tmp_path)
    session_id = _sign_in_and_save_twin(monkeypatch, tmp_path, twin_id="twin_saved")
    cache_file = tmp_path / web.SESSION_DIR / web.CACHE_DIR / "source.candidate.json"
    cache_file.parent.mkdir(parents=True, exist_ok=True)
    cache_file.write_text("{}", encoding="utf-8")

    payload = web._logout_payload(session_id)

    assert payload == {
        "authenticated": False,
        "status": "logged_out",
        "cleared": ["session", "source_cache"],
    }
    assert not (tmp_path / web.SESSION_DIR / web.SESSION_FILE).exists()
    assert not cache_file.exists()
    state = load_json(tmp_path / web.SESSION_DIR / web.ACCOUNT_FILE)
    assert state["users"][0]["persistent_twin"]["twin"]["twin_id"] == "twin_saved"
    assert web._auth_session_payload(session_id)["authenticated"] is False


def test_sign_in_to_account_without_saved_twin_is_explicit(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(web, "_project_root", lambda: tmp_path)
    delivery = web._request_code_payload(
        email="empty@example.com",
        ip_address="127.0.0.1",
    )

    status, payload = web._verify_code_payload(
        email="empty@example.com",
        code=delivery["simulated_code"],
        duration="7_days",
        timezone="Europe/Madrid",
    )

    assert status == HTTPStatus.OK
    assert payload["authenticated"] is True
    assert payload["has_persistent_twin"] is False
    assert payload["persistent_twin_saved_at"] is None
    assert web._auth_session_payload(payload["session"]["id"])["has_persistent_twin"] is False


def test_verify_code_requires_merge_decision_for_existing_persistent_twin(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(web, "_project_root", lambda: tmp_path)
    _sign_in_and_save_twin(monkeypatch, tmp_path, twin_id="twin_saved")
    web._save_session(
        {
            "twin": {"schema_version": "0.2.0", "twin_id": "twin_new_session"},
            "source_documents": [],
            "enrollment_documents": [],
        }
    )
    delivery = web._request_code_payload(
        email="user@example.com",
        ip_address="127.0.0.1",
    )

    status, payload = web._verify_code_payload(
        email="user@example.com",
        code=delivery["simulated_code"],
        duration="7_days",
        timezone="Europe/Madrid",
    )

    assert status == HTTPStatus.CONFLICT
    assert payload["status"] == "merge_decision_required"
    assert payload["options"] == ["merge_session", "discard_session"]


def test_resolve_merge_can_discard_session_twin_and_load_persistent_twin(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(web, "_project_root", lambda: tmp_path)
    _sign_in_and_save_twin(monkeypatch, tmp_path, twin_id="twin_saved")
    web._save_session(
        {
            "twin": {"schema_version": "0.2.0", "twin_id": "twin_new_session"},
            "source_documents": [],
            "enrollment_documents": [],
        }
    )
    delivery = web._request_code_payload(
        email="user@example.com",
        ip_address="127.0.0.1",
    )
    status, payload = web._verify_code_payload(
        email="user@example.com",
        code=delivery["simulated_code"],
        duration="7_days",
        timezone="Europe/Madrid",
    )
    assert status == HTTPStatus.CONFLICT

    status, resolved = web._resolve_merge_payload(
        session_id=payload["session"]["id"],
        merge_strategy="discard_session",
    )

    assert status == HTTPStatus.OK
    assert resolved["authenticated"] is True
    assert web._load_session()["twin"]["twin_id"] == "twin_saved"


def test_delete_account_requires_exact_confirmation(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(web, "_project_root", lambda: tmp_path)
    session_id = _sign_in_and_save_twin(monkeypatch, tmp_path, twin_id="twin_saved")

    status, payload = web._delete_account_payload(
        session_id=session_id,
        confirmation="yes",
    )
    assert status == HTTPStatus.BAD_REQUEST
    assert "confirmation" in payload["error"]

    status, payload = web._delete_account_payload(
        session_id=session_id,
        confirmation=(
            "Are you sure? Your digital twin will be deleted and cannot be recovered. "
            "You will have to rebuild the Twin if you come back later."
        ),
    )
    assert status == HTTPStatus.OK
    assert payload["status"] == "deleted"
    state = load_json(tmp_path / web.SESSION_DIR / web.ACCOUNT_FILE)
    assert state["users"] == []


def _sign_in_and_save_twin(
    monkeypatch,
    tmp_path: Path,
    *,
    twin_id: str,
) -> str:
    monkeypatch.setattr(web, "_project_root", lambda: tmp_path)
    web._save_session(
        {
            "twin": {"schema_version": "0.2.0", "twin_id": twin_id},
            "source_documents": [],
            "enrollment_documents": [],
        }
    )
    delivery = web._request_code_payload(
        email="user@example.com",
        ip_address="127.0.0.1",
    )
    status, payload = web._verify_code_payload(
        email="user@example.com",
        code=delivery["simulated_code"],
        duration="7_days",
        timezone="Europe/Madrid",
    )
    assert status == HTTPStatus.OK
    return payload["session"]["id"]
