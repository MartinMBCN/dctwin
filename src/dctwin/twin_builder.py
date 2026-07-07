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

    inferences = _inferences(evidence_items)
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
        "reflection": {
            "summary": (
                f"This staged extraction found {len(evidence_items)} achievement"
                f"{'' if len(evidence_items) == 1 else 's'} across {len(roles)} role"
                f"{'' if len(roles) == 1 else 's'}. Capabilities and themes are "
                "assigned deterministically as a fast first pass."
            ),
            "strongly_supported": [item["text"] for item in evidence_items[:5]],
            "unclear": [gap["resolution_question"] for gap in gaps],
            "suggested_questions": [gap["resolution_question"] for gap in gaps],
        },
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
    capability = "tag_delivery_excellence"
    if any(word in normalized for word in ("platform", "developer", "engineering")):
        capability = "tag_platform_engineering"
    elif any(word in normalized for word in ("ai", "llm", "machine learning")):
        capability = "tag_ai_adoption"
    elif any(word in normalized for word in ("automated", "automation")):
        capability = "tag_automation"
    elif any(word in normalized for word in ("cost", "saving", "saved", "budget")):
        capability = "tag_cost_optimization"
    elif any(word in normalized for word in ("governance", "decision", "control")):
        capability = "tag_governance"

    theme = "tag_capability_building"
    if re.search(r"\d+%|€|\$|£|saved|reduced|increased|improved", normalized):
        theme = "tag_measurable_business_value"
    elif any(word in normalized for word in ("simplified", "standard", "reusable")):
        theme = "tag_simplifying_complexity"
    elif any(word in normalized for word in ("scaled", "growth", "teams")):
        theme = "tag_scaling_through_systems"

    known = {tag["id"] for tag in tag_catalog.get("tags", [])}
    if capability not in known:
        capability = next(tag["id"] for tag in tag_catalog["tags"] if tag["type"] == "capability")
    if theme not in known:
        theme = next(tag["id"] for tag in tag_catalog["tags"] if tag["type"] == "narrative_theme")
    return {
        "capabilities": [
            {
                "tag_id": capability,
                "confidence": 0.6,
                "rationale": "Assigned by fast deterministic keyword rules.",
            }
        ],
        "narrative_themes": [
            {
                "tag_id": theme,
                "confidence": 0.6,
                "rationale": "Assigned by fast deterministic keyword rules.",
            }
        ],
    }


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


def _inferences(evidence_items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    if not evidence_items:
        return []
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
