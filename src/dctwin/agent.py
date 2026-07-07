from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from dctwin.adapters.base import AdaptedSource
from dctwin.adapters.registry import AdapterRegistry
from dctwin.providers import TwinProvider
from dctwin.validation import (
    ContractValidationError,
    validate_enrollment_document,
    validate_source_document,
    validate_twin,
)


@dataclass(frozen=True)
class SourceAdapterRun:
    source_document: dict[str, Any]
    candidate_twin: dict[str, Any]
    enrollment_document: dict[str, Any] = field(repr=False)


class SourceAdapterAgent:
    """Orchestrates source normalization, semantic adaptation and acceptance."""

    def __init__(
        self,
        *,
        registry: AdapterRegistry,
        provider: TwinProvider,
        source_schema: dict[str, Any],
        enrollment_schema: dict[str, Any],
        twin_schema: dict[str, Any],
        tag_catalog: dict[str, Any],
    ) -> None:
        self._registry = registry
        self._provider = provider
        self._source_schema = source_schema
        self._enrollment_schema = enrollment_schema
        self._twin_schema = twin_schema
        self._tag_catalog = tag_catalog

    def run(self, *, source_type: str, path: Path) -> SourceAdapterRun:
        adapted = self._registry.adapt(source_type, path)
        return self.run_adapted(adapted)

    def run_adapted(self, adapted: AdaptedSource) -> SourceAdapterRun:
        source_document = adapted.model_document
        validate_source_document(source_document, self._source_schema)
        validate_enrollment_document(
            adapted.enrollment_document, self._enrollment_schema
        )
        candidate = self._provider.generate(
            source_document=source_document,
            twin_schema=self._twin_schema,
            tag_catalog=self._tag_catalog,
        )
        for repair_attempt in range(3):
            try:
                validate_twin(
                    candidate,
                    self._twin_schema,
                    self._tag_catalog,
                    source_documents=[source_document],
                )
                break
            except ContractValidationError as error:
                repair = getattr(self._provider, "repair", None)
                if repair_attempt >= 2 or not callable(repair):
                    raise
                candidate = repair(
                    candidate=candidate,
                    validation_issues=error.issues,
                    source_document=source_document,
                    twin_schema=self._twin_schema,
                    tag_catalog=self._tag_catalog,
                )
        return SourceAdapterRun(
            source_document=source_document,
            candidate_twin=candidate,
            enrollment_document=adapted.enrollment_document,
        )
