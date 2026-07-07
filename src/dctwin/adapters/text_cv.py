from __future__ import annotations

import hashlib
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from dctwin.adapters.base import AdaptedSource
from dctwin.privacy import minimize_direct_identifiers


class TextCvAdapter:
    """CV strategy for pasted or plain-text CV material."""

    source_type = "cv"
    name = "text_cv"
    version = "0.1.0"

    def supports(self, path: Path) -> bool:
        return path.is_file() and path.suffix.lower() in {".txt", ".text"}

    def adapt(self, path: Path) -> AdaptedSource:
        text = path.read_text(encoding="utf-8")
        label = path.stem.replace("_", " ").strip() or "Manually entered CV"
        return adapt_cv_text(text, label=label, content_identity=text)


def adapt_cv_text(
    text: str,
    *,
    label: str,
    content_identity: str | bytes | None = None,
) -> AdaptedSource:
    if not text.strip():
        raise ValueError("The pasted CV text is empty")

    identity = content_identity if content_identity is not None else text
    raw_bytes = identity if isinstance(identity, bytes) else identity.encode("utf-8")
    digest = hashlib.sha256(raw_bytes).hexdigest()
    source_id = f"src_{digest[:16]}"
    blocks: list[dict[str, Any]] = []
    enrollment_candidates: list[dict[str, str]] = []
    redaction_counters: dict[str, int] = {}

    for block_number, block_text in enumerate(_text_blocks(text), start=1):
        block_id = f"block_text_{block_number}"
        minimized, redactions = minimize_direct_identifiers(
            block_text,
            counters=redaction_counters,
        )
        blocks.append(
            {
                "id": block_id,
                "locator": {"kind": "section", "value": str(block_number)},
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

    model_document = {
        "schema_version": "0.1.0",
        "source_id": source_id,
        "source_type": "cv",
        "media_type": "text/plain",
        "content_hash": f"sha256:{digest}",
        "ingested_at": datetime.now(UTC).isoformat(),
        "adapter": {"name": "text_cv", "version": TextCvAdapter.version},
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


def _text_blocks(text: str) -> list[str]:
    paragraphs = [
        paragraph.strip()
        for paragraph in text.replace("\r\n", "\n").split("\n\n")
        if paragraph.strip()
    ]
    if len(paragraphs) > 1:
        return paragraphs
    return [line.strip() for line in text.splitlines() if line.strip()]
