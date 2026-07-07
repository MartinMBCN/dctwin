from __future__ import annotations

from copy import deepcopy
from pathlib import Path

from dctwin.io import load_json
from dctwin.reconciliation import ReconciliationAgent
from dctwin.validation import validate_source_document, validate_twin


ROOT = Path(__file__).resolve().parents[1]


def test_reconciliation_merges_duplicate_evidence_as_provenance() -> None:
    existing = load_json(ROOT / "tests/fixtures/valid_twin.json")
    incoming = deepcopy(existing)
    incoming["sources"][0] = {
        **incoming["sources"][0],
        "id": "src_second_cv",
        "label": "Second CV",
        "content_hash": "sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb",
    }
    for ref in incoming["roles"][0]["source_refs"]:
        ref["source_id"] = "src_second_cv"
    for ref in incoming["evidence_items"][0]["source_refs"]:
        ref["source_id"] = "src_second_cv"

    updated, summary = ReconciliationAgent().reconcile(
        existing_twin=existing,
        candidate_twin=incoming,
    )

    assert summary.evidence_merged == 1
    assert summary.evidence_added == 0
    assert len(updated["evidence_items"]) == 1
    assert {
        ref["source_id"] for ref in updated["evidence_items"][0]["source_refs"]
    } == {"src_synthetic_cv", "src_second_cv"}


def test_manual_achievement_updates_twin_with_user_entered_source() -> None:
    twin = load_json(ROOT / "tests/fixtures/valid_twin.json")
    catalog = load_json(ROOT / "catalogs/tag_catalog.json")
    schema = load_json(ROOT / "schemas/digital_career_twin.schema.json")
    source_schema = load_json(ROOT / "schemas/source_document.schema.json")

    updated, source_doc, summary = ReconciliationAgent().add_manual_evidence(
        twin=twin,
        role_id="role_acme_platform_lead",
        text="Improved release reliability by 20% with automated checks.",
        tag_catalog=catalog,
    )

    assert source_doc["source_type"] == "user_entered_data"
    assert summary.evidence_added == 1
    assert len(updated["evidence_items"]) == 2
    validate_source_document(source_doc, source_schema)
    validate_twin(updated, schema, catalog, source_documents=[source_doc])
