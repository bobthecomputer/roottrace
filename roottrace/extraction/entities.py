from __future__ import annotations

import re
from collections.abc import Callable, Iterable
from dataclasses import dataclass


@dataclass(slots=True)
class EntityMatch:
    """Representation of an extracted entity."""

    kind: str
    value: str
    normalized: str | None = None
    context: str | None = None
    score: float | None = None


_EMAIL_RE = re.compile(r"\b[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[A-Za-z]{2,}\b")
_DOMAIN_RE = re.compile(r"\b(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+[a-z]{2,}\b", re.IGNORECASE)
_PHONE_RE = re.compile(
    r"(?:\+?\d{1,3}[\s.-]?)?(?:\(\d{2,3}\)[\s.-]?)?\d{2,4}[\s.-]?\d{2,4}[\s.-]?\d{2,4}"
)
_AMOUNT_PREFIX_RE = re.compile(
    r"(?P<currency>€|\$|eur|usd)\s?(?P<value>\d{1,3}(?:[\s.,]\d{3})*(?:[.,]\d{2})?)",
    re.IGNORECASE,
)
_AMOUNT_SUFFIX_RE = re.compile(
    r"(?P<value>\d{1,3}(?:[\s.,]\d{3})*(?:[.,]\d{2})?)\s?(?P<currency>€|\$|eur|usd)",
    re.IGNORECASE,
)
_PAY_HINTS = [
    "bulletin de salaire",
    "net a payer",
    "net à payer",
    "salaire brut",
    "retenues",
    "cotisation",
]


def extract_entities(text: str) -> list[EntityMatch]:
    """Extract structured entities from the provided text."""

    entities: list[EntityMatch] = []
    entities.extend(_emit_matches("email", _EMAIL_RE.findall(text), normalizer=str.lower))

    domains = set(_DOMAIN_RE.findall(text))
    for domain in domains:
        entities.append(EntityMatch(kind="domain", value=domain, normalized=domain.lower()))

    for phone in _PHONE_RE.findall(text):
        cleaned = re.sub(r"[^\d+]", "", phone)
        if len(cleaned) < 7:
            continue
        entities.append(EntityMatch(kind="phone", value=phone, normalized=cleaned))

    for match in list(_AMOUNT_PREFIX_RE.finditer(text)) + list(_AMOUNT_SUFFIX_RE.finditer(text)):
        currency = match.group("currency").upper().replace("€", "EUR").replace("$", "USD")
        raw_value = match.group("value")
        normalized = raw_value.replace(" ", "").replace(".", "").replace(",", ".")
        entities.append(
            EntityMatch(
                kind="amount",
                value=match.group(0),
                normalized=f"{currency} {normalized}",
            )
        )

    lowered = text.lower()
    for hint in _PAY_HINTS:
        if hint in lowered:
            entities.append(EntityMatch(kind="pay_hint", value=hint))

    return entities


def _emit_matches(
    kind: str,
    values: Iterable[str],
    normalizer: Callable[[str], str] | None = None,
) -> list[EntityMatch]:
    results: list[EntityMatch] = []
    seen: set[str] = set()
    for value in values:
        normalized = normalizer(value) if normalizer else value
        if normalized in seen:
            continue
        seen.add(normalized)
        results.append(EntityMatch(kind=kind, value=value, normalized=normalized))
    return results


__all__ = ["EntityMatch", "extract_entities"]
