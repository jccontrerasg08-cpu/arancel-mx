from datetime import date, datetime

from arancel_mx.pipeline.build import materialize_arancel
from arancel_mx.storage.duckdb import connect, init_tariff_db


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
        "schema_version": "1.0.0",
        "ligie_version": "LIGIE-2022",
        "effective_as_of": date(2026, 8, 9),
        "generated_at": datetime(2026, 8, 9, 12, 0),
    }

    with connect(path) as connection:
        summary = materialize_arancel(connection, [source], [classification], [], release)
        row = connection.execute(
            "SELECT code, level, is_current FROM arancel_mx"
        ).fetchone()

    assert summary["row_count"] == 1
    assert row == ("01", "hs2", True)
