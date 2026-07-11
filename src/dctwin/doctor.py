from __future__ import annotations

import argparse
import os
import shutil
import socket
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path

from dctwin import __version__
from dctwin.local_env import load_dotenv, project_root


VALID_TENANT_ID_CHARACTERS = frozenset(
    "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789-."
)


@dataclass(frozen=True)
class Check:
    level: str
    name: str
    message: str


def _pass(name: str, message: str) -> Check:
    return Check("PASS", name, message)


def _warn(name: str, message: str) -> Check:
    return Check("WARN", name, message)


def _fail(name: str, message: str) -> Check:
    return Check("FAIL", name, message)


def _import_check(module: str, *, timeout_seconds: int = 10) -> Check:
    started = time.perf_counter()
    command = [sys.executable, "-c", f"import {module}"]
    try:
        result = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout_seconds,
            check=False,
        )
    except subprocess.TimeoutExpired:
        return _fail(
            f"import {module}",
            f"Import did not complete within {timeout_seconds}s. Rebuild the virtual environment.",
        )
    elapsed = time.perf_counter() - started
    if result.returncode != 0:
        detail = (result.stderr or result.stdout).strip().splitlines()
        reason = detail[-1] if detail else "unknown import error"
        return _fail(f"import {module}", reason)
    if elapsed > 5:
        return _warn(f"import {module}", f"Import succeeded but took {elapsed:.1f}s")
    return _pass(f"import {module}", f"{elapsed:.1f}s")


def _port_check(host: str, port: int) -> Check:
    try:
        with socket.create_connection((host, port), timeout=0.5):
            return _warn("local port", f"{host}:{port} is already accepting connections")
    except OSError:
        pass

    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as probe:
        probe.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        try:
            probe.bind((host, port))
        except PermissionError:
            return _warn("local port", f"Cannot probe {host}:{port} from this sandbox")
        except OSError as exc:
            return _fail("local port", f"{host}:{port} is not available: {exc}")
    return _pass("local port", f"{host}:{port} is available")


def _writable_check(path: Path, name: str) -> Check:
    try:
        path.mkdir(parents=True, exist_ok=True)
        probe = path / ".ping-write-test"
        probe.write_text("ok", encoding="utf-8")
        probe.unlink(missing_ok=True)
    except OSError as exc:
        return _fail(name, f"{path} is not writable: {exc}")
    return _pass(name, str(path))


def _tenant_id_check() -> Check:
    raw = os.environ.get("AZURE_TENANT_ID")
    if not raw:
        return _warn(
            "AZURE_TENANT_ID",
            "not configured; browser/device-code auth may choose the wrong tenant",
        )

    candidate = raw.strip().strip("{}")
    if not candidate or any(character not in VALID_TENANT_ID_CHARACTERS for character in candidate):
        return _fail(
            "AZURE_TENANT_ID",
            "contains invalid characters; use only the tenant value itself, not labels, quotes, brackets or comments",
        )

    if candidate == "00000000-0000-0000-0000-000000000000":
        return _fail("AZURE_TENANT_ID", "still set to the placeholder all-zero GUID")

    return _pass("AZURE_TENANT_ID", "configured with valid tenant-id characters")


def run_checks(*, host: str = "127.0.0.1", port: int = 8766) -> list[Check]:
    loaded = load_dotenv()
    checks: list[Check] = []

    if sys.version_info >= (3, 11):
        checks.append(_pass("python", sys.version.split()[0]))
    else:
        checks.append(_fail("python", f"{sys.version.split()[0]} found; Python 3.11+ required"))

    try:
        root = project_root()
        checks.append(_pass("project root", str(root)))
    except RuntimeError as exc:
        return [_fail("project root", str(exc))]

    if loaded:
        checks.append(_pass(".env", f"Loaded {', '.join(loaded)}"))
    elif (root / ".env").is_file():
        checks.append(_pass(".env", "Present; values already existed in environment"))
    else:
        checks.append(_warn(".env", "No .env file found; using shell environment only"))

    checks.extend(
        [
            _writable_check(root / ".dctwin-local", "session state"),
            _writable_check(Path(os.environ.get("DCTWIN_STATE_DIR", "~/.dctwin")).expanduser(), "persistent state"),
            _port_check(host, port),
        ]
    )

    for key in ["FOUNDRY_PROJECT_ENDPOINT", "DCTWIN_MODEL_DEPLOYMENT"]:
        value = os.environ.get(key)
        if value:
            checks.append(_pass(key, "configured"))
        else:
            checks.append(_fail(key, "missing; add it to .env or export it in the shell"))

    checks.append(_pass("DCTWIN_MODEL_PATH", os.environ.get("DCTWIN_MODEL_PATH", "staged_extraction")))
    auth_mode = os.environ.get("DCTWIN_AUTH_MODE", "device_code").strip().lower()
    if auth_mode in {"device_code", "browser", "interactive_browser", "auto"}:
        checks.append(_pass("DCTWIN_AUTH_MODE", auth_mode))
    else:
        checks.append(_fail("DCTWIN_AUTH_MODE", "use device_code, browser, interactive_browser or auto"))

    auth_timeout = os.environ.get("DCTWIN_AUTH_TIMEOUT_SECONDS", "180")
    try:
        timeout_seconds = int(auth_timeout)
    except ValueError:
        checks.append(_fail("DCTWIN_AUTH_TIMEOUT_SECONDS", "must be a number of seconds"))
    else:
        if timeout_seconds < 30:
            checks.append(_fail("DCTWIN_AUTH_TIMEOUT_SECONDS", "must be at least 30 seconds"))
        else:
            checks.append(_pass("DCTWIN_AUTH_TIMEOUT_SECONDS", f"{timeout_seconds}s"))

    checks.append(_tenant_id_check())

    for module in ["pypdf", "docx", "azure.identity", "azure.ai.projects"]:
        checks.append(_import_check(module))

    from dctwin.web import _available_azure_auth_methods

    auth_methods = _available_azure_auth_methods()
    if auth_methods:
        checks.append(_pass("azure auth", ", ".join(auth_methods)))
    else:
        checks.append(_fail("azure auth", "No Azure authentication route is available"))

    return checks


def _auth_token_check() -> Check:
    from dctwin.web import _acquire_azure_token, _available_azure_auth_methods

    print(f"\nChecking Azure token using {', '.join(_available_azure_auth_methods())}...")
    try:
        token = _acquire_azure_token()
    except Exception as exc:  # noqa: BLE001 - surface Azure's concrete auth failure
        return _fail("azure token", str(exc).splitlines()[0])

    expires_at = datetime.fromtimestamp(token.expires_on, UTC)
    seconds_remaining = int(token.expires_on - time.time())
    message = f"expires {expires_at.isoformat()} ({max(0, seconds_remaining // 60)} min remaining)"
    if seconds_remaining < 300:
        return _warn("azure token", message)
    return _pass("azure token", message)


def print_report(checks: list[Check]) -> None:
    print(f"Digital Career Twin local ping v{__version__}")
    for check in checks:
        print(f"{check.level:4}  {check.name}: {check.message}")

    failures = [check for check in checks if check.level == "FAIL"]
    warnings = [check for check in checks if check.level == "WARN"]
    if failures:
        print("\nResult: not ready. Fix the FAIL item above and run ping again.")
    elif warnings:
        print("\nResult: ready, with warnings.")
    else:
        print("\nResult: ready.")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Ping the local DCT development environment")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8766)
    parser.add_argument(
        "--auth",
        action="store_true",
        help="Actively acquire an Azure token and report its expiry",
    )
    return parser


def main() -> None:
    args = build_parser().parse_args()
    checks = run_checks(host=args.host, port=args.port)
    if args.auth and not any(check.level == "FAIL" for check in checks):
        checks.append(_auth_token_check())
    print_report(checks)
    raise SystemExit(1 if any(check.level == "FAIL" for check in checks) else 0)


if __name__ == "__main__":
    main()
