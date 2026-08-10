from datetime import date
from decimal import Decimal

from arancel_mx.domain.normalization import consolidate_records


RELEASE = {
    "dataset_version": "2026.08.09",
    "schema_version": "1.0.0",
    "effective_as_of": date(2026, 8, 9),
}


def test_nico_requires_a_contemporaneous_parent_fraction():
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

    assert consolidate_records([classification], [rate], RELEASE) == []


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
