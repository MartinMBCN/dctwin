from __future__ import annotations

from pathlib import Path

from dctwin.adapters.registry import AdapterRegistry
from dctwin.adapters.base import AdaptedSource
from dctwin.agent import SourceAdapterAgent
from dctwin.io import load_json
from dctwin.providers import StaticTwinProvider


ROOT = Path(__file__).resolve().parents[1]


class SyntheticAdapter:
    source_type = "cv"

    def supports(self, path: Path) -> bool:
        return path.suffix == ".pdf"

    def adapt(self, path: Path) -> AdaptedSource:
        del path
        return AdaptedSource(
            model_document=load_json(ROOT / "tests/fixtures/valid_source.json"),
            enrollment_document=load_json(
                ROOT / "tests/fixtures/valid_enrollment_candidates.json"
            ),
        )


def test_source_adapter_agent_runs_a_validated_vertical_slice(tmp_path: Path) -> None:
    registry = AdapterRegistry()
    registry.register(SyntheticAdapter())
    expected = load_json(ROOT / "tests/fixtures/valid_twin.json")
    agent = SourceAdapterAgent(
        registry=registry,
        provider=StaticTwinProvider(expected),
        source_schema=load_json(ROOT / "schemas/source_document.schema.json"),
        enrollment_schema=load_json(
            ROOT / "schemas/enrollment_candidates.schema.json"
        ),
        twin_schema=load_json(ROOT / "schemas/digital_career_twin.schema.json"),
        tag_catalog=load_json(ROOT / "catalogs/tag_catalog.json"),
    )
    input_path = tmp_path / "synthetic.pdf"
    input_path.write_bytes(b"synthetic")

    result = agent.run(source_type="cv", path=input_path)
    assert result.source_document["source_id"] == "src_synthetic_cv"
    assert result.candidate_twin == expected
    assert result.enrollment_document["candidates"][0]["verification_status"] == "unverified"
    assert "alex@example.com" not in repr(result)
