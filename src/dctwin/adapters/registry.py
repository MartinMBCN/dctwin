from __future__ import annotations

from pathlib import Path

from dctwin.adapters.base import AdaptedSource, SourceAdapterStrategy


class AdapterRegistry:
    def __init__(self) -> None:
        self._strategies: dict[str, list[SourceAdapterStrategy]] = {}

    def register(self, strategy: SourceAdapterStrategy) -> None:
        strategies = self._strategies.setdefault(strategy.source_type, [])
        if any(type(existing) is type(strategy) for existing in strategies):
            raise ValueError(
                f"Adapter {type(strategy).__name__!r} already registered for "
                f"{strategy.source_type!r}"
            )
        strategies.append(strategy)

    def adapt(self, source_type: str, path: Path) -> AdaptedSource:
        try:
            strategies = self._strategies[source_type]
        except KeyError as exc:
            supported = ", ".join(sorted(self._strategies)) or "none"
            raise ValueError(
                f"No adapter for source type {source_type!r}; supported: {supported}"
            ) from exc
        for strategy in strategies:
            if strategy.supports(path):
                return strategy.adapt(path)
        formats = ", ".join(type(strategy).__name__ for strategy in strategies)
        raise ValueError(
            f"{path.name!r} is not supported for {source_type!r}; "
            f"registered strategies: {formats}"
        )

    @property
    def source_types(self) -> tuple[str, ...]:
        return tuple(sorted(self._strategies))
