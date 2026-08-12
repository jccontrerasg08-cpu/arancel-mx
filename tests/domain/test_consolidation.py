from datetime import date
from decimal import Decimal

import pytest

from arancel_mx.domain.normalization import consolidate_records


RELEASE = {
    "dataset_version": "2026.08.09",
    "schema_version": "1.0.0",
    "effective_as_of": date(2026, 8, 9),
}


def test_nico_without_parent_fraction_fails_closed():
    classification = {
        "level": "nico10",
        "code": "0101210100",
        "description": "Reproductores.",
        "ligie_version": "LIGIE-2022",
        "validity_basis": "legal",
        "classification_effective_from": date(2022, 12, 12),
        "classification_effective_to": None,
        "source_document_id": "doc-nico",
    }
    rate = {
        "code": "01012101",
        "igi_text": "10",
        "igi_value": Decimal("10"),
        "ligie_version": "LIGIE-2022",
        "rate_effective_from": date(2022, 12, 12),
        "rate_effective_to": None,
        "source_document_id": "doc-rate",
    }

    with pytest.raises(ValueError, match="no contemporaneous parent fraction"):
        consolidate_records([classification], [rate], RELEASE)


def test_fraction_without_matching_rate_fails_closed():
    classification = {
        "level": "fraccion8",
        "code": "01012101",
        "description": "Reproductores de raza pura.",
        "ligie_version": "LIGIE-2022",
        "validity_basis": "observed_snapshot",
        "classification_effective_from": None,
        "classification_effective_to": None,
        "source_document_id": "doc-fraction",
    }

    with pytest.raises(ValueError, match="no matching tariff rate"):
        consolidate_records([classification], [], RELEASE)


def test_nico_primary_source_is_the_nico_document():
    fraction = {
        "level": "fraccion8",
        "code": "01012101",
        "description": "Reproductores de raza pura.",
        "ligie_version": "LIGIE-2022",
        "validity_basis": "observed_snapshot",
        "classification_effective_from": None,
        "classification_effective_to": None,
        "source_document_id": "doc-fraction",
    }
    nico = {
        "level": "nico10",
        "code": "0101210100",
        "description": "Reproductores.",
        "ligie_version": "LIGIE-2022",
        "validity_basis": "observed_snapshot",
        "classification_effective_from": None,
        "classification_effective_to": None,
        "source_document_id": "doc-nico",
    }
    rate = {
        "code": "01012101",
        "igi_text": "10",
        "igi_kind": "ad_valorem",
        "igi_value": Decimal("10"),
        "ligie_version": "LIGIE-2022",
        "rate_effective_from": None,
        "rate_effective_to": None,
        "source_document_id": "doc-rate",
    }

    rows = consolidate_records([fraction, nico], [rate], RELEASE)
    by_level = {row["level"]: row for row in rows}

    assert by_level["fraccion8"]["primary_source_document_id"] == "doc-rate"
    assert by_level["nico10"]["primary_source_document_id"] == "doc-nico"


def test_observed_snapshot_without_start_date_is_current():
    base = {
        "level": "hs2",
        "code": "01",
        "description": "Animales vivos.",
        "ligie_version": "LIGIE-2022",
        "classification_effective_from": None,
        "classification_effective_to": None,
        "source_document_id": "doc-base",
    }

    legal = consolidate_records([{**base, "validity_basis": "legal"}], [], RELEASE)
    observed = consolidate_records(
        [{**base, "validity_basis": "observed_snapshot"}], [], RELEASE
    )

    assert legal[0]["is_current"] is False
    assert observed[0]["is_current"] is True
