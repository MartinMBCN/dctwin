from __future__ import annotations

from pathlib import Path

from dctwin.io import load_json
from dctwin.twin_builder import build_twin_from_extraction
from dctwin.validation import validate_twin


ROOT = Path(__file__).resolve().parents[1]


def test_build_twin_from_compact_extraction_produces_valid_dct() -> None:
    source = load_json(ROOT / "tests/fixtures/valid_source.json")
    catalog = load_json(ROOT / "catalogs/tag_catalog.json")
    schema = load_json(ROOT / "schemas/digital_career_twin.schema.json")
    extraction = {
        "source_label": "Synthetic CV",
        "person_name": "Alex Example",
        "roles": [
            {
                "id": "r1",
                "title": "Platform Lead",
                "organization": "ACME",
                "start_date": "2022",
                "end_date": "2025",
                "summary": "Led a reusable delivery platform.",
                "source_block_id": "block_page_1",
                "quote": "ACME — Platform Lead, 2022–2025",
                "confidence": 0.9,
            }
        ],
        "achievements": [
            {
                "text": "Reduced deployment time by 60% through a reusable delivery platform.",
                "role_id": "r1",
                "role_index": 0,
                "context": None,
                "source_block_id": "block_page_1",
                "quote": "Reduced deployment time by 60% through a reusable delivery platform.",
                "confidence": 0.95,
            }
        ],
        "interpretation": {
            "reflection_summary": "Alex shows a pattern of platform work that turns reusable systems into measurable delivery improvement.",
            "recurring_patterns": [
                {
                    "text": "Reusable platform mechanisms are connected to measurable delivery outcomes.",
                    "supporting_achievement_indexes": [0],
                }
            ],
            "capability_hypotheses": [
                {
                    "value": "Platform engineering for delivery acceleration",
                    "confidence": 0.78,
                    "rationale": "The achievement links a reusable platform to a quantified deployment-time reduction.",
                    "supporting_achievement_indexes": [0],
                    "alternatives": ["Delivery improvement with one platform example"],
                }
            ],
            "unclear_questions": ["What was the adoption scope of the platform?"],
        },
    }

    twin = build_twin_from_extraction(
        extraction=extraction,
        source_document=source,
        tag_catalog=catalog,
    )

    assert twin["roles"][0]["title"] == "Platform Lead"
    assert twin["evidence_items"][0]["role_id"] == twin["roles"][0]["id"]
    assert twin["evidence_items"][0]["tag_assignments"]["capabilities"]
    assert twin["reflection"]["summary"].startswith("Alex shows a pattern")
    assert twin["inferences"][0]["value"] == "Platform engineering for delivery acceleration"
    validate_twin(twin, schema, catalog, source_documents=[source])
