from datetime import date, datetime
import json

import pytest

from arancel_mx.pipeline.build import materialize_arancel
from arancel_mx.storage.duckdb import connect, init_tariff_db


def release_metadata():
    return {
        "registry_version": "test-registry-v1",
        "registry_sha256": "b" * 64,
        "git_commit_sha": "local",
        "github_run_id": "local",
        "github_run_attempt": "local",
        "github_workflow_ref": "local",
        "github_artifact_name": "local",
        "reconciliation": {
            "publishable": True,
            "error_codes": [],
            "discrepancies": [],
            "legal_document_ids": ["doc-1"],
            "proposal_document_ids": [],
            "indicator_document_ids": [],
        },
        "source_identity": [
            {
                "dataset_key": "ligie",
                "document_role": "ligie_snapshot",
                "source_url": "https://www.diputados.gob.mx/ligie.pdf",
                "sha256": "a" * 64,
                "registry_version": "test-registry-v1",
            }
        ],
    }


def test_build_materializes_a_valid_public_record(tmp_path):
    path = init_tariff_db(tmp_path / "arancel.duckdb")
    source = {
        "source_document_id": "doc-1",
        "authority": "Cámara de Diputados",
        "publication_venue": "DOF",
        "title": "LIGIE",
        "source_url": "https://www.diputados.gob.mx/ligie.pdf",
        "sha256": "a" * 64,
        "observed_at": date(2026, 8, 9),
        "retrieved_at": datetime(2026, 8, 9, 12, 0),
    }
    classification = {
        "level": "hs2",
        "code": "01",
        "description": "Animales vivos.",
        "ligie_version": "LIGIE-2022",
        "validity_basis": "observed_snapshot",
        "updated_at": date(2026, 8, 9),
        "source_document_id": "doc-1",
    }
    release = {
        "dataset_version": "2026.08.09",
        "schema_version": "2",
        "ligie_version": "LIGIE-2022",
        "effective_as_of": date(2026, 8, 9),
        "generated_at": datetime(2026, 8, 9, 12, 0),
        "release_metadata": release_metadata(),
    }

    with connect(path) as connection:
        summary = materialize_arancel(connection, [source], [classification], [], release)
        row = connection.execute(
            "SELECT code, level, is_current FROM arancel_mx"
        ).fetchone()
        stored_metadata = json.loads(
            connection.execute(
                "SELECT release_metadata_json FROM dataset_release"
            ).fetchone()[0]
        )
        stored_sources = json.loads(
            connection.execute(
                "SELECT source_documents_json FROM dataset_release"
            ).fetchone()[0]
        )

    assert summary["row_count"] == 1
    assert row == ("01", "hs2", True)
    assert stored_metadata["registry_version"] == "test-registry-v1"
    assert stored_metadata["registry_sha256"] == "b" * 64
    assert stored_metadata["level_counts"] == {
        "hs2": 1,
        "hs4": 0,
        "hs6": 0,
        "fraccion8": 0,
        "nico10": 0,
    }
    assert stored_metadata["reconciliation"]["publishable"] is True
    assert stored_metadata["source_identity"][0]["dataset_key"] == "ligie"
    assert stored_sources[0]["source_document_id"] == "doc-1"
    assert stored_sources[0]["source_url"] == source["source_url"]
    assert "local_path" not in stored_sources[0]


def test_build_materializes_national_notes_into_the_public_view(tmp_path):
    path = init_tariff_db(tmp_path / "arancel.duckdb")
    source = {
        "source_document_id": "doc-1",
        "authority": "Cámara de Diputados",
        "publication_venue": "DOF",
        "title": "LIGIE",
        "source_url": "https://www.diputados.gob.mx/ligie.pdf",
        "sha256": "a" * 64,
        "observed_at": date(2026, 8, 9),
        "retrieved_at": datetime(2026, 8, 9, 12, 0),
    }
    classification = {
        "level": "hs2",
        "code": "01",
        "description": "Animales vivos.",
        "ligie_version": "LIGIE-2022",
        "validity_basis": "observed_snapshot",
        "updated_at": date(2026, 8, 9),
        "source_document_id": "doc-1",
    }
    release = {
        "dataset_version": "2026.08.09",
        "schema_version": "2",
        "ligie_version": "LIGIE-2022",
        "effective_as_of": date(2026, 8, 9),
        "generated_at": datetime(2026, 8, 9, 12, 0),
        "release_metadata": release_metadata(),
    }
    notes = [
        {
            "chapter": "01",
            "note_number": "1",
            "text": "Los animales vivos de este capítulo.",
            "source_document_id": "doc-1",
        }
    ]

    with connect(path) as connection:
        materialize_arancel(
            connection, [source], [classification], [], release, national_notes=notes
        )
        row = connection.execute(
            "SELECT chapter, note_number, text FROM arancel_mx_national_notes"
        ).fetchone()
        empty = materialize_arancel(connection, [source], [classification], [], release)
        leftover = connection.execute(
            "SELECT COUNT(*) FROM arancel_mx_national_notes"
        ).fetchone()[0]

    assert row == ("01", "1", "Los animales vivos de este capítulo.")
    assert leftover == 0
    assert empty["row_count"] == 1

    path = init_tariff_db(tmp_path / "arancel.duckdb")
    release = {
        "dataset_version": "2026.08.09",
        "schema_version": "2",
        "ligie_version": "LIGIE-2022",
        "effective_as_of": date(2026, 8, 9),
        "generated_at": datetime(2026, 8, 9, 12, 0),
    }

    with connect(path) as connection:
        with pytest.raises(ValueError, match="release.release_metadata"):
            materialize_arancel(connection, [], [], [], release)


def test_materialize_clears_stale_ancillary_tables(tmp_path):
    path = init_tariff_db(tmp_path / "arancel.duckdb")
    source = {
        "source_document_id": "doc-1",
        "authority": "Cámara de Diputados",
        "publication_venue": "DOF",
        "title": "LIGIE",
        "source_url": "https://www.diputados.gob.mx/ligie.pdf",
        "sha256": "a" * 64,
        "observed_at": date(2026, 8, 9),
        "retrieved_at": datetime(2026, 8, 9, 12, 0),
    }
    classification = {
        "level": "hs2",
        "code": "01",
        "description": "Animales vivos.",
        "ligie_version": "LIGIE-2022",
        "validity_basis": "observed_snapshot",
        "updated_at": date(2026, 8, 9),
        "source_document_id": "doc-1",
    }
    release = {
        "dataset_version": "2026.08.09",
        "schema_version": "2",
        "ligie_version": "LIGIE-2022",
        "effective_as_of": date(2026, 8, 9),
        "generated_at": datetime(2026, 8, 9, 12, 0),
        "release_metadata": release_metadata(),
    }

    with connect(path) as connection:
        connection.execute(
            """
            INSERT INTO nico_proposal_batch VALUES (?, ?, ?, ?, ?)
            """,
            ["batch-old", date(2025, 1, 1), None, "doc-old", "c" * 64],
        )
        connection.execute(
            """
            INSERT INTO nico_proposal VALUES (?, ?, ?, ?, ?, ?, 'proposal')
            """,
            ["proposal-old", "batch-old", "0101210199", "01012101", "add", "stale"],
        )
        materialize_arancel(connection, [source], [classification], [], release)
        leftover = connection.execute("SELECT COUNT(*) FROM nico_proposal").fetchone()[0]

    assert leftover == 0


def test_materialize_rejects_multiple_current_rows_for_the_same_code(tmp_path):
    path = init_tariff_db(tmp_path / "arancel.duckdb")
    source = {
        "source_document_id": "doc-1",
        "authority": "SNICE",
        "publication_venue": "SNICE",
        "title": "LIGIE",
        "source_url": "https://www.snice.gob.mx/ligie.xlsx",
        "sha256": "a" * 64,
        "observed_at": date(2026, 8, 9),
        "retrieved_at": datetime(2026, 8, 9, 12, 0),
    }
    classifications = [
        {
            "level": level,
            "code": code,
            "description": "Reproductores de raza pura.",
            "ligie_version": "LIGIE-2022",
            "validity_basis": "observed_snapshot",
            "updated_at": date(2026, 8, 9),
            "source_document_id": "doc-1",
        }
        for level, code in (
            ("hs2", "01"),
            ("hs4", "0101"),
            ("hs6", "010121"),
            ("fraccion8", "01012101"),
        )
    ]
    rates = [
        {
            "code": "01012101",
            "igi_text": "10",
            "igi_kind": "ad_valorem",
            "igi_value": 10,
            "ige_text": "Ex.",
            "ige_kind": "exento",
            "ige_value": 0,
            "ligie_version": "LIGIE-2022",
            "updated_at": date(2026, 8, 9),
            "source_document_id": "doc-1",
        },
        {
            "code": "01012101",
            "igi_text": "5",
            "igi_kind": "ad_valorem",
            "igi_value": 5,
            "ige_text": "Ex.",
            "ige_kind": "exento",
            "ige_value": 0,
            "ligie_version": "LIGIE-2022",
            "updated_at": date(2026, 8, 8),
            "source_document_id": "doc-1",
        },
    ]
    release = {
        "dataset_version": "2026.08.09",
        "schema_version": "2",
        "ligie_version": "LIGIE-2022",
        "effective_as_of": date(2026, 8, 9),
        "generated_at": datetime(2026, 8, 9, 12, 0),
        "release_metadata": release_metadata(),
    }

    with connect(path) as connection:
        with pytest.raises(ValueError, match="duplicate_current_records"):
            materialize_arancel(connection, [source], classifications, rates, release)
