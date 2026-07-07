from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from pypdf import PdfReader

from dctwin.adapters.base import AdaptedSource
from dctwin.privacy import minimize_direct_identifiers


class PdfCvAdapter:
    """First source-specific strategy: a text-bearing PDF CV."""

    source_type = "cv"
    name = "pdf_cv"
    version = "0.1.0"

    def supports(self, path: Path) -> bool:
        return path.is_file() and path.suffix.lower() == ".pdf"

    def adapt(self, path: Path) -> AdaptedSource:
        raw_bytes = path.read_bytes()
        digest = hashlib.sha256(raw_bytes).hexdigest()
        source_id = f"src_{digest[:16]}"
        reader = PdfReader(path)
        blocks: list[dict[str, Any]] = []
        enrollment_candidates: list[dict[str, str]] = []
        redaction_counters: dict[str, int] = {}

        for page_number, page in enumerate(reader.pages, start=1):
            extracted = page.extract_text() or ""
            minimized, redactions = minimize_direct_identifiers(
                extracted, counters=redaction_counters
            )
            block_id = f"block_page_{page_number}"
            blocks.append(
                {
                    "id": block_id,
                    "locator": {"kind": "page", "value": str(page_number)},
                    "text": minimized.strip(),
                    "redactions": [
                        {"category": item.category, "placeholder": item.placeholder}
                        for item in redactions
                    ],
                }
            )
            enrollment_candidates.extend(
                {
                    "type": "email",
                    "value": item.value,
                    "source_block_id": block_id,
                    "purpose": "account_enrollment",
                    "verification_status": "unverified",
                }
                for item in redactions
                if item.category == "email"
            )

        if not any(block["text"] for block in blocks):
            raise ValueError("The PDF contains no extractable text; OCR is not implemented yet")

        model_document = {
            "schema_version": "0.1.0",
            "source_id": source_id,
            "source_type": self.source_type,
            "media_type": "application/pdf",
            "content_hash": f"sha256:{digest}",
            "ingested_at": datetime.now(UTC).isoformat(),
            "adapter": {"name": self.name, "version": self.version},
            "privacy": {
                "classification": "personal_data",
                "direct_identifiers_minimized": True,
                "enrollment_candidates_separated": True,
            },
            "blocks": blocks,
        }
        return AdaptedSource(
            model_document=model_document,
            enrollment_document={
                "schema_version": "0.1.0",
                "source_id": source_id,
                "candidates": enrollment_candidates,
            },
        )
