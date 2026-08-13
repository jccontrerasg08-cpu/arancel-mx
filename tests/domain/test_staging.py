from datetime import date

import pytest

from arancel_mx.domain.normalization import promote_staging, stage_rows, validate_staging
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


def test_promote_staging_rolls_back_when_a_later_row_fails(tmp_path):
    path = init_tariff_db(tmp_path / "arancel.duckdb")
    with connect(path) as connection:
        _stage(
            connection,
            staging_row_id="a-fraction",
            role="tariff_fraction",
            normalized={
                "code": "01012101",
                "description": "Reproductores de raza pura.",
                "ligie_version": "LIGIE-2022",
                "validity_basis": "legal",
                "classification_effective_from": date(2022, 12, 12),
                "source_document_id": "doc-fraction",
            },
        )
        _stage(
            connection,
            staging_row_id="b-fraction",
            role="tariff_fraction",
            normalized={
                "code": "01012901",
                "description": "Los demás.",
                "ligie_version": "LIGIE-2022",
                "validity_basis": "legal",
                "classification_effective_from": "not-a-date",
                "source_document_id": "doc-fraction-2",
            },
        )
        with pytest.raises(ValueError, match="invalid staging date"):
            promote_staging(connection)
        fractions = connection.execute("SELECT COUNT(*) FROM tariff_fraction").fetchone()[0]
        statuses = {
            row[0]: row[1]
            for row in connection.execute(
                "SELECT staging_row_id, row_status FROM staging_arancel_row"
            ).fetchall()
        }

    assert fractions == 0
    assert statuses["a-fraction"] != "promoted"
    assert statuses["b-fraction"] != "promoted"


def test_validate_staging_quarantines_incomplete_nico_proposal(tmp_path):
    path = init_tariff_db(tmp_path / "arancel.duckdb")
    with connect(path) as connection:
        _stage(
            connection,
            role="nico_proposal",
            normalized={
                "proposed_nico10": "0101210199",
                "action": "add",
                "source_document_id": "doc-proposal",
            },
        )
        report = validate_staging(connection)
        status = connection.execute(
            "SELECT row_status FROM staging_arancel_row"
        ).fetchone()[0]

    assert report.publishable is False
    assert report.quarantined[0].reason_code == "missing_provenance"
    assert status == "quarantined"


def test_validate_staging_quarantines_nico_proposal_that_is_not_10_digits(tmp_path):
    path = init_tariff_db(tmp_path / "arancel.duckdb")
    with connect(path) as connection:
        _stage(
            connection,
            role="nico_proposal",
            normalized={
                "proposed_nico10": "01012101",
                "action": "add",
                "observed_at": date(2026, 8, 10),
                "source_document_id": "doc-proposal",
                "source_sha256": "a" * 64,
            },
        )
        report = validate_staging(connection)

    assert report.publishable is False
    assert report.quarantined[0].reason_code == "ambiguous_code"


def test_validate_staging_quarantines_whitespace_source_document_id(tmp_path):
    path = init_tariff_db(tmp_path / "arancel.duckdb")
    with connect(path) as connection:
        _stage(
            connection,
            role="tariff_fraction",
            normalized={
                "code": "01012101",
                "description": "Reproductores de raza pura.",
                "source_document_id": "   ",
            },
        )
        report = validate_staging(connection)

    assert report.publishable is False
    assert report.quarantined[0].reason_code == "missing_provenance"


def test_validate_staging_quarantines_incomplete_national_note_and_indicator(tmp_path):
    path = init_tariff_db(tmp_path / "arancel.duckdb")
    with connect(path) as connection:
        _stage(
            connection,
            staging_row_id="note-1",
            role="national_notes",
            normalized={"chapter": "01", "note_number": "1", "source_document_id": "doc-note"},
        )
        _stage(
            connection,
            staging_row_id="indicator-1",
            role="weighted_tariff_indicator",
            normalized={
                "period": date(2025, 12, 1),
                "hs6": "10121",
                "source_document_id": "doc-indicator",
            },
        )
        report = validate_staging(connection)
        reasons = {item.staging_row_id: item.reason_code for item in report.quarantined}

    assert report.publishable is False
    assert reasons["note-1"] == "missing_note_text"
    assert reasons["indicator-1"] == "ambiguous_code"
