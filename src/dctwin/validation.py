from __future__ import annotations

from collections import Counter
import re
from typing import Any, Iterable


class ContractValidationError(ValueError):
    def __init__(self, issues: Iterable[str]) -> None:
        self.issues = tuple(issues)
        super().__init__("\n".join(self.issues))


def _schema_issues(document: dict[str, Any], schema: dict[str, Any]) -> list[str]:
    issues: list[str] = []
    _validate_schema_subset(document, schema, schema, [], issues)
    return issues


def _validate_schema_subset(
    value: Any,
    rule: dict[str, Any],
    root: dict[str, Any],
    path: list[str],
    issues: list[str],
) -> None:
    if "$ref" in rule:
        rule = _resolve_ref(root, rule["$ref"])

    if "anyOf" in rule:
        branch_issues: list[list[str]] = []
        for branch in rule["anyOf"]:
            trial: list[str] = []
            _validate_schema_subset(value, branch, root, path, trial)
            if not trial:
                return
            branch_issues.append(trial)
        issues.append(f"{_path(path)}: does not match any allowed schema")
        return

    if "const" in rule and value != rule["const"]:
        issues.append(f"{_path(path)}: expected {rule['const']!r}")

    if "enum" in rule and value not in rule["enum"]:
        issues.append(f"{_path(path)}: expected one of {rule['enum']!r}")

    expected_type = rule.get("type")
    if expected_type is not None and not _matches_type(value, expected_type):
        issues.append(f"{_path(path)}: expected type {_type_label(expected_type)}")
        return

    if isinstance(value, str):
        if len(value) < rule.get("minLength", 0):
            issues.append(f"{_path(path)}: string is shorter than {rule['minLength']}")
        pattern = rule.get("pattern")
        if pattern and re.fullmatch(pattern, value) is None:
            issues.append(f"{_path(path)}: does not match pattern {pattern!r}")

    if isinstance(value, (int, float)) and not isinstance(value, bool):
        if "minimum" in rule and value < rule["minimum"]:
            issues.append(f"{_path(path)}: must be >= {rule['minimum']}")
        if "maximum" in rule and value > rule["maximum"]:
            issues.append(f"{_path(path)}: must be <= {rule['maximum']}")

    if isinstance(value, list):
        if "minItems" in rule and len(value) < rule["minItems"]:
            issues.append(f"{_path(path)}: must contain at least {rule['minItems']} item(s)")
        if "maxItems" in rule and len(value) > rule["maxItems"]:
            issues.append(f"{_path(path)}: must contain at most {rule['maxItems']} item(s)")
        if rule.get("uniqueItems") and len({repr(item) for item in value}) != len(value):
            issues.append(f"{_path(path)}: items must be unique")
        item_rule = rule.get("items")
        if isinstance(item_rule, dict):
            for index, item in enumerate(value):
                _validate_schema_subset(item, item_rule, root, [*path, str(index)], issues)
        contains_rule = rule.get("contains")
        if isinstance(contains_rule, dict):
            if not any(
                not _schema_issues_for_value(item, contains_rule, root, [*path, str(index)])
                for index, item in enumerate(value)
            ):
                required_type = (
                    contains_rule.get("properties", {})
                    .get("tag_type", {})
                    .get("const")
                )
                if required_type:
                    issues.append(
                        f"{_path(path)}: must include at least one tag assignment with "
                        f"tag_type={required_type!r}"
                    )
                else:
                    issues.append(f"{_path(path)}: must contain a matching item")

    if isinstance(value, dict):
        required = rule.get("required", [])
        for key in required:
            if key not in value:
                issues.append(f"{_path([*path, key])}: required property is missing")
        properties = rule.get("properties", {})
        if rule.get("additionalProperties") is False:
            for key in value:
                if key not in properties:
                    issues.append(f"{_path([*path, key])}: additional property is not allowed")
        for key, child_rule in properties.items():
            if key in value:
                _validate_schema_subset(value[key], child_rule, root, [*path, key], issues)


def _schema_issues_for_value(
    value: Any,
    rule: dict[str, Any],
    root: dict[str, Any],
    path: list[str],
) -> list[str]:
    issues: list[str] = []
    _validate_schema_subset(value, rule, root, path, issues)
    return issues


def _resolve_ref(root: dict[str, Any], ref: str) -> dict[str, Any]:
    if not ref.startswith("#/"):
        raise ValueError(f"Unsupported schema reference: {ref}")
    current: Any = root
    for part in ref.removeprefix("#/").split("/"):
        current = current[part]
    if not isinstance(current, dict):
        raise ValueError(f"Schema reference does not resolve to an object: {ref}")
    return current


def _matches_type(value: Any, expected: str | list[str]) -> bool:
    options = expected if isinstance(expected, list) else [expected]
    return any(_matches_single_type(value, option) for option in options)


def _matches_single_type(value: Any, expected: str) -> bool:
    if expected == "object":
        return isinstance(value, dict)
    if expected == "array":
        return isinstance(value, list)
    if expected == "string":
        return isinstance(value, str)
    if expected == "number":
        return isinstance(value, (int, float)) and not isinstance(value, bool)
    if expected == "integer":
        return isinstance(value, int) and not isinstance(value, bool)
    if expected == "boolean":
        return isinstance(value, bool)
    if expected == "null":
        return value is None
    raise ValueError(f"Unsupported schema type: {expected}")


def _type_label(expected: str | list[str]) -> str:
    return " or ".join(expected) if isinstance(expected, list) else expected


def _path(path: list[str]) -> str:
    return ".".join(path) or "$"


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
        if brief_item.get("kind") in {"interpretation", "attention_item"} and not brief_item.get("supporting_evidence_ids"):
            issues.append(f"{owner}: {brief_item.get('kind')} requires supporting evidence")
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
