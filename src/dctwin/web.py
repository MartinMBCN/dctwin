from __future__ import annotations

import argparse
import json
import os
import tempfile
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path
from typing import Any
from urllib.parse import unquote

from dctwin.adapters import AdapterRegistry, DocxCvAdapter, PdfCvAdapter
from dctwin.agent import SourceAdapterAgent
from dctwin.foundry import FoundryTwinProvider
from dctwin.io import load_json


MAX_UPLOAD_BYTES = 15 * 1024 * 1024


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
                    "formats": ["pdf", "docx"],
                    "foundry": "ready" if _foundry_configured() else "not_configured",
                },
            )
        else:
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "Not found"})

    def do_POST(self) -> None:  # noqa: N802
        if self.path != "/api/adapt":
            self._send_json(HTTPStatus.NOT_FOUND, {"error": "Not found"})
            return
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
        try:
            with tempfile.NamedTemporaryFile(suffix=suffix, delete=False) as temporary:
                temporary.write(self.rfile.read(length))
                temporary_path = Path(temporary.name)

            registry = AdapterRegistry()
            registry.register(PdfCvAdapter())
            registry.register(DocxCvAdapter())
            adapted = registry.adapt("cv", temporary_path)
            if not _foundry_configured():
                self._send_json(
                    HTTPStatus.SERVICE_UNAVAILABLE,
                    {"error": "The local agent is not connected to a Foundry model deployment"},
                )
                return

            from azure.identity import AzureDeveloperCliCredential

            contracts = _contracts()
            provider = FoundryTwinProvider.from_files(
                project_endpoint=os.environ["FOUNDRY_PROJECT_ENDPOINT"],
                model_deployment=os.environ["DCTWIN_MODEL_DEPLOYMENT"],
                credential=AzureDeveloperCliCredential(process_timeout=30),
                project_root=_project_root(),
            )
            try:
                agent = SourceAdapterAgent(
                    registry=registry,
                    provider=provider,
                    source_schema=contracts["source"],
                    enrollment_schema=contracts["enrollment"],
                    twin_schema=contracts["twin"],
                    tag_catalog=contracts["catalog"],
                )
                run = agent.run_adapted(adapted)
            finally:
                provider.close()

            model = run.source_document
            enrollment = run.enrollment_document
            self._send_json(
                HTTPStatus.OK,
                {
                    "source": model,
                    "enrollment": enrollment,
                    "twin": run.candidate_twin,
                    "summary": {
                        "filename": filename,
                        "adapter": model["adapter"]["name"],
                        "blocks": len(model["blocks"]),
                        "redactions": sum(
                            len(block["redactions"]) for block in model["blocks"]
                        ),
                        "enrollment_candidates": len(enrollment["candidates"]),
                    },
                    "agent": {
                        "status": "complete",
                        "message": "The local Source Adapter Agent generated and validated this Twin through the configured Foundry model.",
                    },
                },
            )
        except Exception as exc:
            self._send_json(
                HTTPStatus.UNPROCESSABLE_ENTITY,
                {"error": f"The document could not be adapted: {exc}"},
            )
        finally:
            if temporary_path is not None:
                temporary_path.unlink(missing_ok=True)

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
