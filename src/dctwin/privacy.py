from __future__ import annotations

import re
from dataclasses import dataclass, field


@dataclass(frozen=True)
class Redaction:
    category: str
    placeholder: str
    value: str = field(repr=False)


_PATTERNS: tuple[tuple[str, re.Pattern[str]], ...] = (
    (
        "email",
        re.compile(r"\b[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}\b", re.IGNORECASE),
    ),
    (
        "phone",
        re.compile(r"(?<!\w)\+[0-9][0-9 ().-]{7,}[0-9](?!\w)"),
    ),
    (
        "street_address",
        re.compile(
            r"\b[0-9]{1,5}\s+[A-Z][A-Za-zÀ-ÿ' -]{2,40}\s"
            r"(?:Street|St|Road|Rd|Avenue|Ave|Lane|Ln|Calle|Carrer|Passeig)\b",
            re.IGNORECASE,
        ),
    ),
)


def minimize_direct_identifiers(
    text: str,
    *,
    counters: dict[str, int] | None = None,
) -> tuple[str, list[Redaction]]:
    """Replace direct identifiers without retaining their original values."""

    minimized = text
    redactions: list[Redaction] = []
    counters = counters if counters is not None else {}

    for category, pattern in _PATTERNS:
        def replace(match: re.Match[str]) -> str:
            counters[category] = counters.get(category, 0) + 1
            placeholder = f"[{category.upper()}_{counters[category]}]"
            redactions.append(
                Redaction(category=category, placeholder=placeholder, value=match.group(0))
            )
            return placeholder

        minimized = pattern.sub(replace, minimized)

    return minimized, redactions
