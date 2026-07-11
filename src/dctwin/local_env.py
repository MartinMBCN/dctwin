from __future__ import annotations

import os
from pathlib import Path


def project_root() -> Path:
    for candidate in [Path.cwd(), *Path(__file__).resolve().parents]:
        if (candidate / "src/web/index.html").is_file():
            return candidate
    raise RuntimeError("Run local DCT commands from the repository root")


def load_dotenv(path: Path | None = None) -> list[str]:
    """Load simple KEY=VALUE pairs from .env without adding a runtime dependency."""

    env_path = path or project_root() / ".env"
    if not env_path.is_file():
        return []

    loaded: list[str] = []
    for raw_line in env_path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip().strip("'\"")
        if " #" in value:
            value = value.split(" #", 1)[0].strip().strip("'\"")
        if not key or key in os.environ:
            continue
        os.environ[key] = value
        loaded.append(key)
    return loaded
