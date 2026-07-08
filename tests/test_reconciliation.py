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


def test_manual_achievements_split_non_empty_lines_for_one_role() -> None:
    twin = load_json(ROOT / "tests/fixtures/valid_twin.json")
    catalog = load_json(ROOT / "catalogs/tag_catalog.json")
    source_schema = load_json(ROOT / "schemas/source_document.schema.json")

    updated, source_doc, summary = ReconciliationAgent().add_manual_evidence(
        twin=twin,
        role_id="role_acme_platform_lead",
        text=(
            "Reduced incident response time by 25% with clearer escalation paths.\n\n"
            "Improved onboarding by creating a reusable engineering playbook."
        ),
        tag_catalog=catalog,
    )

    added = updated["evidence_items"][-2:]
    assert summary.evidence_extracted == 2
    assert summary.evidence_added == 2
    assert len(source_doc["blocks"]) == 2
    assert {item["role_id"] for item in added} == {"role_acme_platform_lead"}
    assert {ref["block_id"] for item in added for ref in item["source_refs"]} == {
        "block_manual_1",
        "block_manual_2",
    }
    validate_source_document(source_doc, source_schema)


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


def test_reconciliation_remaps_overview_brief_item_evidence_refs() -> None:
    existing = _twin_with_evidence("Reduced deployment time by 60% with a reusable platform.")
    incoming = _twin_with_evidence(
        "Reduced deployment time by 60% through a reusable delivery platform.",
        source_id="src_second_cv",
    )
    incoming_evidence_id = incoming["evidence_items"][0]["id"]
    incoming["reflection"]["overview_brief_items"] = [
        {
            "id": "brief_incoming",
            "section": "areas_of_higher_confidence",
            "kind": "observation",
            "text": "The quantified deployment-time improvement is directly stated in the source.",
            "salience": 0.8,
            "confidence": 0.9,
            "supporting_evidence_ids": [incoming_evidence_id],
        }
    ]

    updated, summary = ReconciliationAgent().reconcile(
        existing_twin=existing,
        candidate_twin=incoming,
    )

    assert summary.evidence_merged == 1
    assert incoming_evidence_id not in {
        evidence["id"] for evidence in updated["evidence_items"]
    }
    brief_item = next(
        item
        for item in updated["reflection"]["overview_brief_items"]
        if item["id"] == "brief_incoming"
    )
    assert brief_item["supporting_evidence_ids"] == [existing["evidence_items"][0]["id"]]


def test_reconciliation_merges_similar_overview_brief_items() -> None:
    existing = _twin_with_evidence("Reduced AWS costs by 37% and saved $1.1M annually.")
    incoming = _twin_with_evidence(
        "Reduced cloud costs by 37%, saving $1.1M per year.",
        source_id="src_second_cv",
    )
    evidence_ids = [
        existing["evidence_items"][0]["id"],
        incoming["evidence_items"][0]["id"],
    ]
    existing["reflection"]["overview_brief_items"] = [
        _brief_item(
            "career_in_brief",
            "Approximately 12+ years in senior technology transformation and delivery roles from 2014–2026 across banking, retail, consulting, and AI/healthcare.",
            evidence_ids[0],
        ),
        _brief_item(
            "patterns_and_structural_observations",
            "Frequent engagement model includes interim/contract and consultancy roles at enterprise clients and vendors.",
            evidence_ids[0],
        ),
        _brief_item(
            "areas_of_higher_confidence",
            "Consistent delivery of measurable operational outcomes: cost reductions (AWS 37%, $1.1M), throughput/release frequency increases (4x), and reliability improvements.",
            evidence_ids[0],
        ),
        _brief_item(
            "areas_of_less_clarity",
            "Employment continuity and exact role seniority prior to 2014 are not detailed; earlier career timeline is incomplete.",
            evidence_ids[0],
        ),
        _brief_item(
            "professionally_salient_attention_items",
            "Recent DATAVANT Enterprise AI Transformation Lead role duration is short (Dec 2025–Jun 2026); interviewer may ask about scope, handover, or reason for six-month tenure.",
            evidence_ids[0],
        ),
    ]
    incoming["reflection"]["overview_brief_items"] = [
        _brief_item(
            "career_in_brief",
            "Career includes multiple senior technology and transformation roles from 2014 to 2026 across banking, life sciences, ecommerce, and SaaS.",
            evidence_ids[1],
        ),
        _brief_item(
            "patterns_and_structural_observations",
            "Frequent short-to-medium term engagements including multiple contract roles and consulting engagements.",
            evidence_ids[1],
        ),
        _brief_item(
            "areas_of_higher_confidence",
            "Demonstrated ability to produce quantified outcomes: AWS cost reduction ($1.1M, 37%), revenue enablement (>€200M), release frequency x4, chatbot adoption to 2.3M users, and avoided $1M spend.",
            evidence_ids[1],
        ),
        _brief_item(
            "areas_of_less_clarity",
            "Duration and reporting lines for earlier roles before 2014 are not provided; employment type varies and is not always explicit for every role.",
            evidence_ids[1],
        ),
        _brief_item(
            "professionally_salient_attention_items",
            "Recent short tenure as Enterprise AI Transformation Lead (Dec 2025–Jun 2026) may prompt questions about scope, handoff, or program outcome.",
            evidence_ids[1],
        ),
    ]

    updated, _summary = ReconciliationAgent().reconcile(
        existing_twin=existing,
        candidate_twin=incoming,
    )

    sections = [
        item["section"]
        for item in updated["reflection"]["overview_brief_items"]
        if item["section"] != "confidence_statement"
    ]
    assert sections.count("career_in_brief") == 1
    assert sections.count("patterns_and_structural_observations") == 0
    assert sections.count("areas_of_higher_confidence") == 1
    assert sections.count("areas_of_less_clarity") == 1
    assert sections.count("professionally_salient_attention_items") == 1
    assert not any(
        "reason for six-month" in item["text"].lower()
        for item in updated["reflection"]["overview_brief_items"]
    )


def test_reconciliation_merges_confidence_and_capability_adjacent_brief_items() -> None:
    existing = _twin_with_evidence("Designed MEL frameworks and KPI dashboards for AI-enabled health programs.")
    incoming = _twin_with_evidence(
        "Operationalized MEL systems and large-scale monitoring dashboards for digital health programs.",
        source_id="src_second_cv",
    )
    existing_id = existing["evidence_items"][0]["id"]
    incoming_id = incoming["evidence_items"][0]["id"]
    existing["reflection"]["overview_brief_items"] = [
        _brief_item(
            "areas_of_higher_confidence",
            "Demonstrated capacity to design and implement MEL frameworks for AI-enabled health programs, including KPI development and Theory of Change facilitation.",
            existing_id,
        ),
        _brief_item(
            "confidence_statement",
            "Most role dates, project budgets, and quantified outcomes are directly stated in the source; overall extraction confidence is high.",
            existing_id,
        ),
    ]
    incoming["reflection"]["overview_brief_items"] = [
        _brief_item(
            "areas_of_higher_confidence",
            "Proven capability in designing and operationalizing MEL systems and large-scale monitoring, including dashboards and performance frameworks.",
            incoming_id,
        ),
        _brief_item(
            "confidence_statement",
            "Most role descriptions and outputs are supported by specific projects, dates, and publications; confidence in extracted facts is high.",
            incoming_id,
        ),
    ]

    updated, _summary = ReconciliationAgent().reconcile(
        existing_twin=existing,
        candidate_twin=incoming,
    )

    brief_items = updated["reflection"]["overview_brief_items"]
    assert [
        item["section"] for item in brief_items
    ].count("areas_of_higher_confidence") == 1
    assert [
        item["section"] for item in brief_items
    ].count("confidence_statement") == 1


def test_reconciliation_normalizes_overview_brief_item_sections_and_drops_logistics() -> None:
    existing = _twin_with_evidence("Reduced AWS costs by 37% and saved $1.1M annually.")
    incoming = _twin_with_evidence(
        "Led short-term contract transformation work through June 2026.",
        source_id="src_second_cv",
    )
    incoming_id = incoming["evidence_items"][0]["id"]
    incoming["reflection"]["overview_brief_items"] = [
        _brief_item(
            "career_in_brief",
            "Demonstrated record of quantified operational impact (cost reductions, throughput, automation) across multiple roles (examples: $1.1M AWS savings; 37% cost reduction; 5–12x ROI).",
            incoming_id,
        ),
        _brief_item(
            "areas_of_less_clarity",
            "Current availability or notice period is not stated.",
            incoming_id,
        ),
        _brief_item(
            "areas_of_less_clarity",
            "Employment status and reason for short 2025–2026 role length is not explained.",
            incoming_id,
        ),
        _brief_item(
            "patterns_and_structural_observations",
            "Multiple short-duration roles may indicate portfolio consulting focus or frequent transitions—clarify preference for permanent vs contract work.",
            incoming_id,
        ),
    ]

    updated, _summary = ReconciliationAgent().reconcile(
        existing_twin=existing,
        candidate_twin=incoming,
    )

    items = updated["reflection"]["overview_brief_items"]
    assert any(
        item["section"] == "areas_of_higher_confidence"
        and "quantified operational impact" in item["text"]
        for item in items
    )
    assert not any("availability or notice period" in item["text"] for item in items)
    assert not any("reason for short" in item["text"] for item in items)
    assert any(
        item["section"] == "professionally_salient_attention_items"
        and "contract" in item["text"].lower()
        for item in items
    )


def test_reconciliation_merges_overview_brief_domain_duplicates() -> None:
    existing = _twin_with_evidence("Reduced AWS costs by 37% and saved $1.1M annually.")
    incoming = _twin_with_evidence(
        "Avoided $1M in vendor spend and increased release frequency by 4x.",
        source_id="src_second_cv",
    )
    evidence_ids = [
        existing["evidence_items"][0]["id"],
        incoming["evidence_items"][0]["id"],
    ]
    existing["reflection"]["overview_brief_items"] = [
        _brief_item(
            "career_in_brief",
            "Career spans senior transformation and platform leadership roles from 2014 to 2026 across financial services, retail, consulting, and life sciences.",
            evidence_ids[0],
        ),
        _brief_item(
            "areas_of_higher_confidence",
            "Consistent track record of quantified operational impact: cost reductions (AWS 37%, $1.1M), reliability improvements (36% failure reduction), and delivery velocity gains (4x releases).",
            evidence_ids[0],
        ),
        _brief_item(
            "professionally_salient_attention_items",
            "Frequently engaged in short-to-medium term consulting or contract roles focused on transformation and scaling engineering organisations.",
            evidence_ids[0],
        ),
        _brief_item(
            "areas_of_less_clarity",
            "Current role durations and exact reporting lines suggest promotion but scope and handoff details are limited.",
            evidence_ids[0],
        ),
    ]
    incoming["reflection"]["overview_brief_items"] = [
        _brief_item(
            "career_in_brief",
            "~20-year career with repeated senior roles in technology, operations and transformation across multiple industries and geographies.",
            evidence_ids[1],
        ),
        _brief_item(
            "areas_of_higher_confidence",
            "Proven ability to deliver quantified outcomes (cost reductions: $1.1M AWS; 37% cost; avoided $1M; ROI 5–12x; release frequency ×4; onboarding reduced from ~180h to <15m).",
            evidence_ids[1],
        ),
        _brief_item(
            "professionally_salient_attention_items",
            "Multiple short contracts (6–18 months) may reflect targeted transformation engagements rather than permanent placements; verify candidate preference for permanent vs. contract roles.",
            evidence_ids[1],
        ),
        _brief_item(
            "areas_of_less_clarity",
            "Recent role duration is short; scope and long-term ownership of outcomes beyond implementation unclear.",
            evidence_ids[1],
        ),
    ]

    updated, _summary = ReconciliationAgent().reconcile(
        existing_twin=existing,
        candidate_twin=incoming,
    )

    items = updated["reflection"]["overview_brief_items"]
    sections = [item["section"] for item in items]
    assert sections.count("career_in_brief") == 1
    assert sections.count("areas_of_higher_confidence") == 1
    assert sections.count("professionally_salient_attention_items") == 1
    assert not any("handoff" in item["text"].lower() for item in items)
    assert not any("long-term ownership" in item["text"].lower() for item in items)


def test_reconciliation_refiles_uncertainty_and_drops_non_cv_native_caveats() -> None:
    existing = _twin_with_evidence("Designed governance and operating models for regulated organizations.")
    incoming = _twin_with_evidence(
        "Held several short consulting engagements focused on transformation delivery.",
        source_id="src_second_cv",
    )
    evidence_ids = [
        existing["evidence_items"][0]["id"],
        incoming["evidence_items"][0]["id"],
    ]
    existing["reflection"]["overview_brief_items"] = [
        _brief_item(
            "areas_of_higher_confidence",
            "Demonstrated ability to design and implement governance and operating models for large, regulated organizations.",
            evidence_ids[0],
        ),
        _brief_item(
            "patterns_and_structural_observations",
            "Limited public detail on team direct reports and formal people-management span beyond scaling counts.",
            evidence_ids[0],
        ),
    ]
    incoming["reflection"]["overview_brief_items"] = [
        _brief_item(
            "areas_of_less_clarity",
            "Some role durations are short; longer-term impact and retention outcomes post-engagement are not described in the source.",
            evidence_ids[1],
        ),
        _brief_item(
            "professionally_salient_attention_items",
            "Duration and reporting lines for some short contract roles are clear, but long-term retained vs pure-contract status per engagement is not explicit.",
            evidence_ids[1],
        ),
    ]

    updated, _summary = ReconciliationAgent().reconcile(
        existing_twin=existing,
        candidate_twin=incoming,
    )

    items = updated["reflection"]["overview_brief_items"]
    assert any(
        item["section"] == "patterns_and_structural_observations"
        and "governance and operating models" in item["text"]
        for item in items
    )
    assert any(
        item["section"] == "areas_of_less_clarity"
        and "direct reports" in item["text"]
        for item in items
    )
    assert not any("retention outcomes" in item["text"] for item in items)
    assert not any("post-engagement" in item["text"] for item in items)
    assert not any("pure-contract" in item["text"] for item in items)


def test_reconciliation_merges_similar_recurring_patterns() -> None:
    existing = _twin_with_evidence("Built a reusable delivery platform.")
    existing["reflection"]["strongly_supported"] = [
        "Designing and implementing scalable operating models and team structures",
        "Building reusable engineering platforms",
    ]
    existing["inferences"] = []
    incoming = _twin_with_evidence(
        "Improved governance transparency with metrics.",
        source_id="src_second_cv",
    )
    incoming["reflection"]["strongly_supported"] = [
        "Designing and implementing scalable operating models and team-of-teams structures",
        "Building reusable engineering platforms for delivery acceleration",
    ]
    incoming["inferences"] = []

    updated, _summary = ReconciliationAgent().reconcile(
        existing_twin=existing,
        candidate_twin=incoming,
    )

    patterns = updated["reflection"]["strongly_supported"]
    assert len(patterns) == 2
    assert "Designing and implementing scalable operating models and team-of-teams structures" in patterns
    assert "Building reusable engineering platforms for delivery acceleration" in patterns


def test_reconciliation_merges_recurring_patterns_with_shared_governance_theme() -> None:
    existing = _twin_with_evidence("Created transparent portfolio governance.")
    existing["reflection"]["strongly_supported"] = [
        "Establishing executive governance, metrics, and decision frameworks",
    ]
    existing["inferences"] = []
    incoming = _twin_with_evidence(
        "Improved reporting and decision clarity.",
        source_id="src_second_cv",
    )
    incoming["reflection"]["strongly_supported"] = [
        "Establishing governance, metrics, and reporting to create transparency and measurable outcomes",
    ]
    incoming["inferences"] = []

    updated, _summary = ReconciliationAgent().reconcile(
        existing_twin=existing,
        candidate_twin=incoming,
    )

    patterns = updated["reflection"]["strongly_supported"]
    assert len(patterns) == 1
    assert patterns == [
        "Establishing governance, metrics, and reporting to create transparency and measurable outcomes"
    ]


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
    for item in twin["reflection"].get("overview_brief_items", []):
        item["supporting_evidence_ids"] = [evidence["id"]]
    twin["reflection"]["summary"] = "Technology leadership pattern with measurable platform outcomes."
    twin["reflection"]["strongly_supported"] = [inference_value]
    return twin


def _brief_item(section: str, text: str, evidence_id: str) -> dict:
    return {
        "id": f"brief_{hash(text) & 0xfffffff:x}",
        "section": section,
        "kind": "observation",
        "text": text,
        "salience": 0.8,
        "confidence": 0.8,
        "supporting_evidence_ids": [evidence_id],
    }
