from datetime import date, datetime
from decimal import Decimal
import hashlib
import json
from pathlib import Path

import duckdb
import pytest

from arancel_mx.certification.consumer import certify_duckdb
from arancel_mx.pipeline.build import export_arancel_release, materialize_arancel
from arancel_mx.storage.duckdb import connect, init_tariff_db
from scripts.check_duckdb_compat import probe_database


SOURCE_ID = "doc-1"
SOURCE_URL = "https://www.snice.gob.mx/ligie.xlsx"


def _release_metadata() -> dict[str, object]:
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
            "legal_document_ids": [SOURCE_ID],
            "proposal_document_ids": [],
            "indicator_document_ids": [],
        },
        "source_identity": [
            {
                "dataset_key": "ligie",
                "document_role": "ligie_snapshot",
                "source_url": SOURCE_URL,
                "sha256": "a" * 64,
                "registry_version": "test-registry-v1",
            }
        ],
    }


def _classification(level: str, code: str, description: str) -> dict[str, object]:
    return {
        "level": level,
        "code": code,
        "description": description,
        "ligie_version": "LIGIE-2022",
        "validity_basis": "observed_snapshot",
        "updated_at": date(2026, 8, 10),
        "source_document_id": SOURCE_ID,
    }


def _public_release(tmp_path: Path) -> tuple[Path, dict[str, object]]:
    warehouse = init_tariff_db(tmp_path / "warehouse.duckdb")
    source = {
        "source_document_id": SOURCE_ID,
        "authority": "Secretaría de Economía / SNICE",
        "publication_venue": "SNICE",
        "title": "LIGIE",
        "source_url": SOURCE_URL,
        "media_type": "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        "sha256": "a" * 64,
        "observed_at": date(2026, 8, 10),
        "retrieved_at": datetime(2026, 8, 10, 20, 35, 49),
    }
    classifications = [
        _classification("hs2", "01", "Animales vivos"),
        _classification("hs4", "0101", "Caballos, asnos, mulos y burdéganos"),
        _classification("hs6", "010121", "Reproductores de raza pura"),
        _classification("fraccion8", "01012101", "Reproductores de raza pura"),
        _classification("nico10", "0101210100", "Reproductores de raza pura"),
    ]
    rates = [
        {
            "code": "01012101",
            "unit_code": "01",
            "unit_name": "Cabeza",
            "igi_text": "15",
            "igi_kind": "ad_valorem",
            "igi_value": Decimal("15"),
            "ige_text": "Ex.",
            "ige_kind": "exento",
            "ige_value": Decimal("0"),
            "ligie_version": "LIGIE-2022",
            "updated_at": date(2026, 8, 10),
            "source_document_id": SOURCE_ID,
        }
    ]
    release = {
        "dataset_version": "2026.08.10",
        "schema_version": "2",
        "ligie_version": "LIGIE-2022",
        "effective_as_of": date(2026, 8, 10),
        "generated_at": datetime(2026, 8, 10, 20, 35, 47),
        "release_metadata": _release_metadata(),
    }

    with connect(warehouse) as connection:
        summary = materialize_arancel(
            connection,
            [source],
            classifications,
            rates,
            release,
        )
    assert summary["row_count"] == 5

    release_dir = tmp_path / "release"
    export_arancel_release(warehouse, release_dir)
    database = release_dir / "arancel_mx.duckdb"
    manifest = json.loads((release_dir / "manifest.json").read_text(encoding="utf-8"))
    return database, manifest


def _delete_level(database: Path, level: str) -> None:
    with duckdb.connect(str(database)) as connection:
        ids = [
            row[0]
            for row in connection.execute(
                "SELECT record_id FROM canonical_record WHERE level = ?", [level]
            ).fetchall()
        ]
        for record_id in ids:
            connection.execute(
                "DELETE FROM record_provenance WHERE record_id = ?", [record_id]
            )
        connection.execute("DELETE FROM canonical_record WHERE level = ?", [level])


def test_certify_duckdb_accepts_real_exported_public_database(tmp_path: Path):
    database, manifest = _public_release(tmp_path)
    before = hashlib.sha256(database.read_bytes()).hexdigest()

    checks = certify_duckdb(database, manifest)

    assert checks == (
        "core_objects",
        "public_columns",
        "release_metadata",
        "row_count",
        "record_ids",
        "hierarchy",
        "value_origin",
    )
    assert hashlib.sha256(database.read_bytes()).hexdigest() == before


def test_public_database_does_not_require_internal_source_registry(tmp_path: Path):
    database, manifest = _public_release(tmp_path)
    with duckdb.connect(str(database), read_only=True) as connection:
        objects = {row[0] for row in connection.execute("SHOW TABLES").fetchall()}

    assert "source_registry" not in objects
    assert certify_duckdb(database, manifest)


def test_certify_duckdb_rejects_missing_core_table(tmp_path: Path):
    database, manifest = _public_release(tmp_path)
    with duckdb.connect(str(database)) as connection:
        connection.execute("DROP TABLE tariff_rate")

    with pytest.raises(ValueError, match="missing core DuckDB objects"):
        certify_duckdb(database, manifest)


def test_certify_duckdb_rejects_manifest_row_count_mismatch(tmp_path: Path):
    database, manifest = _public_release(tmp_path)
    manifest["row_count"] = 999

    with pytest.raises(ValueError, match="row count"):
        certify_duckdb(database, manifest)


def test_certify_duckdb_rejects_fraction_without_hs6_parent(tmp_path: Path):
    database, manifest = _public_release(tmp_path)
    _delete_level(database, "hs6")
    manifest["row_count"] = 4

    with pytest.raises(ValueError, match="hierarchy"):
        certify_duckdb(database, manifest)


def test_certify_duckdb_rejects_nico_without_fraction_parent(tmp_path: Path):
    database, manifest = _public_release(tmp_path)
    _delete_level(database, "fraccion8")
    manifest["row_count"] = 4

    with pytest.raises(ValueError, match="hierarchy"):
        certify_duckdb(database, manifest)


def test_certify_duckdb_rejects_tariff_values_on_hs_level(tmp_path: Path):
    database, manifest = _public_release(tmp_path)
    with duckdb.connect(str(database)) as connection:
        connection.execute(
            """
            UPDATE canonical_record
            SET values_from_level='fraccion8', igi_text='5',
                igi_kind='ad_valorem', igi_value=5
            WHERE level='hs6'
            """
        )

    with pytest.raises(ValueError, match="value origin"):
        certify_duckdb(database, manifest)


def test_compat_probe_reads_public_view_without_mutation(tmp_path: Path):
    database, _manifest = _public_release(tmp_path)
    before = hashlib.sha256(database.read_bytes()).hexdigest()

    result = probe_database(database, expected_row_count=5)

    assert result["row_count"] == 5
    assert result["duckdb_version"] == duckdb.__version__
    assert result["public_column_count"] > 0
    assert hashlib.sha256(database.read_bytes()).hexdigest() == before
