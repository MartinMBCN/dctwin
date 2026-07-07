from __future__ import annotations

from copy import deepcopy
from pathlib import Path

import pytest
from jsonschema import Draft202012Validator

from dctwin.io import load_json
from dctwin.validation import (
    ContractValidationError,
    validate_enrollment_document,
    validate_source_document,
    validate_tag_catalog,
    validate_twin,
)


ROOT = Path(__file__).resolve().parents[1]


@pytest.fixture
def contracts() -> dict[str, dict]:
    return {
        "source_schema": load_json(ROOT / "schemas/source_document.schema.json"),
        "enrollment_schema": load_json(ROOT / "schemas/enrollment_candidates.schema.json"),
        "twin_schema": load_json(ROOT / "schemas/digital_career_twin.schema.json"),
        "tag_schema": load_json(ROOT / "schemas/tag_catalog.schema.json"),
        "catalog": load_json(ROOT / "catalogs/tag_catalog.json"),
        "source": load_json(ROOT / "tests/fixtures/valid_source.json"),
        "enrollment": load_json(
            ROOT / "tests/fixtures/valid_enrollment_candidates.json"
        ),
        "twin": load_json(ROOT / "tests/fixtures/valid_twin.json"),
    }


def test_schemas_are_valid_json_schema(contracts: dict[str, dict]) -> None:
    Draft202012Validator.check_schema(contracts["source_schema"])
    Draft202012Validator.check_schema(contracts["enrollment_schema"])
    Draft202012Validator.check_schema(contracts["twin_schema"])
    Draft202012Validator.check_schema(contracts["tag_schema"])


def test_valid_fixtures_pass_all_contracts(contracts: dict[str, dict]) -> None:
    validate_tag_catalog(contracts["catalog"], contracts["tag_schema"])
    validate_source_document(contracts["source"], contracts["source_schema"])
    validate_enrollment_document(
        contracts["enrollment"], contracts["enrollment_schema"]
    )
    validate_twin(
        contracts["twin"],
        contracts["twin_schema"],
        contracts["catalog"],
        source_documents=[contracts["source"]],
    )


def test_unknown_evidence_reference_is_rejected(contracts: dict[str, dict]) -> None:
    twin = deepcopy(contracts["twin"])
    twin["inferences"][0]["supporting_evidence_ids"] = ["ev_missing"]
    with pytest.raises(ContractValidationError, match="unknown supporting evidence"):
        validate_twin(twin, contracts["twin_schema"], contracts["catalog"])


def test_unknown_tag_is_rejected(contracts: dict[str, dict]) -> None:
    twin = deepcopy(contracts["twin"])
    twin["evidence_items"][0]["tag_assignments"]["capabilities"][0]["tag_id"] = "tag_invented"
    with pytest.raises(ContractValidationError, match="unknown tag_id"):
        validate_twin(twin, contracts["twin_schema"], contracts["catalog"])


def test_unknown_source_block_is_rejected(contracts: dict[str, dict]) -> None:
    twin = deepcopy(contracts["twin"])
    twin["evidence_items"][0]["source_refs"][0]["block_id"] = "block_missing"
    with pytest.raises(ContractValidationError, match="unknown block_id"):
        validate_twin(
            twin,
            contracts["twin_schema"],
            contracts["catalog"],
            source_documents=[contracts["source"]],
        )
