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


def test_reconciliation_merges_rephrased_evidence_with_shared_metric_and_entities() -> None:
    existing = _twin_with_evidence(
        "Identified supplier-driven cost anomaly and avoided up to $900K in non-value spend."
    )
    incoming = _twin_with_evidence(
        "Avoided up to $900K in non-value spend by identifying supplier-caused spend anomaly and modelling risk across cohorts.",
        source_id="src_second_cv",
    )

    updated, summary = ReconciliationAgent().reconcile(
        existing_twin=existing,
        candidate_twin=incoming,
    )

    assert summary.evidence_merged == 1
    assert summary.evidence_added == 0
    assert len(updated["evidence_items"]) == 1


def test_reconciliation_merges_rephrased_scaling_evidence_with_shared_numbers() -> None:
    existing = _twin_with_evidence(
        "Scaled marketplace engineering from 18 to 60 staff supporting expansion to 11 marketplaces and 2 new markets generating >€180M."
    )
    incoming = _twin_with_evidence(
        "Scaled marketplace engineering from 18 to 60 staff and enabled expansion into two markets generating >€180M.",
        source_id="src_second_cv",
    )

    updated, summary = ReconciliationAgent().reconcile(
        existing_twin=existing,
        candidate_twin=incoming,
    )

    assert summary.evidence_merged == 1
    assert len(updated["evidence_items"]) == 1


def test_reconciliation_merges_partial_overlap_evidence_with_shared_core_event_and_metric() -> None:
    existing = _twin_with_evidence(
        "Launched support chatbot and scaled adoption from 4,000 beta users to 1.8M customers in five months."
    )
    incoming = _twin_with_evidence(
        "Launched support chatbot, scaled to 1.8M customers in five months, reducing support calls 12%.",
        source_id="src_second_cv",
    )

    updated, summary = ReconciliationAgent().reconcile(
        existing_twin=existing,
        candidate_twin=incoming,
    )

    assert summary.evidence_merged == 1
    assert summary.evidence_added == 0
    assert len(updated["evidence_items"]) == 1


def test_reconciliation_merges_similar_capability_hypotheses() -> None:
    existing = _twin_with_evidence(
        "Reduced AWS costs by 37% through Kubernetes transformation.",
        inference_value="Delivers measurable cost savings and reliability improvements through platform engineering and cloud rationalization",
    )
    incoming = _twin_with_evidence(
        "Increased release frequency and avoided $1M spend through cloud transformation.",
        source_id="src_second_cv",
        inference_value="Delivers measurable cost and delivery improvements through platform engineering and cloud transformation",
    )

    updated, _summary = ReconciliationAgent().reconcile(
        existing_twin=existing,
        candidate_twin=incoming,
    )

    assert len(updated["inferences"]) == 1
    assert len(updated["inferences"][0]["supporting_evidence_ids"]) == 2


def _twin_with_evidence(
    text: str,
    *,
    source_id: str = "src_synthetic_cv",
    inference_value: str = "Platform and cost optimization capability",
) -> dict:
    twin = load_json(ROOT / "tests/fixtures/valid_twin.json")
    twin["sources"][0]["id"] = source_id
    twin["sources"][0]["content_hash"] = (
        "sha256:aaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaaa"
        if source_id == "src_synthetic_cv"
        else "sha256:bbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbbb"
    )
    for role in twin["roles"]:
        role["source_refs"][0]["source_id"] = source_id
    evidence = twin["evidence_items"][0]
    evidence["id"] = f"ev_{source_id.removeprefix('src_')}"
    evidence["text"] = text
    evidence["source_refs"][0]["source_id"] = source_id
    evidence["source_refs"][0]["quote"] = text
    twin["inferences"][0]["value"] = inference_value
    twin["inferences"][0]["supporting_evidence_ids"] = [evidence["id"]]
    twin["reflection"]["summary"] = "Technology leadership pattern with measurable platform outcomes."
    twin["reflection"]["strongly_supported"] = [inference_value]
    return twin
