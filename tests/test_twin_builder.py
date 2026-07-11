from __future__ import annotations

from pathlib import Path

from dctwin.foundry import FoundryExtractionTwinProvider
from dctwin.io import load_json
from dctwin.twin_builder import build_twin_from_extraction, tag_assignments, _mirror_summary
from dctwin.validation import validate_twin


ROOT = Path(__file__).resolve().parents[1]


def test_compact_extraction_contract_includes_education_training() -> None:
    schema = FoundryExtractionTwinProvider._extraction_schema(["block_page_1"])

    assert "education_training" in schema["required"]
    education = schema["properties"]["education_training"]
    assert education["items"]["properties"]["kind"]["enum"] == [
        "education",
        "certification",
    ]
    interpretation = schema["properties"]["interpretation"]
    assert "overview_brief_items" in interpretation["required"]
    assert interpretation["properties"]["overview_brief_items"]["maxItems"] == 12
    assert interpretation["properties"]["recurring_patterns"]["maxItems"] == 6
    assert interpretation["properties"]["capability_hypotheses"]["maxItems"] == 6
    assert interpretation["properties"]["unclear_questions"]["maxItems"] == 5
    assert interpretation["properties"]["overview_brief_items"]["items"]["properties"]["section"]["enum"] == [
        "career_in_brief",
        "patterns_and_structural_observations",
        "areas_of_higher_confidence",
        "areas_of_less_clarity",
        "professionally_salient_attention_items",
        "confidence_statement",
    ]


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
        "education_training": [
            {
                "kind": "education",
                "value": "MSc Computer Science, Example University",
                "source_block_id": "block_page_1",
                "quote": "Education: MSc Computer Science, Example University",
                "confidence": 0.92,
            },
            {
                "kind": "certification",
                "value": "Professional Development: Certified Scrum Master",
                "source_block_id": "block_page_1",
                "quote": "Professional Development: Certified Scrum Master",
                "confidence": 0.88,
            },
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
            "overview_brief_items": [
                {
                    "section": "career_in_brief",
                    "kind": "observation",
                    "text": "The evidence contains one Platform Lead role at ACME.",
                    "salience": 0.8,
                    "confidence": 0.9,
                    "supporting_achievement_indexes": [0],
                },
                {
                    "section": "patterns_and_structural_observations",
                    "kind": "interpretation",
                    "text": "Reusable platform work is connected to measurable delivery improvement.",
                    "salience": 0.9,
                    "confidence": 0.78,
                    "supporting_achievement_indexes": [0],
                },
                {
                    "section": "patterns_and_structural_observations",
                    "kind": "interpretation",
                    "text": "Unsupported interpretation should not enter the canonical Twin.",
                    "salience": 0.95,
                    "confidence": 0.9,
                    "supporting_achievement_indexes": [],
                },
            ],
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
    assert {fact["kind"] for fact in twin["person"]["facts"]} == {
        "name",
        "education",
        "certification",
    }
    assert twin["evidence_items"][0]["role_id"] == twin["roles"][0]["id"]
    assert twin["evidence_items"][0]["tag_assignments"]["capabilities"]
    assert twin["reflection"]["summary"].startswith("The available evidence presents")
    assert [item["section"] for item in twin["reflection"]["overview_brief_items"]] == [
        "career_in_brief",
        "patterns_and_structural_observations",
    ]
    assert twin["reflection"]["overview_brief_items"][0]["supporting_evidence_ids"] == [
        twin["evidence_items"][0]["id"]
    ]
    assert not any(
        "Unsupported interpretation" in item["text"]
        for item in twin["reflection"]["overview_brief_items"]
    )
    assert twin["inferences"][0]["value"] == "Platform engineering for delivery acceleration"
    validate_twin(twin, schema, catalog, source_documents=[source])


def test_mirror_summary_uses_objective_overview_brief_voice() -> None:
    assert _mirror_summary(
        "Experienced technology leader focused on measurable platform outcomes."
    ) == (
        "The available evidence presents technology leadership "
        "focused on measurable platform outcomes."
    )
    assert _mirror_summary("I’m less certain about education history.") == (
        "There is less clarity about education history."
    )
    assert _mirror_summary(
        "Your Twin currently contains evidence spanning twelve years across nine roles."
    ) == "Your Twin currently contains evidence spanning twelve years across nine roles."


def test_fast_tagger_assigns_multiple_capabilities_for_infrastructure_cost_work() -> None:
    catalog = load_json(ROOT / "catalogs/tag_catalog.json")

    assignments = tag_assignments(
        "Reduced AWS costs by 37% ($1.1M annually) through Kubernetes transformation and infrastructure rationalization.",
        catalog,
    )

    capabilities = {item["tag_id"] for item in assignments["capabilities"]}
    themes = {item["tag_id"] for item in assignments["narrative_themes"]}
    assert "tag_cost_optimization" in capabilities
    assert "tag_platform_engineering" in capabilities
    assert "tag_cloud_infrastructure_management" in capabilities
    assert "tag_measurable_business_value" in themes
    assert "tag_simplifying_complexity" in themes


def test_compact_extraction_mapping_preserves_role_dates_from_noisy_values() -> None:
    source = load_json(ROOT / "tests/fixtures/valid_source.json")
    catalog = load_json(ROOT / "catalogs/tag_catalog.json")
    extraction = {
        "source_label": "Synthetic CV",
        "person_name": None,
        "roles": [
            {
                "id": "r1",
                "title": "Delivery Lead",
                "organization": "Example Co",
                "start_date": None,
                "end_date": "Present",
                "summary": "Led delivery teams.",
                "source_block_id": "block_page_1",
                "quote": "Delivery Lead, Example Co, Mar 2020 — Present",
                "confidence": 0.8,
            }
        ],
        "education_training": [],
        "achievements": [],
        "interpretation": {
            "reflection_summary": "",
            "overview_brief_items": [],
            "recurring_patterns": [],
            "capability_hypotheses": [],
            "unclear_questions": [],
        },
    }

    twin = build_twin_from_extraction(
        extraction=extraction,
        source_document=source,
        tag_catalog=catalog,
    )

    assert twin["roles"][0]["start_date"] == "2020-03"
    assert twin["roles"][0]["end_date"] is None
