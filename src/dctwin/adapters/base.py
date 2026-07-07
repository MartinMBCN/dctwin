from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Protocol


@dataclass(frozen=True)
class AdaptedSource:
    """Separated model input and private enrollment output from one source."""

    model_document: dict[str, Any]
    enrollment_document: dict[str, Any] = field(repr=False)


class SourceAdapterStrategy(Protocol):
    """A source-specific reader that emits the normalized source contract."""

    source_type: str

    def supports(self, path: Path) -> bool: ...

    def adapt(self, path: Path) -> AdaptedSource: ...
