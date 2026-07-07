from __future__ import annotations

from copy import deepcopy
from typing import Any, Protocol


class TwinProvider(Protocol):
    """Model-facing boundary used by the Source Adapter Agent."""

    def generate(
        self,
        *,
        source_document: dict[str, Any],
        twin_schema: dict[str, Any],
        tag_catalog: dict[str, Any],
    ) -> dict[str, Any]: ...


class StaticTwinProvider:
    """Deterministic local provider for tests and quota-free development."""

    def __init__(self, response: dict[str, Any]) -> None:
        self._response = response

    def generate(
        self,
        *,
        source_document: dict[str, Any],
        twin_schema: dict[str, Any],
        tag_catalog: dict[str, Any],
    ) -> dict[str, Any]:
        del source_document, twin_schema, tag_catalog
        return deepcopy(self._response)
