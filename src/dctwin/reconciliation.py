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

        for item in candidate.get("evidence_items", []):
            if item.get("role_id") in role_map:
                item["role_id"] = role_map[item["role_id"]]
            match = self._best_evidence_match(twin, item)
            if match is None:
                self._add_unique("evidence_items", twin, item)
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
                counts["evidence_merged"] += 1
                actions.append(
                    {
                        "classification": "DUPLICATE",
                        "action": "MERGE_PROVENANCE",
                        "entity": "evidence",
                        "incoming_id": item.get("id"),
                        "target_id": existing_item.get("id"),
                        "score": round(score, 3),
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
        evidence_text = source_doc["blocks"][0]["text"]
        source = {
            "id": source_doc["source_id"],
            "type": "user_entered_data",
            "label": source_doc["blocks"][0]["text"][:80] or "User entered evidence",
            "adapter": "manual_evidence@0.1.0",
            "content_hash": source_doc["content_hash"],
        }
        if source["id"] not in {item.get("id") for item in updated.get("sources", [])}:
            updated.setdefault("sources", []).append(source)

        evidence = {
            "id": self._unique_id(
                "ev",
                evidence_text,
                {item.get("id") for item in updated.get("evidence_items", [])},
            ),
            "type": classify_evidence(evidence_text),
            "text": evidence_text,
            "role_id": role_id,
            "context": "Manually entered by user.",
            "source_refs": [
                {
                    "source_id": source_doc["source_id"],
                    "block_id": "block_manual_1",
                    "quote": evidence_text,
                }
            ],
            "tag_assignments": tag_assignments(evidence_text, tag_catalog),
        }
        match = self._best_evidence_match(updated, evidence)
        actions: list[dict[str, Any]]
        if match and match[1] >= self.exact_threshold:
            target, score = match
            self._merge_source_refs(target, evidence)
            self._merge_tag_assignments(target, evidence)
            summary = ReconciliationSummary(
                roles_detected=0,
                evidence_extracted=1,
                evidence_matched=1,
                evidence_merged=1,
                actions=[
                    {
                        "classification": "DUPLICATE",
                        "action": "MERGE_PROVENANCE",
                        "entity": "manual_evidence",
                        "target_id": target.get("id"),
                        "score": round(score, 3),
                    }
                ],
            )
        else:
            if match:
                evidence["context"] = (
                    f"Possible duplicate of {match[0].get('id')}. "
                    "Manually entered by user."
                )
                possible_duplicates = 1
                actions = [
                    {
                        "classification": "POSSIBLE_DUPLICATE",
                        "action": "ADD_WITH_POSSIBLE_DUPLICATE_CONTEXT",
                        "entity": "manual_evidence",
                        "target_id": match[0].get("id"),
                        "appended_id": evidence["id"],
                        "score": round(match[1], 3),
                    }
                ]
            else:
                possible_duplicates = 0
                actions = [
                    {
                        "classification": "NEW",
                        "action": "ADD",
                        "entity": "manual_evidence",
                        "appended_id": evidence["id"],
                    }
                ]
            updated.setdefault("evidence_items", []).append(evidence)
            summary = ReconciliationSummary(
                evidence_extracted=1,
                evidence_matched=1 if match else 0,
                evidence_added=1,
                possible_duplicates=possible_duplicates,
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
        support = list(dict.fromkeys([
            *target.get("supporting_evidence_ids", []),
            *incoming.get("supporting_evidence_ids", []),
        ]))
        target["supporting_evidence_ids"] = support
        target["confidence"] = max(target.get("confidence", 0), incoming.get("confidence", 0))
        if len(str(incoming.get("rationale", ""))) > len(str(target.get("rationale", ""))):
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
        }

    @staticmethod
    def _manual_source_document(text: str) -> dict[str, Any]:
        digest = hashlib.sha256(text.strip().encode("utf-8")).hexdigest()
        minimized, redactions = minimize_direct_identifiers(text.strip(), counters={})
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
            "blocks": [
                {
                    "id": "block_manual_1",
                    "locator": {"kind": "record", "value": "manual-entry:1"},
                    "text": minimized,
                    "redactions": [
                        {"category": item.category, "placeholder": item.placeholder}
                        for item in redactions
                    ],
                }
            ],
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
            r"(?:>\s?)?(?:\d+(?:\.\d+)?%|[€$£]\s?\d+(?:\.\d+)?[kmb]?|\d+(?:\.\d+)?\s?(?:m|k|million|markets?|staff|cohorts?))",
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
    score = max(sequence, token_score, containment * 0.95)
    if existing.get("role_id") == incoming.get("role_id"):
        score += 0.08
    if metrics_existing and metrics_incoming:
        score += min(0.18, metric_score * 0.18)
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


def _merge_short_lists(*lists: list[str], limit: int) -> list[str]:
    merged: list[str] = []
    seen: set[str] = set()
    for values in lists:
        for value in values:
            text = str(value or "").strip()
            key = _normalize(text)
            if text and key not in seen:
                merged.append(text)
                seen.add(key)
            if len(merged) >= limit:
                return merged
    return merged
