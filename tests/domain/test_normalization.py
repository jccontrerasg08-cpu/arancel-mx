from datetime import date
from decimal import Decimal

import pytest

from arancel_mx.domain.normalization import (
    code_level,
    derive_name,
    format_code,
    normalize_code,
    parse_duty,
    semantic_record_hash,
)


def test_codes_are_validated_without_silent_padding():
    assert normalize_code("0101.21.01") == "01012101"
    assert normalize_code(0, component_width=2) == "00"
    assert code_level("0101210100") == "nico10"
    assert format_code("0101210100") == "0101.21.01 00"

    with pytest.raises(ValueError):
        normalize_code("1012101")
    with pytest.raises(ValueError):
        normalize_code(10121)


def test_name_uses_first_boundary_and_unicode_limit():
    assert derive_name("Caballos reproductores; los demás.") == "Caballos reproductores"
    derived = derive_name("Árbol " * 30)
    assert len(derived) <= 120
    assert derived.startswith("Árbol")
    assert not derived.endswith(" ")


@pytest.mark.parametrize(
    ("literal", "expected"),
    [
        ("10%", ("ad_valorem", Decimal("10"), "10%")),
        ("Ex.", ("exento", Decimal("0"), "Ex.")),
        ("Prohibida", ("prohibida", None, "Prohibida")),
        ("0.36 USD/Kg", ("especifica", None, "0.36 USD/Kg")),
        ("10% + 0.36 USD/Kg", ("compuesta", None, "10% + 0.36 USD/Kg")),
        ("según decreto", ("desconocida", None, "según decreto")),
        (None, (None, None, None)),
    ],
)
def test_duty_preserves_the_official_literal(literal, expected):
    assert parse_duty(literal) == expected


def test_semantic_hash_ignores_release_transport_metadata():
    row = {
        "level": "fraccion8",
        "code": "01012101",
        "description": "Caballos.",
        "igi_value": Decimal("10"),
        "effective_from": date(2022, 12, 12),
        "dataset_version": "2026.08.09",
        "retrieved_at": "2026-08-09T12:00:00Z",
        "primary_source_url": "https://example.test/one",
    }
    changed_transport = {
        **row,
        "dataset_version": "2026.08.10",
        "retrieved_at": "2026-08-10T12:00:00Z",
        "primary_source_url": "https://example.test/two",
    }

    assert semantic_record_hash(row) == semantic_record_hash(changed_transport)
