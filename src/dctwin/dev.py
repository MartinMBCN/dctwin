from __future__ import annotations

import argparse
import sys

from dctwin.doctor import print_report, run_checks
from dctwin.local_env import load_dotenv


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Run the local DCT preview with environment checks")
    parser.add_argument("--host", default="127.0.0.1")
    parser.add_argument("--port", type=int, default=8766)
    parser.add_argument("--reset", action="store_true", help="Clear local session/cache before starting")
    parser.add_argument("--refresh-auth", action="store_true", help="Acquire an Azure token before starting")
    parser.add_argument("--skip-ping", action="store_true", help="Start without preflight checks")
    return parser


def main() -> None:
    args = build_parser().parse_args()
    load_dotenv()

    if not args.skip_ping:
        checks = run_checks(host=args.host, port=args.port)
        print_report(checks)
        if any(check.level == "FAIL" for check in checks):
            raise SystemExit(1)

    if args.reset:
        from dctwin.web import _reset_session

        _reset_session()
        print("Cleared local session and cache.")

    if args.refresh_auth:
        from datetime import UTC, datetime

        from dctwin.web import _acquire_azure_token

        print("Refreshing Azure credentials before starting the local server...")
        token = _acquire_azure_token()
        print(f"Azure credentials ready until {datetime.fromtimestamp(token.expires_on, UTC).isoformat()}.")

    from dctwin.web import main as web_main

    sys.argv = ["dctwin-web"]
    web_main(["--host", args.host, "--port", str(args.port)])


if __name__ == "__main__":
    main()
