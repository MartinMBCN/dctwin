from __future__ import annotations

import hashlib
import re
from datetime import UTC, datetime
from typing import Any


def build_twin_from_extraction(
    *,
    extraction: dict[str, Any],
    source_document: dict[str, Any],
    tag_catalog: dict[str, Any],
) -> dict[str, Any]:
    """Map a compact role/achievement extraction into the full DCT contract."""

    source_id = source_document["source_id"]
    source = {
        "id": source_id,
        "type": source_document["source_type"],
        "label": extraction.get("source_label") or _source_label(source_document),
        "adapter": (
            f"{source_document['adapter']['name']}@"
            f"{source_document['adapter']['version']}"
        ),
        "content_hash": source_document["content_hash"],
    }
    roles: list[dict[str, Any]] = []
    role_ids_by_index: dict[int, str] = {}
    role_ids_by_original: dict[str, str] = {}

    for index, role in enumerate(extraction.get("roles", [])):
        role_id = _unique_id(
            "role",
            f"{role.get('title')} {role.get('organization')} "
            f"{role.get('start_date')} {role.get('end_date')}",
            {item["id"] for item in roles},
        )
        role_ids_by_index[index] = role_id
        if role.get("id"):
            role_ids_by_original[str(role["id"])] = role_id
        roles.append(
            {
                "id": role_id,
                "title": role.get("title") or "Unspecified role",
                "organization": role.get("organization") or "Unspecified organization",
                "start_date": _date_or_none(role.get("start_date")),
                "end_date": _date_or_none(role.get("end_date")),
                "summary": role.get("summary") or "",
                "extraction_confidence": _confidence(role.get("confidence"), default=0.7),
                "source_refs": [_source_ref(source_id, role, source_document)],
            }
        )

    evidence_items: list[dict[str, Any]] = []
    for item in extraction.get("achievements", []):
        text = str(item.get("text") or "").strip()
        if not text:
            continue
        role_id = _mapped_role_id(item, role_ids_by_index, role_ids_by_original)
        evidence_items.append(
            {
                "id": _unique_id("ev", text, {ev["id"] for ev in evidence_items}),
                "type": classify_evidence(text),
                "text": text,
                "role_id": role_id,
                "context": item.get("context"),
                "source_refs": [_source_ref(source_id, item, source_document)],
                "tag_assignments": tag_assignments(text, tag_catalog),
            }
        )

    facts = []
    person_name = str(extraction.get("person_name") or "").strip()
    if person_name:
        facts.append(
            {
                "id": _unique_id("fact", f"name {person_name}", set()),
                "kind": "name",
                "value": person_name,
                "extraction_confidence": 0.7,
                "source_refs": [
                    {
                        "source_id": source_id,
                        "block_id": source_document["blocks"][0]["id"],
                        "quote": person_name,
                    }
                ],
            }
        )

    interpretation = extraction.get("interpretation", {})
    inferences = _inferences(
        evidence_items=evidence_items,
        capability_hypotheses=interpretation.get("capability_hypotheses", []),
    )
    gaps = []
    if not roles:
        gaps.append(
            {
                "id": "gap_roles_not_detected",
                "field_path": "roles",
                "reason": "The staged extraction path did not identify a clear role.",
                "resolution_question": "Which role should this achievement be associated with?",
            }
        )
    if not evidence_items:
        gaps.append(
            {
                "id": "gap_achievements_not_detected",
                "field_path": "evidence_items",
                "reason": "The staged extraction path did not identify achievements.",
                "resolution_question": "What achievements or responsibilities should be added?",
            }
        )

    return {
        "schema_version": "0.2.0",
        "twin_id": f"twin_{source_id.removeprefix('src_')}",
        "generated_at": datetime.now(UTC).isoformat(),
        "tag_catalog_version": tag_catalog["version"],
        "person": {"facts": facts, "preferences": []},
        "sources": [source],
        "roles": roles,
        "evidence_items": evidence_items,
        "inferences": inferences,
        "gaps": gaps,
        "reflection": _reflection(
            evidence_items=evidence_items,
            gaps=gaps,
            interpretation=interpretation,
            role_count=len(roles),
        ),
    }


def classify_evidence(text: str) -> str:
    normalized = _normalize(text)
    if re.search(r"\d+%|€|\$|£|saved|reduced|increased|improved", normalized):
        return "achievement"
    if any(word in normalized for word in ("decided", "chose", "selected", "designed")):
        return "decision"
    if any(word in normalized for word in ("built", "automated", "implemented", "platform", "system")):
        return "technology"
    if any(word in normalized for word in ("led", "managed", "owned", "responsible")):
        return "responsibility"
    return "project"


def tag_assignments(text: str, tag_catalog: dict[str, Any]) -> dict[str, list[dict[str, Any]]]:
    normalized = _normalize(text)
    known = {tag["id"] for tag in tag_catalog.get("tags", [])}
    capability_ids: list[str] = []
    if any(word in normalized for word in ("platform", "developer", "engineering", "kubernetes", "container")):
        capability_ids.append("tag_platform_engineering")
    if any(word in normalized for word in ("aws", "azure", "cloud", "kubernetes", "container", "infrastructure", "hosting")):
        capability_ids.append("tag_cloud_infrastructure_management")
    if any(word in normalized for word in ("ai", "llm", "machine learning")):
        capability_ids.append("tag_ai_adoption")
    if any(word in normalized for word in ("automated", "automation")):
        capability_ids.append("tag_automation")
    if any(word in normalized for word in ("cost", "saving", "saved", "budget", "$", "€", "£")):
        capability_ids.append("tag_cost_optimization")
    if any(word in normalized for word in ("governance", "decision", "control")):
        capability_ids.append("tag_governance")
    if any(word in normalized for word in ("release", "delivery", "deployment", "quality", "predictability")):
        capability_ids.append("tag_delivery_excellence")
    if not capability_ids:
        capability_ids.append("tag_delivery_excellence")

    theme_ids: list[str] = []
    if re.search(r"\d+%|€|\$|£|saved|reduced|increased|improved", normalized):
        theme_ids.append("tag_measurable_business_value")
    if any(word in normalized for word in ("simplified", "standard", "reusable", "rationalization", "rationalisation")):
        theme_ids.append("tag_simplifying_complexity")
    if any(word in normalized for word in ("scaled", "scaling", "growth", "teams", "platform")):
        theme_ids.append("tag_scaling_through_systems")
    if not theme_ids:
        theme_ids.append("tag_capability_building")

    capability_ids = _known_unique(
        capability_ids,
        known,
        fallback=next(tag["id"] for tag in tag_catalog["tags"] if tag["type"] == "capability"),
    )[:4]
    theme_ids = _known_unique(
        theme_ids,
        known,
        fallback=next(tag["id"] for tag in tag_catalog["tags"] if tag["type"] == "narrative_theme"),
    )[:3]
    return {
        "capabilities": [
            {
                "tag_id": tag_id,
                "confidence": 0.6,
                "rationale": "Assigned by fast deterministic keyword rules.",
            }
            for tag_id in capability_ids
        ],
        "narrative_themes": [
            {
                "tag_id": tag_id,
                "confidence": 0.6,
                "rationale": "Assigned by fast deterministic keyword rules.",
            }
            for tag_id in theme_ids
        ],
    }


def _known_unique(tag_ids: list[str], known: set[str], *, fallback: str) -> list[str]:
    selected: list[str] = []
    for tag_id in tag_ids:
        if tag_id in known and tag_id not in selected:
            selected.append(tag_id)
    if not selected:
        selected.append(fallback)
    return selected


def _source_label(source_document: dict[str, Any]) -> str:
    media_type = source_document.get("media_type", "source")
    return f"{source_document['source_type']} source ({media_type})"


def _source_ref(
    source_id: str,
    item: dict[str, Any],
    source_document: dict[str, Any],
) -> dict[str, Any]:
    block_ids = {block["id"] for block in source_document.get("blocks", [])}
    block_id = item.get("source_block_id")
    if block_id not in block_ids:
        block_id = source_document["blocks"][0]["id"]
    quote = str(item.get("quote") or item.get("text") or "").strip() or None
    return {"source_id": source_id, "block_id": block_id, "quote": quote}


def _mapped_role_id(
    item: dict[str, Any],
    role_ids_by_index: dict[int, str],
    role_ids_by_original: dict[str, str],
) -> str | None:
    if item.get("role_id") is not None and str(item["role_id"]) in role_ids_by_original:
        return role_ids_by_original[str(item["role_id"])]
    if item.get("role_index") is not None:
        try:
            return role_ids_by_index.get(int(item["role_index"]))
        except (TypeError, ValueError):
            return None
    return None


def _inferences(
    *,
    evidence_items: list[dict[str, Any]],
    capability_hypotheses: list[dict[str, Any]],
) -> list[dict[str, Any]]:
    if not evidence_items:
        return []
    inferences: list[dict[str, Any]] = []
    for hypothesis in capability_hypotheses:
        support = _evidence_ids_for_indexes(
            evidence_items,
            hypothesis.get("supporting_achievement_indexes", []),
        )
        if not support:
            continue
        value = str(hypothesis.get("value") or "").strip()
        if not value:
            continue
        inferences.append(
            {
                "id": _unique_id("inf", f"capability {value}", {item["id"] for item in inferences}),
                "kind": "capability",
                "value": value,
                "confidence": _confidence(hypothesis.get("confidence"), default=0.6),
                "rationale": hypothesis.get("rationale") or "Compact interpretation from staged extraction.",
                "supporting_evidence_ids": support,
                "alternatives": hypothesis.get("alternatives") or [],
                "status": "proposed",
            }
        )
    if inferences:
        return inferences

    by_capability: dict[str, list[str]] = {}
    for item in evidence_items:
        for assignment in item["tag_assignments"]["capabilities"]:
            by_capability.setdefault(assignment["tag_id"], []).append(item["id"])
    tag_id, support = max(by_capability.items(), key=lambda pair: len(pair[1]))
    return [
        {
            "id": _unique_id("inf", f"capability {tag_id}", set()),
            "kind": "capability",
            "value": tag_id.removeprefix("tag_").replace("_", " "),
            "confidence": 0.55,
            "rationale": "Fast first-pass inference based on recurring deterministic tag assignments.",
            "supporting_evidence_ids": support,
            "alternatives": ["Requires deeper model reflection for stronger interpretation."],
            "status": "proposed",
        }
    ]


def _reflection(
    *,
    evidence_items: list[dict[str, Any]],
    gaps: list[dict[str, Any]],
    interpretation: dict[str, Any],
    role_count: int,
) -> dict[str, Any]:
    summary = str(interpretation.get("reflection_summary") or "").strip()
    if not summary:
        summary = (
            f"This staged extraction found {len(evidence_items)} achievement"
            f"{'' if len(evidence_items) == 1 else 's'} across {role_count} role"
            f"{'' if role_count == 1 else 's'}. A deeper interpretation is still needed."
        )
    patterns = [
        str(pattern.get("text") or "").strip()
        for pattern in interpretation.get("recurring_patterns", [])
        if str(pattern.get("text") or "").strip()
    ]
    unclear = [
        str(question).strip()
        for question in interpretation.get("unclear_questions", [])
        if str(question).strip()
    ]
    fallback_unclear = [
        gap["resolution_question"]
        for gap in gaps
        if gap.get("resolution_question")
    ]
    return {
        "summary": summary,
        "strongly_supported": patterns or [item["text"] for item in evidence_items[:5]],
        "unclear": unclear or fallback_unclear,
        "suggested_questions": unclear or fallback_unclear,
    }


def _evidence_ids_for_indexes(
    evidence_items: list[dict[str, Any]],
    indexes: list[Any],
) -> list[str]:
    evidence_ids: list[str] = []
    for raw_index in indexes:
        try:
            index = int(raw_index)
        except (TypeError, ValueError):
            continue
        if 0 <= index < len(evidence_items):
            evidence_ids.append(evidence_items[index]["id"])
    return evidence_ids


def _date_or_none(value: Any) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    match = re.match(r"^\d{4}(?:-\d{2})?(?:-\d{2})?$", text)
    return text if match else None


def _confidence(value: Any, *, default: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        return default
    return min(1.0, max(0.0, number))


def _unique_id(prefix: str, text: str, existing_ids: set[str]) -> str:
    digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]
    candidate = f"{prefix}_{digest}"
    counter = 2
    while candidate in existing_ids:
        candidate = f"{prefix}_{digest}_{counter}"
        counter += 1
    return candidate


def _normalize(value: Any) -> str:
    return re.sub(r"[^a-z0-9%€$£]+", " ", str(value or "").lower()).strip()
