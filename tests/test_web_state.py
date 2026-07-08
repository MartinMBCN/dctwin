from __future__ import annotations

import re
from http import HTTPStatus
from pathlib import Path

import pytest

from dctwin import web
from dctwin.io import load_json


def test_reset_session_clears_session_and_cache(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(web, "_project_root", lambda: tmp_path)
    monkeypatch.setenv("DCTWIN_STATE_DIR", str(tmp_path / "persistent_state"))
    state_dir = tmp_path / web.SESSION_DIR
    session_file = state_dir / web.SESSION_FILE
    cache_file = state_dir / web.CACHE_DIR / "source.candidate.json"
    account_file = _account_file(tmp_path)
    session_file.parent.mkdir(parents=True)
    cache_file.parent.mkdir(parents=True)
    account_file.parent.mkdir(parents=True)
    session_file.write_text("{}", encoding="utf-8")
    cache_file.write_text("{}", encoding="utf-8")
    account_file.write_text("{}", encoding="utf-8")

    web._reset_session()

    assert not session_file.exists()
    assert not cache_file.exists()
    assert account_file.exists()


def test_account_repository_uses_stable_state_dir(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(web, "_project_root", lambda: tmp_path / "checkout_a")
    monkeypatch.setenv("DCTWIN_STATE_DIR", str(tmp_path / "persistent_state"))

    repo = web._account_repository()
    delivery = repo.request_login_code(
        email="user@example.com",
        ip_address="127.0.0.1",
    )
    repo.verify_login_code(email="user@example.com", code=delivery.code)

    monkeypatch.setattr(web, "_project_root", lambda: tmp_path / "checkout_b")

    assert web._account_repository().get_user_by_email(email="user@example.com")
    assert not (tmp_path / "checkout_a" / web.SESSION_DIR / web.ACCOUNT_FILE).exists()
    assert not (tmp_path / "checkout_b" / web.SESSION_DIR / web.ACCOUNT_FILE).exists()
    assert (tmp_path / "persistent_state" / web.ACCOUNT_FILE).exists()


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
    monkeypatch.setenv("DCTWIN_STATE_DIR", str(tmp_path / "persistent_state"))
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
    assert auth_session["account"]["created_at"]
    assert auth_session["account"]["last_login_at"]
    assert auth_session["account"]["login_count"] == 1
    assert auth_session["account"]["last_twin_saved_at"]

    state = load_json(_account_file(tmp_path))
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
    state = load_json(_account_file(tmp_path))
    assert state["users"][0]["persistent_twin"]["twin"]["twin_id"] == "twin_saved"
    assert web._auth_session_payload(session_id)["authenticated"] is False


def test_create_account_requires_session_twin(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(web, "_project_root", lambda: tmp_path)

    with pytest.raises(ValueError, match="Create a Digital Career Twin"):
        web._request_code_payload(
            email="empty@example.com",
            ip_address="127.0.0.1",
            purpose="create_account",
        )


def test_sign_in_requires_existing_saved_twin(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(web, "_project_root", lambda: tmp_path)
    monkeypatch.setenv("DCTWIN_STATE_DIR", str(tmp_path / "persistent_state"))
    repo = web._account_repository()
    delivery = repo.request_login_code(
        email="empty@example.com",
        ip_address="127.0.0.1",
    )
    repo.verify_login_code(email="empty@example.com", code=delivery.code)

    with pytest.raises(ValueError, match="No saved Digital Career Twin"):
        web._request_code_payload(
            email="empty@example.com",
            ip_address="127.0.0.1",
            purpose="sign_in",
        )


def test_sign_in_reports_missing_deleted_account(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(web, "_project_root", lambda: tmp_path)
    monkeypatch.setenv("DCTWIN_STATE_DIR", str(tmp_path / "persistent_state"))

    with pytest.raises(ValueError, match="No account found"):
        web._request_code_payload(
            email="deleted@example.com",
            ip_address="127.0.0.1",
            purpose="sign_in",
        )


def test_deleted_account_email_can_be_reused(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(web, "_project_root", lambda: tmp_path)
    monkeypatch.setenv("DCTWIN_STATE_DIR", str(tmp_path / "persistent_state"))
    session_id = _sign_in_and_save_twin(monkeypatch, tmp_path, twin_id="twin_deleted")
    status, payload = web._delete_account_payload(
        session_id=session_id,
        confirmation=(
            "Are you sure? Your digital twin will be deleted and cannot be recovered. "
            "You will have to rebuild the Twin if you come back later."
        ),
    )
    assert status == HTTPStatus.OK

    web._save_session(
        {
            "twin": {"schema_version": "0.2.0", "twin_id": "twin_recreated"},
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
    assert payload["authenticated"] is True
    assert payload["has_persistent_twin"] is True
    assert load_json(_account_file(tmp_path))["users"][0]["persistent_twin"]["twin"]["twin_id"] == "twin_recreated"


def test_sign_in_loads_existing_saved_twin(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(web, "_project_root", lambda: tmp_path)
    session_id = _sign_in_and_save_twin(monkeypatch, tmp_path, twin_id="twin_saved")
    web._logout_payload(session_id)
    delivery = web._request_code_payload(
        email="user@example.com",
        ip_address="127.0.0.1",
        purpose="sign_in",
    )

    status, payload = web._verify_code_payload(
        email="user@example.com",
        code=delivery["simulated_code"],
        duration="7_days",
        timezone="Europe/Madrid",
        purpose="sign_in",
    )

    assert status == HTTPStatus.OK
    assert payload["authenticated"] is True
    assert payload["has_persistent_twin"] is True
    assert web._load_session()["twin"]["twin_id"] == "twin_saved"


def test_persistent_twin_survives_app_version_change(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(web, "_project_root", lambda: tmp_path)
    monkeypatch.setattr(web, "__version__", "0.2.6")
    session_id = _sign_in_and_save_twin(monkeypatch, tmp_path, twin_id="twin_saved")
    assert web._health_payload()["app_version"] == "0.2.6"
    web._logout_payload(session_id)

    monkeypatch.setattr(web, "__version__", "0.2.7")
    delivery = web._request_code_payload(
        email="user@example.com",
        ip_address="127.0.0.1",
        purpose="sign_in",
    )
    status, payload = web._verify_code_payload(
        email="user@example.com",
        code=delivery["simulated_code"],
        duration="7_days",
        timezone="Europe/Madrid",
        purpose="sign_in",
    )

    assert web._health_payload()["app_version"] == "0.2.7"
    assert status == HTTPStatus.OK
    assert payload["has_persistent_twin"] is True
    assert web._load_session()["twin"]["twin_id"] == "twin_saved"


def test_authenticated_session_update_saves_persistent_twin(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(web, "_project_root", lambda: tmp_path)
    session_id = _sign_in_and_save_twin(monkeypatch, tmp_path, twin_id="twin_saved")
    web._save_session(
        {
            "twin": {"schema_version": "0.2.0", "twin_id": "twin_updated"},
            "source_documents": [{"source_id": "src_updated"}],
            "enrollment_documents": [{"source_id": "src_updated", "candidates": []}],
        }
    )

    record = web._save_authenticated_session_twin(session_id)

    assert record is not None
    assert record["twin"]["twin_id"] == "twin_updated"
    state = load_json(_account_file(tmp_path))
    assert state["users"][0]["persistent_twin"]["twin"]["twin_id"] == "twin_updated"
    assert state["users"][0]["persistent_twin"]["source_documents"] == [
        {"source_id": "src_updated"}
    ]


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
    state = load_json(_account_file(tmp_path))
    assert state["users"] == []


def _sign_in_and_save_twin(
    monkeypatch,
    tmp_path: Path,
    *,
    twin_id: str,
) -> str:
    monkeypatch.setattr(web, "_project_root", lambda: tmp_path)
    monkeypatch.setenv("DCTWIN_STATE_DIR", str(tmp_path / "persistent_state"))
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


def _account_file(tmp_path: Path) -> Path:
    return tmp_path / "persistent_state" / web.ACCOUNT_FILE
