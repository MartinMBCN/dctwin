from __future__ import annotations

from pathlib import Path

from dctwin import web


def test_reset_session_clears_session_and_cache(
    monkeypatch,
    tmp_path: Path,
) -> None:
    monkeypatch.setattr(web, "_project_root", lambda: tmp_path)
    state_dir = tmp_path / web.SESSION_DIR
    session_file = state_dir / web.SESSION_FILE
    cache_file = state_dir / web.CACHE_DIR / "source.candidate.json"
    session_file.parent.mkdir(parents=True)
    cache_file.parent.mkdir(parents=True)
    session_file.write_text("{}", encoding="utf-8")
    cache_file.write_text("{}", encoding="utf-8")

    web._reset_session()

    assert not state_dir.exists()
