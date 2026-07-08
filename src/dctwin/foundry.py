from __future__ import annotations

import json
from copy import deepcopy
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

from azure.ai.projects import AIProjectClient
from azure.core.credentials import TokenCredential

from dctwin.twin_builder import build_twin_from_extraction


class FoundryTwinProvider:
    """Generate a candidate Twin through a Foundry model deployment."""

    def __init__(
        self,
        *,
        project_endpoint: str,
        model_deployment: str,
        credential: TokenCredential,
        instructions: str,
        source_instructions: str,
    ) -> None:
        self._project = AIProjectClient(endpoint=project_endpoint, credential=credential)
        self._client = self._project.get_openai_client()
        self._model_deployment = model_deployment
        self._instructions = instructions
        self._source_instructions = source_instructions

    @classmethod
    def from_files(
        cls,
        *,
        project_endpoint: str,
        model_deployment: str,
        credential: TokenCredential,
        project_root: Path,
    ) -> "FoundryTwinProvider":
        return cls(
            project_endpoint=project_endpoint,
            model_deployment=model_deployment,
            credential=credential,
            instructions=(project_root / "prompts/source_adapter_agent.md").read_text(
                encoding="utf-8"
            ),
            source_instructions=(project_root / "prompts/cv_to_dct.md").read_text(
                encoding="utf-8"
            ),
        )

    def generate(
        self,
        *,
        source_document: dict[str, Any],
        twin_schema: dict[str, Any],
        tag_catalog: dict[str, Any],
    ) -> dict[str, Any]:
        source_id = source_document["source_id"]
        request = {
            "current_utc": datetime.now(UTC).isoformat(),
            "required_values": {
                "schema_version": "0.2.0",
                "twin_id": f"twin_{source_id.removeprefix('src_')}",
                "tag_catalog_version": tag_catalog["version"],
                "source_id": source_id,
                "source_type": source_document["source_type"],
                "source_content_hash": source_document["content_hash"],
                "source_adapter": (
                    f"{source_document['adapter']['name']}@"
                    f"{source_document['adapter']['version']}"
                ),
            },
            "source_instructions": self._source_instructions,
            "tag_catalog": tag_catalog,
            "normalized_source_document": source_document,
        }
        return self._request(
            input_value=request,
            twin_schema=twin_schema,
            tag_catalog=tag_catalog,
            instructions=self._instructions,
        )

    def repair(
        self,
        *,
        candidate: dict[str, Any],
        validation_issues: tuple[str, ...],
        source_document: dict[str, Any],
        twin_schema: dict[str, Any],
        tag_catalog: dict[str, Any],
    ) -> dict[str, Any]:
        return self._request(
            input_value={
                "candidate_to_repair": candidate,
                "repair_context": {
                    "validation_issues": validation_issues,
                    "allowed_tag_catalog": tag_catalog,
                    "source_id_must_remain": source_document["source_id"],
                },
            },
            twin_schema=twin_schema,
            tag_catalog=tag_catalog,
            instructions=(
                "Repair the candidate Digital Career Twin so every supplied validation "
                "issue is resolved. Return only the repaired candidate object matching "
                "the response schema. Do not copy repair_context, source_id, tag_catalog, "
                "validation_issues, or any other wrapper field into the output. Preserve "
                "supported semantic content. If an ID changes, update every reference to "
                "it. If an evidence item lacks a capability or narrative_theme assignment, "
                "add an appropriate tag from allowed_tag_catalog with calibrated confidence "
                "and a specific rationale. Do not remove valid evidence merely to pass validation."
            ),
        )

    def _request(
        self,
        *,
        input_value: dict[str, Any],
        twin_schema: dict[str, Any],
        tag_catalog: dict[str, Any],
        instructions: str,
    ) -> dict[str, Any]:
        model_schema = deepcopy(twin_schema)
        self._remove_model_unsupported_keywords(model_schema)
        self._constrain_tag_ids(model_schema, tag_catalog)
        response = self._client.responses.create(
            model=self._model_deployment,
            instructions=instructions,
            input=json.dumps(input_value, ensure_ascii=False),
            reasoning={"effort": "minimal"},
            max_output_tokens=12_000,
            store=False,
            text={
                "verbosity": "medium",
                "format": {
                    "type": "json_schema",
                    "name": "digital_career_twin",
                    "description": "Candidate Digital Career Twin derived from one source",
                    "schema": model_schema,
                    "strict": True,
                }
            },
        )
        if response.status != "completed":
            raise RuntimeError(
                "Foundry did not complete the Twin output: "
                f"{response.incomplete_details or response.status}"
            )
        if not response.output_text:
            raise RuntimeError(
                f"Foundry returned no Twin output (response status: {response.status})"
            )
        try:
            result = json.loads(response.output_text)
        except json.JSONDecodeError as exc:
            raise ValueError(
                "Foundry returned malformed structured output at "
                f"line {exc.lineno}, column {exc.colno}"
            ) from exc
        if not isinstance(result, dict):
            raise ValueError("Foundry output was not a JSON object")
        return result

    @staticmethod
    def _remove_model_unsupported_keywords(value: Any) -> None:
        """Keep the canonical schema strict while deriving Foundry's supported subset."""

        if isinstance(value, dict):
            value.pop("uniqueItems", None)
            for nested in value.values():
                FoundryTwinProvider._remove_model_unsupported_keywords(nested)
        elif isinstance(value, list):
            for nested in value:
                FoundryTwinProvider._remove_model_unsupported_keywords(nested)

    @staticmethod
    def _constrain_tag_ids(
        model_schema: dict[str, Any], tag_catalog: dict[str, Any]
    ) -> None:
        assignments = model_schema["$defs"]["evidence"]["properties"][
            "tag_assignments"
        ]["properties"]
        base = model_schema["$defs"]["tagAssignment"]
        for group_name, tag_type in (
            ("capabilities", "capability"),
            ("narrative_themes", "narrative_theme"),
        ):
            item_schema = deepcopy(base)
            item_schema["properties"]["tag_id"] = {
                "type": "string",
                "enum": [
                    tag["id"]
                    for tag in tag_catalog["tags"]
                    if tag["type"] == tag_type
                ],
            }
            assignments[group_name]["items"] = item_schema

    def close(self) -> None:
        self._project.close()


class FoundryExtractionTwinProvider(FoundryTwinProvider):
    """Model emits transient CVExtractionResult; application builds the DCT."""

    def generate(
        self,
        *,
        source_document: dict[str, Any],
        twin_schema: dict[str, Any],
        tag_catalog: dict[str, Any],
    ) -> dict[str, Any]:
        del twin_schema
        extraction = self._request_extraction(source_document=source_document)
        return build_twin_from_extraction(
            extraction=extraction,
            source_document=source_document,
            tag_catalog=tag_catalog,
        )

    def _request_extraction(self, *, source_document: dict[str, Any]) -> dict[str, Any]:
        block_ids = [block["id"] for block in source_document["blocks"]]
        request = {
            "current_utc": datetime.now(UTC).isoformat(),
            "task": (
                "Extract only compact CV structure: person name if clearly stated, "
                "roles, education/professional development facts, "
                "achievement/responsibility claims, and a compact interpretation. "
                "Do not produce the full DCT structure."
            ),
            "normalized_source_document": source_document,
        }
        response = self._client.responses.create(
            model=self._model_deployment,
            instructions=(
                "You are the fast extraction stage for a Digital Career Twin. "
                "Return compact, source-grounded JSON only. Extract all clear roles "
                "and all clear education, certification, training, and professional "
                "development entries. Extract formal degrees as education; extract "
                "courses, certifications, accreditations, and professional development "
                "as certification unless the source clearly says otherwise. Extract all "
                "material achievements/responsibilities, preserving source block "
                "references and short quotes. Keep quotes to short source snippets, not "
                "whole bullets or paragraphs. Keep role summaries and achievement text "
                "concise. Preserve role start and end dates when the source "
                "states them; use YYYY, YYYY-MM, or YYYY-MM-DD. For current/present roles, "
                "preserve the start date and use null for the end date. Also provide a "
                "bounded compact interpretation: recurring patterns, capability "
                "hypotheses, unclear questions, and atomic overview_brief_items. Each "
                "overview_brief_item should be one professionally salient sentence or "
                "bullet-worthy observation. Aim for 8 to 12 overview_brief_items when "
                "the source contains enough evidence, with no more than 12 total: "
                "1-3 career-in-brief items, 2-4 structural pattern items, 2-4 "
                "higher-confidence items, 0-2 less-clarity items, 0-2 attention items, "
                "and 1 confidence statement. Emit no more than "
                "6 recurring_patterns, 6 capability_hypotheses, and 5 unclear_questions. "
                "Prefer concise, specific, evidence-rich items over generic coverage. "
                "Do not emit the final displayed brief as "
                "prose. Establish observable facts before drawing interpretations. "
                "Include professionally salient structural observations when supported: "
                "career duration, role count, geography, industry/domain movement, "
                "seniority, management emphasis, consulting periods, career gaps, "
                "concurrent roles, quantified outcomes, unusual patterns and attention "
                "items a recruiter, hiring manager or executive assessor would probably "
                "ask about. Interpretations should be traceable to multiple observations. "
                "Present uncertainty neutrally. Apply the Overview Brief quality contract: "
                "select the right salient information, keep section purposes distinct, "
                "order the strongest observations first, prioritize stronger evidence, "
                "make interesting higher-order observations rather than obvious labels, "
                "and check for trajectory, progression, mobility, domain changes, "
                "scale, outcome clusters, gaps, overlaps and compressed tenures. "
                "Include at least one confidence_statement "
                "item. Avoid motivational language, coaching language, conversational "
                "fillers and anthropomorphic phrases such as 'I think', 'I feel', "
                "'I'm reading', 'My impression is', 'You strike me as', or 'If this feels "
                "directionally right'. Do not produce the full DCT schema."
            ),
            input=json.dumps(request, ensure_ascii=False),
            reasoning={"effort": "minimal"},
            max_output_tokens=8_000,
            store=False,
            text={
                "verbosity": "low",
                "format": {
                    "type": "json_schema",
                    "name": "cv_extraction_result",
                    "description": "Transient CVExtractionResult used before deterministic DCT construction",
                    "schema": self._extraction_schema(block_ids),
                    "strict": True,
                },
            },
        )
        if response.status != "completed":
            raise RuntimeError(
                "Foundry did not complete compact extraction: "
                f"{response.incomplete_details or response.status}"
            )
        if not response.output_text:
            raise RuntimeError("Foundry returned no compact extraction output")
        result = json.loads(response.output_text)
        if not isinstance(result, dict):
            raise ValueError("Foundry compact extraction output was not a JSON object")
        return result

    @staticmethod
    def _extraction_schema(block_ids: list[str]) -> dict[str, Any]:
        block_id_schema: dict[str, Any] = {"type": "string"}
        if block_ids:
            block_id_schema["enum"] = block_ids
        source_ref_properties = {
            "source_block_id": block_id_schema,
            "quote": {"type": ["string", "null"]},
            "confidence": {"type": "number", "minimum": 0, "maximum": 1},
        }
        return {
            "type": "object",
            "additionalProperties": False,
            "required": [
                "source_label",
                "person_name",
                "roles",
                "education_training",
                "achievements",
                "interpretation",
            ],
            "properties": {
                "source_label": {"type": ["string", "null"]},
                "person_name": {"type": ["string", "null"]},
                "roles": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": [
                            "id",
                            "title",
                            "organization",
                            "start_date",
                            "end_date",
                            "summary",
                            "source_block_id",
                            "quote",
                            "confidence",
                        ],
                        "properties": {
                            "id": {"type": "string"},
                            "title": {"type": "string"},
                            "organization": {"type": "string"},
                            "start_date": {
                                "type": ["string", "null"],
                                "description": "Role start date from the source using YYYY, YYYY-MM, or YYYY-MM-DD. Use null only if absent.",
                            },
                            "end_date": {
                                "type": ["string", "null"],
                                "description": "Role end date from the source using YYYY, YYYY-MM, or YYYY-MM-DD. Use null for current/present roles or if absent.",
                            },
                            "summary": {"type": "string"},
                            **source_ref_properties,
                        },
                    },
                },
                "achievements": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": [
                            "text",
                            "role_id",
                            "role_index",
                            "context",
                            "source_block_id",
                            "quote",
                            "confidence",
                        ],
                        "properties": {
                            "text": {"type": "string"},
                            "role_id": {"type": ["string", "null"]},
                            "role_index": {"type": ["integer", "null"], "minimum": 0},
                            "context": {"type": ["string", "null"]},
                            **source_ref_properties,
                        },
                    },
                },
                "education_training": {
                    "type": "array",
                    "description": "Education, certifications, training, courses, and professional development entries stated in the source.",
                    "items": {
                        "type": "object",
                        "additionalProperties": False,
                        "required": [
                            "kind",
                            "value",
                            "source_block_id",
                            "quote",
                            "confidence",
                        ],
                        "properties": {
                            "kind": {
                                "type": "string",
                                "enum": ["education", "certification"],
                                "description": "Use education for formal degree/school entries; certification for courses, certifications, accreditations, and professional development.",
                            },
                            "value": {"type": "string"},
                            **source_ref_properties,
                        },
                    },
                },
                "interpretation": {
                    "type": "object",
                    "additionalProperties": False,
                    "required": [
                        "reflection_summary",
                        "overview_brief_items",
                        "recurring_patterns",
                        "capability_hypotheses",
                        "unclear_questions",
                    ],
                    "properties": {
                        "reflection_summary": {
                            "type": "string",
                            "description": "Short compatibility summary. The primary Overview Brief contract is overview_brief_items.",
                        },
                        "overview_brief_items": {
                            "type": "array",
                            "maxItems": 12,
                            "description": "Atomic brief-worthy observations for deterministic application assembly of the Overview Brief.",
                            "items": {
                                "type": "object",
                                "additionalProperties": False,
                                "required": [
                                    "section",
                                    "kind",
                                    "text",
                                    "salience",
                                    "confidence",
                                    "supporting_achievement_indexes",
                                ],
                                "properties": {
                                    "section": {
                                        "type": "string",
                                        "enum": [
                                            "career_in_brief",
                                            "patterns_and_structural_observations",
                                            "areas_of_higher_confidence",
                                            "areas_of_less_clarity",
                                            "professionally_salient_attention_items",
                                            "confidence_statement",
                                        ],
                                    },
                                    "kind": {
                                        "type": "string",
                                        "enum": [
                                            "observation",
                                            "interpretation",
                                            "uncertainty",
                                            "attention_item",
                                            "confidence_statement",
                                        ],
                                    },
                                    "text": {
                                        "type": "string",
                                        "description": "One concise sentence suitable for rendering as a bullet.",
                                    },
                                    "salience": {
                                        "type": "number",
                                        "minimum": 0,
                                        "maximum": 1,
                                    },
                                    "confidence": {
                                        "type": "number",
                                        "minimum": 0,
                                        "maximum": 1,
                                    },
                                    "supporting_achievement_indexes": {
                                        "type": "array",
                                        "items": {"type": "integer", "minimum": 0},
                                    },
                                },
                            },
                        },
                        "recurring_patterns": {
                            "type": "array",
                            "maxItems": 6,
                            "items": {
                                "type": "object",
                                "additionalProperties": False,
                                "required": ["text", "supporting_achievement_indexes"],
                                "properties": {
                                    "text": {"type": "string"},
                                    "supporting_achievement_indexes": {
                                        "type": "array",
                                        "items": {"type": "integer", "minimum": 0},
                                    },
                                },
                            },
                        },
                        "capability_hypotheses": {
                            "type": "array",
                            "maxItems": 6,
                            "items": {
                                "type": "object",
                                "additionalProperties": False,
                                "required": [
                                    "value",
                                    "confidence",
                                    "rationale",
                                    "supporting_achievement_indexes",
                                    "alternatives",
                                ],
                                "properties": {
                                    "value": {"type": "string"},
                                    "confidence": {
                                        "type": "number",
                                        "minimum": 0,
                                        "maximum": 1,
                                    },
                                    "rationale": {"type": "string"},
                                    "supporting_achievement_indexes": {
                                        "type": "array",
                                        "items": {"type": "integer", "minimum": 0},
                                    },
                                    "alternatives": {
                                        "type": "array",
                                        "items": {"type": "string"},
                                    },
                                },
                            },
                        },
                        "unclear_questions": {
                            "type": "array",
                            "maxItems": 5,
                            "items": {"type": "string"},
                        },
                    },
                },
            },
        }
