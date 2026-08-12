from __future__ import annotations

from datetime import date, datetime
from pathlib import Path
from typing import Iterator

import duckdb
import pytest

from arancel_mx.storage.duckdb import ensure_tariff_schema


_DATASET_VERSION = "2026.08.11"
_SCHEMA_VERSION = "2"
_SOURCE_ID = "fixture-source"


_RECORDS = (
    ("r-hs2", "01", "hs2", "01", None, None, None, None, None, "Animales vivos"),
    ("r-hs4", "0101", "hs4", "01", "0101", None, None, None, None, "Caballos, asnos, mulos y burdéganos, vivos"),
    ("r-hs6", "010121", "hs6", "01", "0101", "010121", None, None, None, "Reproductores de raza pura"),
    ("r-frac", "01012101", "fraccion8", "01", "0101", "010121", "01012101", None, None, "Reproductores de raza pura"),
    ("r-nico", "0101210100", "nico10", "01", "0101", "010121", "01012101", "00", "0101210100", "Reproductores de raza pura"),
)


def create_consumer_duckdb(
    path: Path,
    *,
    dataset_version: str = _DATASET_VERSION,
    schema_version: str = _SCHEMA_VERSION,
    validation_status: str = "passed",
    include_view: bool = True,
    include_release: bool = True,
) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    conn = duckdb.connect(str(path))
    try:
        ensure_tariff_schema(conn)
        conn.execute(
            """
            INSERT INTO source_document (
                source_document_id, authority, publication_venue, title, source_url,
                media_type, sha256, local_path, published_at, effective_from,
                effective_to, observed_at, retrieved_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            [
                _SOURCE_ID,
                "SNICE",
                "SNICE",
                "Fixture LIGIE",
                "https://example.invalid/fixture",
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                "f" * 64,
                None,
                date(2026, 4, 20),
                date(2026, 4, 20),
                None,
                date(2026, 8, 11),
                datetime(2026, 8, 11, 12, 0, 0),
            ],
        )

        for index, (
            record_id,
            code,
            level,
            hs2,
            hs4,
            hs6,
            fraccion8,
            nico2,
            nico10,
            description,
        ) in enumerate(_RECORDS, start=1):
            unit_code = "01" if level in {"fraccion8", "nico10"} else None
            unit_name = "Cbza" if level in {"fraccion8", "nico10"} else None
            values_from_level = "fraccion8" if level in {"fraccion8", "nico10"} else None
            igi_text = "10" if level in {"fraccion8", "nico10"} else None
            igi_kind = "ad_valorem" if level in {"fraccion8", "nico10"} else None
            igi_value = 10.0 if level in {"fraccion8", "nico10"} else None
            ige_text = "Ex." if level in {"fraccion8", "nico10"} else None
            ige_kind = "exento" if level in {"fraccion8", "nico10"} else None
            ige_value = 0.0 if level in {"fraccion8", "nico10"} else None
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
                ) VALUES (
                    ?, 1, TRUE, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, FALSE,
                    ?, ?, ?, ?, ?, ?, ?, ?, ?,
                    'LIGIE-2022', ?, ?, ?, 'legal', ?, ?, ?, NULL,
                    ?, NULL, ?, NULL, ?, ?, ?
                )
                """,
                [
                    record_id,
                    code,
                    code,
                    level,
                    hs2,
                    hs4,
                    hs6,
                    fraccion8,
                    nico2,
                    nico10,
                    description,
                    description,
                    unit_code,
                    unit_name,
                    values_from_level,
                    igi_text,
                    igi_kind,
                    igi_value,
                    ige_text,
                    ige_kind,
                    ige_value,
                    dataset_version,
                    schema_version,
                    f"{index:064x}",
                    date(2026, 4, 20),
                    date(2026, 4, 20),
                    date(2026, 4, 20),
                    date(2026, 4, 20) if level in {"fraccion8", "nico10"} else None,
                    date(2026, 4, 20),
                    date(2026, 8, 11),
                    datetime(2026, 8, 11, 12, 0, 0),
                    _SOURCE_ID,
                ],
            )
            conn.execute(
                """
                INSERT INTO record_provenance
                    (record_id, source_document_id, role, is_primary)
                VALUES (?, ?, ?, TRUE)
                """,
                [record_id, _SOURCE_ID, "nico" if level == "nico10" else "base"],
            )

        if include_release:
            conn.execute(
                """
                INSERT INTO dataset_release (
                    dataset_version, schema_version, ligie_version, effective_as_of,
                    generated_at, row_count, validation_status, validation_results_json,
                    source_documents_json, release_metadata_json
                ) VALUES (?, ?, 'LIGIE-2022', ?, ?, ?, ?, '{}', '[]', '{}')
                """,
                [
                    dataset_version,
                    schema_version,
                    date(2026, 8, 11),
                    datetime(2026, 8, 11, 12, 0, 0),
                    len(_RECORDS),
                    validation_status,
                ],
            )

        if include_view:
            conn.execute(
                """
                CREATE OR REPLACE VIEW arancel_mx AS
                WITH provenance AS (
                    SELECT record_id,
                           to_json(list(DISTINCT source_document_id ORDER BY source_document_id))::VARCHAR
                               AS source_document_ids_json,
                           count(DISTINCT source_document_id) AS source_count
                    FROM record_provenance
                    GROUP BY record_id
                )
                SELECT c.*, s.authority AS primary_source_authority,
                       s.source_url AS primary_source_url,
                       p.source_document_ids_json, p.source_count
                FROM canonical_record c
                JOIN source_document s
                  ON s.source_document_id = c.primary_source_document_id
                JOIN provenance p ON p.record_id = c.record_id
                """
            )
    finally:
        conn.close()
    return path


@pytest.fixture
def consumer_duckdb(tmp_path: Path) -> Path:
    return create_consumer_duckdb(tmp_path / "fixture.duckdb")
