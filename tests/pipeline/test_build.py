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


def test_build_rejects_missing_release_metadata_before_transaction(tmp_path):
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
