from __future__ import annotations

import hashlib
import re
from copy import deepcopy
from dataclasses import dataclass, field
from datetime import UTC, datetime
from difflib import SequenceMatcher
from typing import Any

from dctwin.privacy import minimize_direct_identifiers
from dctwin.twin_builder import classify_evidence, tag_assignments


@dataclass(frozen=True)
class ReconciliationSummary:
    roles_detected: int = 0
    evidence_extracted: int = 0
    evidence_matched: int = 0
    evidence_added: int = 0
    evidence_merged: int = 0
    possible_duplicates: int = 0
    actions: list[dict[str, Any]] = field(default_factory=list)

    def as_dict(self) -> dict[str, Any]:
        return {
            "roles_detected": self.roles_detected,
            "evidence_extracted": self.evidence_extracted,
            "evidence_matched": self.evidence_matched,
            "evidence_added": self.evidence_added,
            "evidence_merged": self.evidence_merged,
            "possible_duplicates": self.possible_duplicates,
            "actions": self.actions,
        }


class ReconciliationAgent:
    """Merge new candidate evidence into an existing canonical Twin."""

    exact_threshold = 0.86
    possible_threshold = 0.72

    def reconcile(
        self,
        *,
        existing_twin: dict[str, Any] | None,
        candidate_twin: dict[str, Any],
    ) -> tuple[dict[str, Any], ReconciliationSummary]:
        if existing_twin is None:
            twin = deepcopy(candidate_twin)
            summary = ReconciliationSummary(
                roles_detected=len(twin.get("roles", [])),
                evidence_extracted=len(twin.get("evidence_items", [])),
                evidence_added=len(twin.get("evidence_items", [])),
                actions=[
                    {
                        "classification": "NEW",
                        "action": "ADD",
                        "entity": "twin",
                        "reason": "No existing session Twin was loaded.",
                    }
                ],
            )
            twin["generated_at"] = datetime.now(UTC).isoformat()
            return twin, summary

        twin = deepcopy(existing_twin)
        candidate = deepcopy(candidate_twin)
        actions: list[dict[str, Any]] = []
        role_map = self._merge_sources_and_roles(twin, candidate, actions)
        counts = {
            "evidence_matched": 0,
            "evidence_added": 0,
            "evidence_merged": 0,
            "possible_duplicates": 0,
        }
        evidence_id_map: dict[str, str] = {}

        for item in candidate.get("evidence_items", []):
            incoming_evidence_id = str(item.get("id") or "")
            if item.get("role_id") in role_map:
                item["role_id"] = role_map[item["role_id"]]
            match = self._best_evidence_match(twin, item)
            if match is None:
                self._add_unique("evidence_items", twin, item)
                if incoming_evidence_id:
                    evidence_id_map[incoming_evidence_id] = item["id"]
                counts["evidence_added"] += 1
                actions.append(
                    {
                        "classification": "NEW",
                        "action": "ADD",
                        "entity": "evidence",
                        "incoming_id": item.get("id"),
                        "reason": "No similar evidence was found in the existing Twin.",
                    }
                )
                continue

            existing_item, score = match
            counts["evidence_matched"] += 1
            if score >= self.exact_threshold:
                self._merge_source_refs(existing_item, item)
                self._merge_tag_assignments(existing_item, item)
                if incoming_evidence_id:
                    evidence_id_map[incoming_evidence_id] = existing_item["id"]
                counts["evidence_merged"] += 1
                actions.append(
                    {
                        "classification": "DUPLICATE",
                        "action": "MERGE_PROVENANCE",
                        "entity": "evidence",
                        "incoming_id": item.get("id"),
                        "target_id": existing_item.get("id"),
                        "score": round(score, 3),
                        "confidence_delta": "none",
                        "inference_delta": "none",
                        "canonical_wording_delta": "none",
                    }
                )
            else:
                appended = deepcopy(item)
                appended["context"] = (
                    f"Possible duplicate of {existing_item.get('id')}. "
                    f"{appended.get('context') or ''}"
                ).strip()
                appended["id"] = self._unique_id(
                    "ev",
                    appended.get("text", ""),
                    {ev.get("id") for ev in twin.get("evidence_items", [])},
                )
                self._add_unique("evidence_items", twin, appended)
                if incoming_evidence_id:
                    evidence_id_map[incoming_evidence_id] = appended["id"]
                counts["possible_duplicates"] += 1
                actions.append(
                    {
                        "classification": "POSSIBLE_DUPLICATE",
                        "action": "ADD_WITH_POSSIBLE_DUPLICATE_CONTEXT",
                        "entity": "evidence",
                        "incoming_id": item.get("id"),
                        "target_id": existing_item.get("id"),
                        "appended_id": appended.get("id"),
                        "score": round(score, 3),
                    }
                )

        self._merge_person_facts(twin, candidate, actions)
        self._merge_gaps(twin, candidate)
        self._remap_candidate_evidence_refs(candidate, evidence_id_map)
        self._merge_inferences(twin, candidate)
        self._refresh_reflection(twin, candidate)
        twin["generated_at"] = datetime.now(UTC).isoformat()

        return twin, ReconciliationSummary(
            roles_detected=len(candidate.get("roles", [])),
            evidence_extracted=len(candidate.get("evidence_items", [])),
            evidence_matched=counts["evidence_matched"],
            evidence_added=counts["evidence_added"],
            evidence_merged=counts["evidence_merged"],
            possible_duplicates=counts["possible_duplicates"],
            actions=actions,
        )

    def add_manual_evidence(
        self,
        *,
        twin: dict[str, Any],
        role_id: str,
        text: str,
        tag_catalog: dict[str, Any],
    ) -> tuple[dict[str, Any], dict[str, Any], ReconciliationSummary]:
        if not text.strip():
            raise ValueError("Manual evidence text is empty")
        if role_id not in {role.get("id") for role in twin.get("roles", [])}:
            raise ValueError(f"Unknown role_id {role_id!r}")

        updated = deepcopy(twin)
        source_doc = self._manual_source_document(text)
        source = {
            "id": source_doc["source_id"],
            "type": "user_entered_data",
            "label": _manual_source_label(source_doc),
            "adapter": "manual_evidence@0.1.0",
            "content_hash": source_doc["content_hash"],
        }
        if source["id"] not in {item.get("id") for item in updated.get("sources", [])}:
            updated.setdefault("sources", []).append(source)

        actions: list[dict[str, Any]] = []
        counts = {
            "evidence_matched": 0,
            "evidence_added": 0,
            "evidence_merged": 0,
            "possible_duplicates": 0,
        }
        existing_ids = {item.get("id") for item in updated.get("evidence_items", [])}
        for block in source_doc["blocks"]:
            evidence_text = block["text"]
            evidence = {
                "id": self._unique_id("ev", evidence_text, existing_ids),
                "type": classify_evidence(evidence_text),
                "text": evidence_text,
                "role_id": role_id,
                "context": "Manually entered by user.",
                "source_refs": [
                    {
                        "source_id": source_doc["source_id"],
                        "block_id": block["id"],
                        "quote": evidence_text,
                    }
                ],
                "tag_assignments": tag_assignments(evidence_text, tag_catalog),
            }
            match = self._best_evidence_match(updated, evidence)
            if match and match[1] >= self.exact_threshold:
                target, score = match
                self._merge_source_refs(target, evidence)
                self._merge_tag_assignments(target, evidence)
                counts["evidence_matched"] += 1
                counts["evidence_merged"] += 1
                actions.append(
                    {
                        "classification": "DUPLICATE",
                        "action": "MERGE_PROVENANCE",
                        "entity": "manual_evidence",
                        "target_id": target.get("id"),
                        "score": round(score, 3),
                        "confidence_delta": "none",
                        "inference_delta": "none",
                        "canonical_wording_delta": "none",
                    }
                )
                continue

            if match:
                evidence["context"] = (
                    f"Possible duplicate of {match[0].get('id')}. "
                    "Manually entered by user."
                )
                counts["evidence_matched"] += 1
                counts["possible_duplicates"] += 1
                actions.append(
                    {
                        "classification": "POSSIBLE_DUPLICATE",
                        "action": "ADD_WITH_POSSIBLE_DUPLICATE_CONTEXT",
                        "entity": "manual_evidence",
                        "target_id": match[0].get("id"),
                        "appended_id": evidence["id"],
                        "score": round(match[1], 3),
                    }
                )
            else:
                actions.append(
                    {
                        "classification": "NEW",
                        "action": "ADD",
                        "entity": "manual_evidence",
                        "appended_id": evidence["id"],
                    }
                )
            updated.setdefault("evidence_items", []).append(evidence)
            existing_ids.add(evidence["id"])
            counts["evidence_added"] += 1

        summary = ReconciliationSummary(
            evidence_extracted=len(source_doc["blocks"]),
            evidence_matched=counts["evidence_matched"],
            evidence_added=counts["evidence_added"],
            evidence_merged=counts["evidence_merged"],
            possible_duplicates=counts["possible_duplicates"],
            actions=actions,
        )

        self._refresh_reflection(updated)
        updated["generated_at"] = datetime.now(UTC).isoformat()
        return updated, source_doc, summary

    def _merge_sources_and_roles(
        self,
        twin: dict[str, Any],
        candidate: dict[str, Any],
        actions: list[dict[str, Any]],
    ) -> dict[str, str]:
        source_ids = {source.get("id") for source in twin.get("sources", [])}
        for source in candidate.get("sources", []):
            if source.get("id") not in source_ids:
                twin.setdefault("sources", []).append(source)
                source_ids.add(source.get("id"))

        role_map: dict[str, str] = {}
        for role in candidate.get("roles", []):
            incoming_id = role.get("id", "")
            existing = self._find_matching_role(twin, role)
            if existing:
                role_map[incoming_id] = existing["id"]
                self._merge_source_refs(existing, role)
                actions.append(
                    {
                        "classification": "DUPLICATE",
                        "action": "MERGE_PROVENANCE",
                        "entity": "role",
                        "incoming_id": role.get("id"),
                        "target_id": existing.get("id"),
                    }
                )
            else:
                role["id"] = self._unique_id(
                    "role",
                    f"{role.get('title')} {role.get('organization')} {role.get('start_date')}",
                    {item.get("id") for item in twin.get("roles", [])},
                )
                role_map[incoming_id] = role["id"]
                twin.setdefault("roles", []).append(role)
                actions.append(
                    {
                        "classification": "NEW",
                        "action": "ADD",
                        "entity": "role",
                        "incoming_id": role.get("id"),
                    }
                )
        return role_map

    def _find_matching_role(
        self, twin: dict[str, Any], incoming: dict[str, Any]
    ) -> dict[str, Any] | None:
        incoming_key = self._role_key(incoming)
        for role in twin.get("roles", []):
            if self._role_key(role) == incoming_key:
                return role
            same_org = _normalize(role.get("organization")) == _normalize(
                incoming.get("organization")
            )
            same_title = SequenceMatcher(
                None, _normalize(role.get("title")), _normalize(incoming.get("title"))
            ).ratio() >= 0.78
            same_dates = (
                role.get("start_date") == incoming.get("start_date")
                or role.get("end_date") == incoming.get("end_date")
            )
            if same_org and same_title and same_dates:
                return role
        return None

    @staticmethod
    def _role_key(role: dict[str, Any]) -> tuple[str, str, str | None, str | None]:
        return (
            _normalize(role.get("title")),
            _normalize(role.get("organization")),
            role.get("start_date"),
            role.get("end_date"),
        )

    def _best_evidence_match(
        self, twin: dict[str, Any], incoming: dict[str, Any]
    ) -> tuple[dict[str, Any], float] | None:
        best: tuple[dict[str, Any], float] | None = None
        for existing in twin.get("evidence_items", []):
            score = _evidence_similarity(existing, incoming)
            if best is None or score > best[1]:
                best = (existing, score)
        if best and best[1] >= self.possible_threshold:
            return best
        return None

    @staticmethod
    def _merge_source_refs(target: dict[str, Any], incoming: dict[str, Any]) -> None:
        seen = {
            (ref.get("source_id"), ref.get("block_id"), ref.get("quote"))
            for ref in target.get("source_refs", [])
        }
        for ref in incoming.get("source_refs", []):
            key = (ref.get("source_id"), ref.get("block_id"), ref.get("quote"))
            if key not in seen:
                target.setdefault("source_refs", []).append(ref)
                seen.add(key)

    @staticmethod
    def _merge_tag_assignments(target: dict[str, Any], incoming: dict[str, Any]) -> None:
        target_groups = target.setdefault(
            "tag_assignments", {"capabilities": [], "narrative_themes": []}
        )
        incoming_groups = incoming.get("tag_assignments", {})
        for group_name in ("capabilities", "narrative_themes"):
            seen = {item.get("tag_id") for item in target_groups.setdefault(group_name, [])}
            for item in incoming_groups.get(group_name, []):
                if item.get("tag_id") not in seen:
                    target_groups[group_name].append(item)
                    seen.add(item.get("tag_id"))

    @staticmethod
    def _add_unique(collection: str, twin: dict[str, Any], item: dict[str, Any]) -> None:
        existing_ids = {existing.get("id") for existing in twin.get(collection, [])}
        if item.get("id") in existing_ids:
            item["id"] = ReconciliationAgent._unique_id(
                item["id"].split("_", 1)[0], item.get("text", repr(item)), existing_ids
            )
        twin.setdefault(collection, []).append(item)

    @staticmethod
    def _merge_person_facts(
        twin: dict[str, Any], candidate: dict[str, Any], actions: list[dict[str, Any]]
    ) -> None:
        facts = twin.setdefault("person", {}).setdefault("facts", [])
        existing = {(fact.get("kind"), repr(fact.get("value"))): fact for fact in facts}
        existing_ids = {fact.get("id") for fact in facts}
        for fact in candidate.get("person", {}).get("facts", []):
            key = (fact.get("kind"), repr(fact.get("value")))
            if key in existing:
                ReconciliationAgent._merge_source_refs(existing[key], fact)
            else:
                if fact.get("id") in existing_ids:
                    fact["id"] = ReconciliationAgent._unique_id(
                        "fact", f"{fact.get('kind')} {fact.get('value')}", existing_ids
                    )
                facts.append(fact)
                existing_ids.add(fact.get("id"))
                actions.append(
                    {
                        "classification": "NEW",
                        "action": "ADD",
                        "entity": "fact",
                        "incoming_id": fact.get("id"),
                    }
                )

    @staticmethod
    def _merge_gaps(twin: dict[str, Any], candidate: dict[str, Any]) -> None:
        existing = {(gap.get("field_path"), gap.get("resolution_question")) for gap in twin.get("gaps", [])}
        existing_ids = {gap.get("id") for gap in twin.get("gaps", [])}
        for gap in candidate.get("gaps", []):
            key = (gap.get("field_path"), gap.get("resolution_question"))
            if key not in existing:
                if gap.get("id") in existing_ids:
                    gap["id"] = ReconciliationAgent._unique_id(
                        "gap", f"{gap.get('field_path')} {gap.get('resolution_question')}", existing_ids
                    )
                twin.setdefault("gaps", []).append(gap)
                existing_ids.add(gap.get("id"))
                existing.add(key)

    def _merge_inferences(self, twin: dict[str, Any], candidate: dict[str, Any]) -> None:
        existing_ids = {item.get("id") for item in twin.get("inferences", [])}
        evidence_ids = {item.get("id") for item in twin.get("evidence_items", [])}
        for inference in candidate.get("inferences", []):
            inference["supporting_evidence_ids"] = [
                item for item in inference.get("supporting_evidence_ids", []) if item in evidence_ids
            ]
            if not inference["supporting_evidence_ids"]:
                continue
            existing = self._find_matching_inference(twin, inference)
            if existing is not None:
                self._merge_inference(existing, inference)
                continue
            if inference.get("id") in existing_ids:
                inference["id"] = ReconciliationAgent._unique_id(
                    "inf", f"{inference.get('kind')} {inference.get('value')}", existing_ids
                )
            twin.setdefault("inferences", []).append(inference)
            existing_ids.add(inference.get("id"))

    @staticmethod
    def _remap_candidate_evidence_refs(
        candidate: dict[str, Any],
        evidence_id_map: dict[str, str],
    ) -> None:
        if not evidence_id_map:
            return
        for inference in candidate.get("inferences", []):
            inference["supporting_evidence_ids"] = [
                evidence_id_map.get(evidence_id, evidence_id)
                for evidence_id in inference.get("supporting_evidence_ids", [])
            ]
        for item in candidate.get("reflection", {}).get("overview_brief_items", []):
            item["supporting_evidence_ids"] = [
                evidence_id_map.get(evidence_id, evidence_id)
                for evidence_id in item.get("supporting_evidence_ids", [])
            ]

    @staticmethod
    def _find_matching_inference(
        twin: dict[str, Any],
        incoming: dict[str, Any],
    ) -> dict[str, Any] | None:
        incoming_tokens = _meaningful_tokens(incoming.get("value"))
        for existing in twin.get("inferences", []):
            if existing.get("kind") != incoming.get("kind"):
                continue
            token_score = _jaccard(incoming_tokens, _meaningful_tokens(existing.get("value")))
            text_score = SequenceMatcher(
                None, _normalize(existing.get("value")), _normalize(incoming.get("value"))
            ).ratio()
            if max(token_score, text_score) >= 0.62:
                return existing
        return None

    @staticmethod
    def _merge_inference(target: dict[str, Any], incoming: dict[str, Any]) -> None:
        existing_support = set(target.get("supporting_evidence_ids", []))
        incoming_support = set(incoming.get("supporting_evidence_ids", []))
        new_distinct_support = incoming_support - existing_support
        support = list(dict.fromkeys([
            *target.get("supporting_evidence_ids", []),
            *incoming.get("supporting_evidence_ids", []),
        ]))
        target["supporting_evidence_ids"] = support
        if new_distinct_support:
            target["confidence"] = max(target.get("confidence", 0), incoming.get("confidence", 0))
        if new_distinct_support and len(str(incoming.get("rationale", ""))) > len(str(target.get("rationale", ""))):
            target["rationale"] = incoming.get("rationale")
        target["alternatives"] = list(dict.fromkeys([
            *target.get("alternatives", []),
            *incoming.get("alternatives", []),
        ]))

    @staticmethod
    def _refresh_reflection(
        twin: dict[str, Any],
        candidate: dict[str, Any] | None = None,
    ) -> None:
        existing_reflection = twin.get("reflection", {})
        candidate_reflection = (candidate or {}).get("reflection", {})
        summary = candidate_reflection.get("summary") or existing_reflection.get("summary") or ""
        if summary.startswith("This staged extraction found"):
            summary = existing_reflection.get("summary", summary)
        supported = _merge_short_lists(
            candidate_reflection.get("strongly_supported", []),
            existing_reflection.get("strongly_supported", []),
            [inference.get("value", "") for inference in twin.get("inferences", [])],
            limit=8,
        )
        unclear = _merge_short_lists(
            candidate_reflection.get("unclear", []),
            existing_reflection.get("unclear", []),
            [gap.get("resolution_question", "") for gap in twin.get("gaps", [])],
            limit=6,
        )
        twin["reflection"] = {
            "summary": summary,
            "strongly_supported": supported,
            "unclear": unclear,
            "suggested_questions": unclear,
            "overview_brief_items": _merge_overview_brief_items(
                candidate_reflection.get("overview_brief_items", []),
                existing_reflection.get("overview_brief_items", []),
            ),
        }

    @staticmethod
    def _manual_source_document(text: str) -> dict[str, Any]:
        digest = hashlib.sha256(text.strip().encode("utf-8")).hexdigest()
        counters: dict[str, int] = {}
        blocks = []
        for index, line in enumerate(_manual_achievement_lines(text), start=1):
            minimized, redactions = minimize_direct_identifiers(line, counters=counters)
            blocks.append(
                {
                    "id": f"block_manual_{index}",
                    "locator": {"kind": "record", "value": f"manual-entry:{index}"},
                    "text": minimized,
                    "redactions": [
                        {"category": item.category, "placeholder": item.placeholder}
                        for item in redactions
                    ],
                }
            )
        return {
            "schema_version": "0.1.0",
            "source_id": f"src_{digest[:16]}",
            "source_type": "user_entered_data",
            "media_type": "text/plain",
            "content_hash": f"sha256:{digest}",
            "ingested_at": datetime.now(UTC).isoformat(),
            "adapter": {"name": "manual_evidence", "version": "0.1.0"},
            "privacy": {
                "classification": "personal_data",
                "direct_identifiers_minimized": True,
                "enrollment_candidates_separated": True,
            },
            "blocks": blocks,
        }

    @staticmethod
    def _unique_id(prefix: str, text: str, existing_ids: set[str | None]) -> str:
        digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]
        candidate = f"{prefix}_{digest}"
        counter = 2
        while candidate in existing_ids:
            candidate = f"{prefix}_{digest}_{counter}"
            counter += 1
        return candidate


def _normalize(value: Any) -> str:
    return re.sub(r"[^a-z0-9%€$£]+", " ", str(value or "").lower()).strip()


def _metrics(value: Any) -> set[str]:
    text = str(value or "").lower()
    return set(
        re.findall(
            r"(?:>\s?)?(?:\d{1,3}(?:,\d{3})+(?:\.\d+)?%?|"
            r"\d+(?:\.\d+)?%|[€$£]\s?\d{1,3}(?:,\d{3})+(?:\.\d+)?[kmb]?|"
            r"[€$£]\s?\d+(?:\.\d+)?[kmb]?|"
            r"\d+(?:\.\d+)?\s?(?:m|k|million|markets?|staff|cohorts?|customers?|users?|months?|years?))",
            text,
        )
    )


def _evidence_similarity(existing: dict[str, Any], incoming: dict[str, Any]) -> float:
    # General duplicate heuristic:
    # - exact phrasing is useful but insufficient for CV variants;
    # - shared numbers/currency and role context are strong evidence;
    # - token containment catches concise vs elaborated rephrasings.
    # This intentionally avoids source- or example-specific rules.
    existing_text = existing.get("text")
    incoming_text = incoming.get("text")
    normalized_existing = _normalize(existing_text)
    normalized_incoming = _normalize(incoming_text)
    sequence = SequenceMatcher(None, normalized_existing, normalized_incoming).ratio()
    existing_tokens = _meaningful_tokens(existing_text)
    incoming_tokens = _meaningful_tokens(incoming_text)
    token_score = _jaccard(existing_tokens, incoming_tokens)
    containment = _containment(existing_tokens, incoming_tokens)
    metrics_existing = _metrics(existing_text)
    metrics_incoming = _metrics(incoming_text)
    metric_score = _jaccard(metrics_existing, metrics_incoming)
    signature_score = _signature_similarity(existing_tokens, incoming_tokens)
    score = max(sequence, token_score, containment * 0.95)
    if existing.get("role_id") == incoming.get("role_id"):
        score += 0.08
    if metrics_existing and metrics_incoming:
        score += min(0.18, metric_score * 0.18)
    if metrics_existing & metrics_incoming:
        score = max(score, signature_score + 0.18)
        if containment >= 0.5:
            score = max(score, 0.88)
    return min(1.0, score)


def _meaningful_tokens(value: Any) -> set[str]:
    stopwords = {
        "a",
        "an",
        "and",
        "by",
        "for",
        "from",
        "in",
        "into",
        "of",
        "the",
        "through",
        "to",
        "with",
        "across",
        "via",
        "using",
    }
    return {
        _stem(token)
        for token in re.findall(r"[a-z0-9€$£>]+", str(value or "").lower())
        if token not in stopwords and len(token) > 1
    }


def _stem(token: str) -> str:
    for suffix in ("ing", "ed", "es", "s"):
        if len(token) > len(suffix) + 3 and token.endswith(suffix):
            return token[: -len(suffix)]
    return token


def _jaccard(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / len(left | right)


def _containment(left: set[str], right: set[str]) -> float:
    if not left or not right:
        return 0.0
    return len(left & right) / min(len(left), len(right))


def _signature_similarity(left: set[str], right: set[str]) -> float:
    """Compare the core event/entity words without requiring identical outcomes."""

    low_information = {
        "achiev",
        "achievement",
        "business",
        "customer",
        "customers",
        "deliv",
        "enable",
        "enabled",
        "improv",
        "increase",
        "increased",
        "led",
        "measur",
        "month",
        "months",
        "outcome",
        "reduc",
        "reduced",
        "scal",
        "scaled",
        "support",
        "supporting",
        "team",
        "teams",
        "user",
        "users",
        "value",
    }
    left_signature = {
        token for token in left if not token.isdigit() and token not in low_information
    }
    right_signature = {
        token for token in right if not token.isdigit() and token not in low_information
    }
    return _containment(left_signature, right_signature)


def _merge_short_lists(*lists: list[str], limit: int) -> list[str]:
    merged: list[str] = []
    seen: set[str] = set()
    for values in lists:
        for value in values:
            text = str(value or "").strip()
            key = _normalize(text)
            if not text:
                continue
            match_index = _find_similar_short_text(merged, text)
            if match_index is not None:
                merged[match_index] = _preferred_short_text(merged[match_index], text)
                seen.add(key)
                continue
            if key not in seen:
                merged.append(text)
                seen.add(key)
            if len(merged) >= limit:
                return merged
    return merged


def _merge_overview_brief_items(*lists: list[dict[str, Any]]) -> list[dict[str, Any]]:
    merged: list[dict[str, Any]] = []
    for items in lists:
        for item in items or []:
            item = _normalized_overview_brief_item(item)
            if item is None:
                continue
            if not _overview_brief_item_has_required_support(item):
                continue
            match = _find_similar_overview_brief_item(merged, item)
            if match is None:
                merged.append(deepcopy(item))
                continue
            existing = merged[match]
            preferred_text = _preferred_short_text(
                str(existing.get("text", "")),
                str(item.get("text", "")),
            )
            existing["text"] = preferred_text
            existing["salience"] = max(existing.get("salience", 0), item.get("salience", 0))
            existing["confidence"] = max(existing.get("confidence", 0), item.get("confidence", 0))
            existing["supporting_evidence_ids"] = list(dict.fromkeys([
                *existing.get("supporting_evidence_ids", []),
                *item.get("supporting_evidence_ids", []),
            ]))
    section_order = {
        "career_in_brief": 0,
        "patterns_and_structural_observations": 1,
        "areas_of_higher_confidence": 2,
        "areas_of_less_clarity": 3,
        "professionally_salient_attention_items": 4,
        "confidence_statement": 5,
    }
    sorted_items = sorted(
        merged,
        key=lambda item: (
            section_order.get(item.get("section"), 99),
            -_overview_brief_strength(item),
            item.get("text", ""),
        ),
    )
    return _limit_overview_brief_sections(_editorial_pass_overview_brief_items(sorted_items))


def _editorial_pass_overview_brief_items(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    edited: list[dict[str, Any]] = []
    for item in items:
        if _is_redundant_overview_brief_item(edited, item):
            continue
        edited.append(item)
    return edited


def _is_redundant_overview_brief_item(
    previous_items: list[dict[str, Any]],
    incoming: dict[str, Any],
) -> bool:
    incoming_section = incoming.get("section")
    incoming_text = str(incoming.get("text") or "")
    incoming_tokens = _meaningful_tokens(incoming_text)
    incoming_signature = _editorial_signature(incoming_tokens)
    incoming_metrics = _metrics(incoming_text)
    for item in previous_items:
        if item.get("section") != incoming_section:
            continue
        existing_text = str(item.get("text") or "")
        existing_tokens = _meaningful_tokens(existing_text)
        if not incoming_tokens or not existing_tokens:
            continue
        containment = _containment(incoming_tokens, existing_tokens)
        token_score = _jaccard(incoming_tokens, existing_tokens)
        shared_signature = incoming_signature & _editorial_signature(existing_tokens)
        shared_metrics = incoming_metrics & _metrics(existing_text)
        if containment >= 0.62 or token_score >= 0.5:
            return True
        if len(shared_signature) >= 2 and containment >= 0.36:
            return True
        if shared_metrics and len(shared_signature) >= 1 and containment >= 0.32:
            return True
        if (
            incoming_section == "patterns_and_structural_observations"
            and _operating_model_editorial_overlap(incoming_tokens, existing_tokens)
        ):
            return True
    return False


def _operating_model_editorial_overlap(left: set[str], right: set[str]) -> bool:
    operating_terms = {"model", "operat", "operating"}
    structure_terms = {
        "dependenci",
        "delivery",
        "engineering",
        "engineer",
        "organization",
        "organizations",
        "platform",
        "product",
        "scale",
        "scaling",
        "speed",
        "structur",
        "team",
        "teams",
        "velocity",
    }
    return (
        bool(left & operating_terms)
        and bool(right & operating_terms)
        and bool(left & structure_terms)
        and bool(right & structure_terms)
    )


def _editorial_signature(tokens: set[str]) -> set[str]:
    signature_terms = {
        "adoption",
        "ai",
        "automation",
        "banking",
        "capabilities",
        "cloud",
        "compliance",
        "consult",
        "consulting",
        "cost",
        "delivery",
        "domain",
        "engineering",
        "enterprise",
        "governance",
        "international",
        "leadership",
        "management",
        "metric",
        "metrics",
        "model",
        "models",
        "operat",
        "operating",
        "outcome",
        "outcomes",
        "platform",
        "product",
        "regulated",
        "reliability",
        "reorganiz",
        "scale",
        "scaling",
        "speed",
        "structur",
        "team",
        "teams",
        "transformation",
        "velocity",
    }
    return tokens & signature_terms


def _overview_brief_strength(item: dict[str, Any]) -> float:
    support_count = len(item.get("supporting_evidence_ids", []) or [])
    support_bonus = min(0.25, support_count * 0.06)
    kind = item.get("kind")
    kind_bonus = {
        "interpretation": 0.05,
        "observation": 0.03,
        "attention_item": 0.02,
        "uncertainty": 0.0,
        "confidence_statement": 0.0,
    }.get(kind, 0.0)
    metric_bonus = 0.06 if _metrics(item.get("text")) else 0.0
    return (
        float(item.get("salience", 0) or 0) * 0.5
        + float(item.get("confidence", 0) or 0) * 0.25
        + support_bonus
        + kind_bonus
        + metric_bonus
    )


def _overview_brief_item_has_required_support(item: dict[str, Any]) -> bool:
    kind = item.get("kind")
    if kind not in {"interpretation", "attention_item"}:
        return True
    return bool(item.get("supporting_evidence_ids"))


def _limit_overview_brief_sections(items: list[dict[str, Any]]) -> list[dict[str, Any]]:
    section_limits = {
        "career_in_brief": 2,
        "patterns_and_structural_observations": 6,
        "areas_of_higher_confidence": 5,
        "areas_of_less_clarity": 2,
        "professionally_salient_attention_items": 3,
        "confidence_statement": 1,
    }
    counts: dict[str, int] = {}
    limited: list[dict[str, Any]] = []
    for item in items:
        section = str(item.get("section") or "")
        count = counts.get(section, 0)
        if count >= section_limits.get(section, 3):
            continue
        limited.append(item)
        counts[section] = count + 1
    return limited[:19]


def _find_similar_overview_brief_item(
    existing: list[dict[str, Any]],
    incoming: dict[str, Any],
) -> int | None:
    incoming_section = incoming.get("section")
    incoming_text = str(incoming.get("text") or "")
    incoming_tokens = _meaningful_tokens(incoming_text)
    incoming_metrics = _metrics(incoming_text)
    for index, item in enumerate(existing):
        if item.get("section") != incoming_section:
            continue
        existing_text = str(item.get("text") or "")
        existing_tokens = _meaningful_tokens(existing_text)
        shared = len(incoming_tokens & existing_tokens)
        if shared < 3:
            continue
        token_score = _jaccard(incoming_tokens, existing_tokens)
        containment = _containment(incoming_tokens, existing_tokens)
        text_score = SequenceMatcher(
            None,
            _normalize(incoming_text),
            _normalize(existing_text),
        ).ratio()
        shared_metrics = incoming_metrics & _metrics(existing_text)
        if max(token_score, text_score) >= 0.54 or containment >= 0.48:
            return index
        if shared_metrics and (token_score >= 0.34 or containment >= 0.34):
            return index
        if incoming_section == "areas_of_less_clarity" and containment >= 0.42:
            return index
        if incoming_section == "confidence_statement" and _confidence_statement_overlap(
            incoming_tokens, existing_tokens
        ):
            return index
        if incoming_section == "areas_of_higher_confidence" and _capability_domain_overlap(
            incoming_tokens, existing_tokens
        ):
            return index
        if incoming_section == "career_in_brief" and _career_scope_overlap(
            incoming_tokens, existing_tokens
        ):
            return index
        if incoming_section == "areas_of_higher_confidence" and _outcome_domain_overlap(
            incoming_text,
            existing_text,
            incoming_tokens,
            existing_tokens,
        ):
            return index
        if (
            incoming_section == "professionally_salient_attention_items"
            and _contract_transition_overlap(incoming_tokens, existing_tokens)
        ):
            return index
    return None


def _confidence_statement_overlap(left: set[str], right: set[str]) -> bool:
    confidence_terms = {
        "confidence",
        "confid",
        "direct",
        "explicit",
        "extract",
        "fact",
        "facts",
        "metric",
        "metrics",
        "outcome",
        "outcomes",
        "project",
        "projects",
        "role",
        "roles",
        "source",
        "support",
        "supported",
    }
    return len((left & right) & confidence_terms) >= 3


def _capability_domain_overlap(left: set[str], right: set[str]) -> bool:
    capability_terms = {
        "ai",
        "automation",
        "dashboard",
        "dashboards",
        "design",
        "develop",
        "development",
        "framework",
        "frameworks",
        "grant",
        "grants",
        "health",
        "healthcare",
        "implement",
        "implementation",
        "kpi",
        "kpis",
        "mel",
        "monitor",
        "monitoring",
        "operational",
        "operationalizing",
        "platform",
        "program",
        "programs",
        "system",
        "systems",
        "theory",
    }
    shared_terms = (left & right) & capability_terms
    return len(shared_terms) >= 2 and _containment(left & capability_terms, right & capability_terms) >= 0.4


def _career_scope_overlap(left: set[str], right: set[str]) -> bool:
    scope_terms = {
        "career",
        "role",
        "roles",
        "senior",
        "technology",
        "transformation",
        "platform",
        "leadership",
        "industr",
        "industry",
        "industries",
        "geograph",
        "geographies",
        "financial",
        "services",
        "retail",
        "consult",
        "consulting",
        "life",
        "science",
        "sciences",
    }
    shared_scope = (left & right) & scope_terms
    return len(shared_scope) >= 4 and (
        ("career" in left and "career" in right)
        or ("role" in left and "role" in right)
        or ("roles" in left and "roles" in right)
    )


def _outcome_domain_overlap(
    left_text: str,
    right_text: str,
    left: set[str],
    right: set[str],
) -> bool:
    outcome_terms = {
        "adoption",
        "cost",
        "failure",
        "financial",
        "impact",
        "metric",
        "metrics",
        "operational",
        "outcome",
        "outcomes",
        "quantified",
        "reduction",
        "reductions",
        "reliability",
        "release",
        "revenue",
        "roi",
        "saving",
        "savings",
        "throughput",
        "velocity",
    }
    shared_outcomes = (left & right) & outcome_terms
    shared_metrics = _metrics(left_text) & _metrics(right_text)
    return len(shared_outcomes) >= 2 and (
        len(shared_metrics) >= 1 or _containment(left & outcome_terms, right & outcome_terms) >= 0.4
    )


def _contract_transition_overlap(left: set[str], right: set[str]) -> bool:
    contract_terms = {"contract", "contracts", "consult", "consultancy", "consulting", "interim"}
    transition_terms = {
        "duration",
        "engagement",
        "engagements",
        "frequent",
        "medium",
        "multiple",
        "permanent",
        "placement",
        "preference",
        "reflect",
        "short",
        "transition",
        "transitions",
    }
    return (
        bool(left & contract_terms)
        and bool(right & contract_terms)
        and bool(left & transition_terms)
        and bool(right & transition_terms)
    )


def _normalized_overview_brief_item(item: dict[str, Any]) -> dict[str, Any] | None:
    text = str(item.get("text") or "").strip()
    if not text:
        return None
    normalized = deepcopy(item)
    normalized["text"] = text
    lower = text.lower()
    tokens = _meaningful_tokens(text)
    if _is_logistical_cv_gap(lower):
        return None
    if _is_confidence_statement_item(tokens):
        normalized["section"] = "confidence_statement"
    elif _is_quantified_outcome_item(text, tokens):
        normalized["section"] = "areas_of_higher_confidence"
    elif _is_contract_transition_attention_item(tokens):
        normalized["section"] = "professionally_salient_attention_items"
    elif _is_uncertainty_item(lower, tokens):
        normalized["section"] = "areas_of_less_clarity"
    elif _is_governance_operating_model_pattern(tokens):
        normalized["section"] = "patterns_and_structural_observations"
    elif _is_team_or_leadership_pattern(tokens):
        normalized["section"] = "patterns_and_structural_observations"
    return normalized


def _is_logistical_cv_gap(text: str) -> bool:
    logistical_terms = (
        "availability",
        "notice period",
        "reason for end",
        "reason for short",
        "reason for six-month",
        "reason for 6-month",
        "ongoing availability",
        "handoff",
        "hand-off",
        "long-term ownership",
        "longer-term impact",
        "post-engagement",
        "retention outcome",
        "retention outcomes",
        "retained vs pure-contract",
        "indicative of turnover",
        "project-limited",
    )
    return any(term in text for term in logistical_terms)


def _is_quantified_outcome_item(text: str, tokens: set[str]) -> bool:
    outcome_terms = {
        "adoption",
        "automation",
        "cost",
        "costs",
        "failure",
        "financial",
        "metric",
        "metrics",
        "operational",
        "outcome",
        "outcomes",
        "reduction",
        "reductions",
        "reliability",
        "release",
        "revenue",
        "roi",
        "saving",
        "savings",
        "throughput",
    }
    return bool(_metrics(text)) and bool(tokens & outcome_terms)


def _is_contract_transition_attention_item(tokens: set[str]) -> bool:
    contract_terms = {"contract", "contracts", "consult", "consultancy", "consulting", "interim"}
    attention_terms = {
        "availability",
        "clarify",
        "engagement",
        "engagements",
        "frequent",
        "multiple",
        "permanent",
        "preference",
        "short",
        "transition",
        "transitions",
    }
    return bool(tokens & contract_terms) and bool(tokens & attention_terms)


def _is_confidence_statement_item(tokens: set[str]) -> bool:
    confidence_terms = {"based", "confidence", "confid", "explicit", "evidence", "observations", "source"}
    claim_terms = {"claims", "descriptions", "outcomes", "role", "roles", "technical"}
    return len(tokens & confidence_terms) >= 2 and bool(tokens & claim_terms)


def _is_uncertainty_item(text: str, tokens: set[str]) -> bool:
    uncertainty_phrases = (
        "limited explicit detail",
        "limited public detail",
        "not fully quantified",
        "not fully enumerated",
        "not explicit",
        "not described",
        "unclear",
    )
    uncertainty_terms = {"detail", "explicit", "limited", "unclear", "quantified"}
    scope_terms = {"p&l", "reporting", "line", "lines", "direct", "management", "headcount", "scope"}
    return any(phrase in text for phrase in uncertainty_phrases) or (
        bool(tokens & uncertainty_terms) and bool(tokens & scope_terms)
    )


def _is_governance_operating_model_pattern(tokens: set[str]) -> bool:
    governance_terms = {"governance", "operating", "model", "models", "regulated"}
    delivery_terms = {"design", "implement", "implementation", "organization", "organizations", "organisation", "organisations"}
    return bool(tokens & governance_terms) and bool(tokens & delivery_terms)


def _is_team_or_leadership_pattern(tokens: set[str]) -> bool:
    team_terms = {"headcount", "leadership", "management", "managerial", "organization", "organisations", "restructur", "team", "teams"}
    scale_terms = {"direct", "distributed", "line", "matrix", "multi", "multinational", "reorganiz", "scale", "scaling", "scope"}
    return bool(tokens & team_terms) and bool(tokens & scale_terms)


def _find_similar_short_text(existing: list[str], incoming: str) -> int | None:
    incoming_tokens = _meaningful_tokens(incoming)
    for index, value in enumerate(existing):
        existing_tokens = _meaningful_tokens(value)
        shared = len(incoming_tokens & existing_tokens)
        if shared < 3:
            continue
        token_score = _jaccard(incoming_tokens, existing_tokens)
        containment = _containment(incoming_tokens, existing_tokens)
        text_score = SequenceMatcher(
            None,
            _normalize(incoming),
            _normalize(value),
        ).ratio()
        if max(token_score, text_score) >= 0.58 or containment >= 0.5:
            return index
    return None


def _preferred_short_text(existing: str, incoming: str) -> str:
    # Prefer the richer phrasing, but avoid replacing a useful short label with
    # a much longer sentence unless it carries materially more information.
    existing_tokens = _meaningful_tokens(existing)
    incoming_tokens = _meaningful_tokens(incoming)
    if len(incoming_tokens) >= len(existing_tokens) + 2:
        return incoming
    return existing


def _manual_achievement_lines(text: str) -> list[str]:
    return [line.strip() for line in text.splitlines() if line.strip()]


def _manual_source_label(source_doc: dict[str, Any]) -> str:
    blocks = source_doc.get("blocks", [])
    if len(blocks) == 1:
        return blocks[0].get("text", "")[:80] or "User entered achievement"
    return f"{len(blocks)} user entered achievements"
