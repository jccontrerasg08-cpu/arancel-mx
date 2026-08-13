from datetime import date

from arancel_mx.domain.normalization import promote_staging, stage_rows
from arancel_mx.storage.duckdb import connect, init_tariff_db


def _stage(connection, *, role, normalized, staging_row_id="row-1"):
    stage_rows(
        connection,
        [
            {
                "staging_row_id": staging_row_id,
                "capture_id": "capture-1",
                "dataset_key": "ligie",
                "document_role": role,
                "sheet_name": "Datos",
                "source_row_number": 2,
                "parser_version": "test-1",
                "raw": {},
                "normalized": normalized,
            }
        ],
    )


def test_promote_staging_persists_classification_effective_dates(tmp_path):
    path = init_tariff_db(tmp_path / "arancel.duckdb")
    with connect(path) as connection:
        _stage(
            connection,
            role="tariff_fraction",
            normalized={
                "code": "01012101",
                "description": "Reproductores de raza pura.",
                "ligie_version": "LIGIE-2022",
                "validity_basis": "legal",
                "classification_effective_from": date(2022, 12, 12),
                "classification_effective_to": None,
                "source_document_id": "doc-fraction",
            },
        )
        summary = promote_staging(connection)
        stored = connection.execute(
            """
            SELECT classification_effective_from, classification_effective_to
            FROM tariff_fraction
            """
        ).fetchone()
        status = connection.execute(
            "SELECT row_status FROM staging_arancel_row"
        ).fetchone()[0]

    assert summary.tariff_fractions == 1
    assert stored == (date(2022, 12, 12), None)
    assert status == "promoted"


def test_promote_staging_writes_proposals_notes_and_indicators(tmp_path):
    path = init_tariff_db(tmp_path / "arancel.duckdb")
    with connect(path) as connection:
        _stage(
            connection,
            staging_row_id="proposal-1",
            role="nico_proposal",
            normalized={
                "proposed_nico10": "0101210199",
                "action": "add",
                "description": "Propuesta de prueba.",
                "observed_at": date(2026, 8, 10),
                "source_document_id": "doc-proposal",
                "source_sha256": "a" * 64,
            },
        )
        _stage(
            connection,
            staging_row_id="note-1",
            role="national_notes",
            normalized={
                "chapter": "01",
                "note_number": "1",
                "text": "Nota nacional de prueba.",
                "source_document_id": "doc-note",
            },
        )
        _stage(
            connection,
            staging_row_id="indicator-1",
            role="weighted_tariff_indicator",
            normalized={
                "period": date(2025, 12, 1),
                "hs6": "010121",
                "nmf_weighted_rate": "0.12",
                "source_document_id": "doc-indicator",
            },
        )
        summary = promote_staging(connection)
        proposals = connection.execute("SELECT COUNT(*) FROM nico_proposal").fetchone()[0]
        notes = connection.execute("SELECT COUNT(*) FROM national_note_version").fetchone()[0]
        indicators = connection.execute(
            "SELECT COUNT(*) FROM weighted_tariff_indicator"
        ).fetchone()[0]

    assert summary.proposals == 1
    assert summary.national_notes == 1
    assert summary.indicators == 1
    assert (proposals, notes, indicators) == (1, 1, 1)
