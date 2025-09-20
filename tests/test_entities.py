from __future__ import annotations

from roottrace.extraction.entities import extract_entities


def test_extract_entities_detects_multiple_types() -> None:
    text = (
        "Contact: Investigateur@example.com ou au +33 6 12 34 56 78. "
        "Montant dû: 1 234,56 € sur bulletin de salaire ACME. "
        "Site: https://www.example.com"
    )

    entities = extract_entities(text)
    kinds = {entity.kind for entity in entities}

    assert {"email", "phone", "amount", "pay_hint", "domain"}.issubset(kinds)
    email = next(entity for entity in entities if entity.kind == "email")
    assert email.normalized == "investigateur@example.com"
    amount = next(entity for entity in entities if entity.kind == "amount")
    assert amount.normalized == "EUR 1234.56"
