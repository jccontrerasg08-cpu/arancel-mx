"""Public lookup surface for AduanaMap classifier validation (8+2 identity)."""

from __future__ import annotations

from pathlib import Path

import duckdb
import pytest

from arancel_mx.consumer.dataset import Dataset
from arancel_mx.consumer.errors import QueryError, RecordNotFoundError
from arancel_mx.consumer.models import TariffRecord
from arancel_mx.consumer.query import lookup, parent


def _blank(value: str | None) -> bool:
    return value is None or value == ""


def test_tariff_record_documents_fraction_and_classification_wire_aliases() -> None:
    doc = TariffRecord.__doc__
    assert doc is not None
    assert "fraction8" in doc
    assert "fraccion8" in doc
    assert "classification10" in doc
    assert "nico10" in doc
    assert "fraccion8" in doc and "nico2" in doc


def test_lookup_fraccion8_exposes_hierarchy_identity_and_validity(
    consumer_duckdb: Path,
) -> None:
    record = Dataset.open(consumer_duckdb).lookup("01012101")

    assert record.level == "fraccion8"
    assert record.code == "01012101"
    assert record.hs2 == "01"
    assert record.hs4 == "0101"
    assert record.hs6 == "010121"
    assert record.fraccion8 == "01012101"
    assert _blank(record.nico2)
    assert _blank(record.nico10)
    assert isinstance(record.ligie_version, str) and record.ligie_version
    assert record.ligie_version == "LIGIE-2022"
    assert record.validity_basis == "legal"


def test_lookup_nico10_is_eight_plus_two_not_a_ten_digit_fraction(
    consumer_duckdb: Path,
) -> None:
    record = Dataset.open(consumer_duckdb).lookup("0101210100")

    assert record.level == "nico10"
    assert record.level != "fraccion8"
    assert record.code == "0101210100"
    assert record.fraccion8 == "01012101"
    assert record.nico2 == "00"
    assert record.nico10 == "0101210100"
    assert record.hs2 == "01"
    assert record.hs4 == "0101"
    assert record.hs6 == "010121"
    assert isinstance(record.ligie_version, str) and record.ligie_version
    assert record.validity_basis == "legal"


def test_lookup_missing_code_fail_closes(consumer_duckdb: Path) -> None:
    with pytest.raises(RecordNotFoundError, match="99999999"):
        Dataset.open(consumer_duckdb).lookup("99999999")


def test_lookup_duplicate_current_rows_fail_closes(consumer_duckdb: Path) -> None:
    conn = duckdb.connect(str(consumer_duckdb))
    try:
        conn.execute(
            """
            INSERT INTO canonical_record (
                record_id, record_version, is_current, code, formatted_code, level,
                hs2, hs4, hs6, fraccion8, nico2, nico10, name, description,
                name_is_derived, unit_code, unit_name, values_from_level,
                igi_text, igi_kind, igi_value, ige_text, ige_kind, ige_value,
                ligie_version, dataset_version, schema_version, record_hash,
                validity_basis, updated_at, published_at,
                classification_effective_from, classification_effective_to,
                rate_effective_from, rate_effective_to, effective_from, effective_to,
                observed_at, retrieved_at, primary_source_document_id
            )
            SELECT
                'r-frac-dup', record_version, is_current, code, formatted_code, level,
                hs2, hs4, hs6, fraccion8, nico2, nico10, name, description,
                name_is_derived, unit_code, unit_name, values_from_level,
                igi_text, igi_kind, igi_value, ige_text, ige_kind, ige_value,
                ligie_version, dataset_version, schema_version, 'd' || substr(record_hash, 2),
                validity_basis, updated_at, published_at,
                classification_effective_from, classification_effective_to,
                rate_effective_from, rate_effective_to, effective_from, effective_to,
                observed_at, retrieved_at, primary_source_document_id
            FROM canonical_record
            WHERE record_id = 'r-frac'
            """
        )
        conn.execute(
            """
            INSERT INTO record_provenance
                (record_id, source_document_id, role, is_primary)
            VALUES ('r-frac-dup', 'fixture-source', 'base', TRUE)
            """
        )
    finally:
        conn.close()

    conn = duckdb.connect(str(consumer_duckdb), read_only=True)
    try:
        with pytest.raises(QueryError, match="multiple current records"):
            lookup(conn, "01012101")
    finally:
        conn.close()


def test_parent_children_and_ficha_ancestors_carry_validator_fields(
    consumer_duckdb: Path,
) -> None:
    dataset = Dataset.open(consumer_duckdb)

    ancestor = dataset.parent("0101210100")
    assert ancestor is not None
    assert ancestor.code == "01012101"
    assert ancestor.level == "fraccion8"
    assert ancestor.fraccion8 == "01012101"
    assert ancestor.hs2 == "01"
    assert ancestor.ligie_version == "LIGIE-2022"
    assert ancestor.validity_basis == "legal"

    kids = dataset.children("01012101")
    assert len(kids) == 1
    assert kids[0].level == "nico10"
    assert kids[0].fraccion8 == "01012101"
    assert kids[0].nico2 == "00"
    assert kids[0].nico10 == "0101210100"

    card = dataset.ficha("0101210100")
    assert tuple(node.code for node in card.hierarchy) == (
        "01",
        "0101",
        "010121",
        "01012101",
        "0101210100",
    )
    chapter, heading, subheading, fraction, nico = card.hierarchy
    assert chapter.hs2 == "01"
    assert heading.hs4 == "0101"
    assert subheading.hs6 == "010121"
    assert fraction.fraccion8 == "01012101"
    assert _blank(fraction.nico2)
    assert nico.nico10 == "0101210100"
    assert nico.nico2 == "00"
    assert nico.fraccion8 == "01012101"
    assert all(node.ligie_version == "LIGIE-2022" for node in card.hierarchy)
    assert all(node.validity_basis == "legal" for node in card.hierarchy)


def test_parent_of_chapter_still_returns_none(consumer_duckdb: Path) -> None:
    conn = duckdb.connect(str(consumer_duckdb), read_only=True)
    try:
        assert parent(conn, "01") is None
    finally:
        conn.close()
