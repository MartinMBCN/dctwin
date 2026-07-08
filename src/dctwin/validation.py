from __future__ import annotations

from collections import Counter
from typing import Any, Iterable

from jsonschema import Draft202012Validator, FormatChecker


class ContractValidationError(ValueError):
    def __init__(self, issues: Iterable[str]) -> None:
        self.issues = tuple(issues)
        super().__init__("\n".join(self.issues))


def _schema_issues(document: dict[str, Any], schema: dict[str, Any]) -> list[str]:
    validator = Draft202012Validator(schema, format_checker=FormatChecker())
    issues: list[str] = []
    for error in sorted(
        validator.iter_errors(document), key=lambda item: list(item.absolute_path)
    ):
        path = ".".join(str(part) for part in error.absolute_path) or "$"
        if error.validator == "contains":
            required_type = (
                error.schema.get("contains", {})
                .get("properties", {})
                .get("tag_type", {})
                .get("const")
            )
            if required_type:
                issues.append(
                    f"{path}: must include at least one tag assignment with "
                    f"tag_type={required_type!r}"
                )
                continue
        issues.append(f"{path}: {error.message}")
    return issues


def _duplicates(values: Iterable[str]) -> set[str]:
    counts = Counter(values)
    return {value for value, count in counts.items() if count > 1}


def validate_source_document(document: dict[str, Any], schema: dict[str, Any]) -> None:
    issues = _schema_issues(document, schema)
    block_ids = [block["id"] for block in document.get("blocks", []) if "id" in block]
    for duplicate in sorted(_duplicates(block_ids)):
        issues.append(f"blocks: duplicate block id {duplicate!r}")
    if issues:
        raise ContractValidationError(issues)


def validate_enrollment_document(document: dict[str, Any], schema: dict[str, Any]) -> None:
    issues = _schema_issues(document, schema)
    values = [
        (candidate.get("type"), candidate.get("value"))
        for candidate in document.get("candidates", [])
    ]
    for duplicate in sorted(_duplicates(f"{kind}:{value}" for kind, value in values)):
        issues.append(f"candidates: duplicate enrollment candidate {duplicate!r}")
    if issues:
        raise ContractValidationError(issues)


def validate_tag_catalog(catalog: dict[str, Any], schema: dict[str, Any]) -> None:
    issues = _schema_issues(catalog, schema)
    tag_ids = [tag["id"] for tag in catalog.get("tags", []) if "id" in tag]
    for duplicate in sorted(_duplicates(tag_ids)):
        issues.append(f"tags: duplicate tag id {duplicate!r}")
    if issues:
        raise ContractValidationError(issues)


def validate_twin(
    twin: dict[str, Any],
    schema: dict[str, Any],
    tag_catalog: dict[str, Any],
    source_documents: Iterable[dict[str, Any]] | None = None,
) -> None:
    issues = _schema_issues(twin, schema)

    sources = {source.get("id") for source in twin.get("sources", [])}
    roles = {role.get("id") for role in twin.get("roles", [])}
    evidence = {item.get("id") for item in twin.get("evidence_items", [])}
    catalog = {tag.get("id"): tag.get("type") for tag in tag_catalog.get("tags", [])}
    normalized_sources = {
        source.get("source_id"): source for source in (source_documents or [])
    }
    known_blocks = {
        source_id: {block.get("id") for block in source.get("blocks", [])}
        for source_id, source in normalized_sources.items()
    }

    id_groups = {
        "sources": [source.get("id") for source in twin.get("sources", [])],
        "roles": [role.get("id") for role in twin.get("roles", [])],
        "evidence_items": [item.get("id") for item in twin.get("evidence_items", [])],
        "facts": [fact.get("id") for fact in twin.get("person", {}).get("facts", [])],
        "inferences": [item.get("id") for item in twin.get("inferences", [])],
        "gaps": [gap.get("id") for gap in twin.get("gaps", [])],
    }
    for label, values in id_groups.items():
        for duplicate in sorted(_duplicates(value for value in values if value)):
            issues.append(f"{label}: duplicate id {duplicate!r}")

    def check_refs(owner: str, refs: Iterable[dict[str, Any]]) -> None:
        for ref in refs:
            source_id = ref.get("source_id")
            if source_id not in sources:
                issues.append(f"{owner}: unknown source_id {source_id!r}")
            elif source_id in known_blocks and ref.get("block_id") not in known_blocks[source_id]:
                issues.append(
                    f"{owner}: unknown block_id {ref.get('block_id')!r} "
                    f"for source {source_id!r}"
                )

    for fact in twin.get("person", {}).get("facts", []):
        check_refs(f"fact {fact.get('id')}", fact.get("source_refs", []))
    for preference in twin.get("person", {}).get("preferences", []):
        check_refs(f"preference {preference.get('kind')}", preference.get("source_refs", []))
    for role in twin.get("roles", []):
        check_refs(f"role {role.get('id')}", role.get("source_refs", []))

    for item in twin.get("evidence_items", []):
        owner = f"evidence {item.get('id')}"
        role_id = item.get("role_id")
        if role_id is not None and role_id not in roles:
            issues.append(f"{owner}: unknown role_id {role_id!r}")
        check_refs(owner, item.get("source_refs", []))
        assignment_groups = item.get("tag_assignments", {})
        for expected_type, group_name in (
            ("capability", "capabilities"),
            ("narrative_theme", "narrative_themes"),
        ):
            for assignment in assignment_groups.get(group_name, []):
                tag_id = assignment.get("tag_id")
                if tag_id not in catalog:
                    issues.append(f"{owner}: unknown tag_id {tag_id!r}")
                elif catalog[tag_id] != expected_type:
                    issues.append(
                        f"{owner}: tag {tag_id!r} is {catalog[tag_id]!r}, "
                        f"not {expected_type!r}"
                    )

    for inference in twin.get("inferences", []):
        owner = f"inference {inference.get('id')}"
        for evidence_id in inference.get("supporting_evidence_ids", []):
            if evidence_id not in evidence:
                issues.append(f"{owner}: unknown supporting evidence {evidence_id!r}")

    for brief_item in twin.get("reflection", {}).get("overview_brief_items", []):
        owner = f"overview brief item {brief_item.get('id')}"
        for evidence_id in brief_item.get("supporting_evidence_ids", []):
            if evidence_id not in evidence:
                issues.append(f"{owner}: unknown supporting evidence {evidence_id!r}")

    for source in twin.get("sources", []):
        normalized = normalized_sources.get(source.get("id"))
        if normalized and source.get("content_hash") != normalized.get("content_hash"):
            issues.append(
                f"source {source.get('id')}: content_hash does not match normalized source"
            )

    if twin.get("tag_catalog_version") != tag_catalog.get("version"):
        issues.append(
            "tag_catalog_version: Twin declares "
            f"{twin.get('tag_catalog_version')!r}, loaded catalog is {tag_catalog.get('version')!r}"
        )

    if issues:
        raise ContractValidationError(issues)
