from __future__ import annotations

import json
from pathlib import Path

import duckdb
import pytest

from arancel_mx.cli import build_parser, main
from arancel_mx.consumer.release_diff import EVENTS, auxiliary_rows, diff_auxiliary, diff_rows, release_diff_report
from tests.consumer.conftest import create_consumer_duckdb


def _row(code: str, level: str = "fraccion8", **values: object) -> dict[str, object]:
    base: dict[str, object] = {
        "code": code,
        "level": level,
        "description": "Caballos",
        "igi_text": "10",
        "ige_text": "Ex.",
        "unit_code": "01",
        "parent": code[:6],
    }
    base.update(values)
    return base


def _rows(*rows: dict[str, object]) -> dict[str, dict[str, object]]:
    return {str(row["code"]): row for row in rows}


def test_identical_releases_have_no_changes() -> None:
    rows = _rows(_row("01012101"), _row("0101210100", level="nico10", parent="01012101"))
    assert diff_rows(rows, dict(rows)) == ()


def test_added_and_removed_codes_carry_the_description() -> None:
    before = _rows(_row("01012101", description="Reproductores"))
    after = _rows(_row("01012199", description="Los demás"))
    changes = diff_rows(before, after)
    assert [(c["code"], c["event"], c["old_value"], c["new_value"]) for c in changes] == [
        ("01012101", "row_removed", "Reproductores", None),
        ("01012199", "row_added", None, "Los demás"),
    ]


def test_one_code_can_change_several_fields_and_each_is_reported() -> None:
    before = _rows(_row("98030001", igi_text="10", ige_text="10"))
    after = _rows(_row("98030001", igi_text="Ex.", ige_text="Ex."))
    events = [c["event"] for c in diff_rows(before, after)]
    assert events == ["igi_changed", "ige_changed"]


def test_accents_are_compared_literally_and_never_normalized() -> None:
    before = _rows(_row("39079908", description="contenido de solidos"))
    after = _rows(_row("39079908", description="contenido de sólidos"))
    (change,) = diff_rows(before, after)
    assert change["event"] == "description_changed"
    assert (change["old_value"], change["new_value"]) == ("contenido de solidos", "contenido de sólidos")


def test_a_value_that_becomes_unknown_is_a_change_not_a_zero() -> None:
    (change,) = diff_rows(_rows(_row("01012101", igi_text="10")), _rows(_row("01012101", igi_text=None)))
    assert (change["event"], change["old_value"], change["new_value"]) == ("igi_changed", "10", None)


def test_moving_a_code_under_another_parent_is_a_hierarchy_change() -> None:
    before = _rows(_row("0101210100", level="nico10", parent="01012101"))
    after = _rows(_row("0101210100", level="nico10", parent="01012199"))
    assert [c["event"] for c in diff_rows(before, after)] == ["hierarchy_changed"]


def test_level_filter_and_unknown_level() -> None:
    before = _rows(_row("01012101"), _row("0101210100", level="nico10"))
    after = _rows(_row("01012101", igi_text="5"), _row("0101210100", level="nico10", igi_text="5"))
    assert [c["code"] for c in diff_rows(before, after, levels=["nico10"])] == ["0101210100"]
    with pytest.raises(ValueError, match="unknown level"):
        diff_rows(before, after, levels=["capitulo"])


def test_a_code_that_changes_level_is_refused_instead_of_guessed() -> None:
    with pytest.raises(ValueError, match="changed level"):
        diff_rows(_rows(_row("0101")), _rows(_row("0101", level="hs4")))


def test_report_counts_every_event_and_only_calls_verified_pairs_verified() -> None:
    before = _rows(_row("01012101"))
    after = _rows(_row("01012101", igi_text="5"), _row("01012199"))
    verified = {"dataset_version": "2026.11.20", "release_verified": True, "github_digest_state": "verified"}
    local = {"dataset_version": "2026.11.16", "release_verified": False, "github_digest_state": "not_applicable"}
    report = release_diff_report(before, after, from_info=verified, to_info=verified)
    assert report["comparison_status"] == "verified_snapshots"
    assert set(report["counts"]["by_event"]) == set(EVENTS)
    assert report["counts"]["by_event"]["igi_changed"] == 1
    assert report["counts"]["by_event"]["row_added"] == 1
    assert report["counts"]["changes"] == 2
    assert "not legal events" in str(report["note"])
    mixed = release_diff_report(before, after, from_info=local, to_info=verified)
    assert mixed["comparison_status"] == "unverified_local_files"


def test_parser_accepts_two_releases_levels_and_format() -> None:
    namespace = build_parser().parse_args(
        ["data", "diff", "--from", "data-2026.08.15", "--to", "data-2026.11.20", "--level", "fraccion8", "--level", "nico10", "--offline", "--format", "json"]
    )
    assert namespace.consumer_action == "data_diff"
    assert (namespace.from_dataset, namespace.to_dataset) == ("data-2026.08.15", "data-2026.11.20")
    assert namespace.level == ["fraccion8", "nico10"]
    assert namespace.offline is True


def test_cli_compares_two_local_files_end_to_end(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    before = create_consumer_duckdb(tmp_path / "before.duckdb", dataset_version="2026.08.11")
    after = create_consumer_duckdb(tmp_path / "after.duckdb", dataset_version="2026.08.12")
    with duckdb.connect(str(after)) as conn:
        conn.execute("UPDATE canonical_record SET igi_text = '15' WHERE code = '01012101'")
    assert main(["data", "diff", "--from", str(before), "--to", str(after), "--format", "json"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["from"]["dataset_version"] == "2026.08.11"
    assert report["to"]["dataset_version"] == "2026.08.12"
    assert report["comparison_status"] == "unverified_local_files"
    assert [(c["code"], c["event"], c["old_value"], c["new_value"]) for c in report["changes"]] == [
        ("01012101", "igi_changed", "10", "15")
    ]

    assert main(["data", "diff", "--from", str(before), "--to", str(after), "--format", "csv"]) == 0
    lines = capsys.readouterr().out.splitlines()
    assert lines[0] == "code,event,level,new_value,old_value"
    assert lines[1] == "01012101,igi_changed,fraccion8,15,10"



def test_nom_rows_report_additions_removals_and_literal_scope_changes() -> None:
    before = {("85171301", "1", "NOM-208-SCFI-2016"): "Únicamente: radio", ("85171301", "3", "NOM-024-SCFI-2013"): None}
    after = {("85171301", "1", "NOM-208-SCFI-2016"): "Únicamente: radiocomunicación", ("85171302", "3", "NOM-024-SCFI-2013"): None}
    report = diff_auxiliary("nom", before, after)
    assert report["status"] == "compared"
    assert [(c["fraction8"], c["event"]) for c in report["changes"]] == [
        ("85171301", "nom_scope_changed"),
        ("85171301", "nom_removed"),
        ("85171302", "nom_added"),
    ]
    assert report["by_event"] == {"nom_added": 1, "nom_removed": 1, "nom_scope_changed": 1}


def test_an_auxiliary_table_missing_on_one_side_is_not_compared_rather_than_all_added() -> None:
    after = {("85171301", "1", "NOM-208-SCFI-2016"): None}
    report = diff_auxiliary("nom", "view not present", after)
    assert report == {"status": "not_compared", "reason": "from: view not present", "changes": []}
    report = diff_auxiliary("national_notes", {}, "older schema without scope_type")
    assert report["status"] == "not_compared"
    assert report["reason"] == "to: older schema without scope_type"


def _aux_db(with_scope: bool) -> duckdb.DuckDBPyConnection:
    conn = duckdb.connect()
    conn.execute("CREATE TABLE nom_t (fraction8 VARCHAR, numeral INTEGER, nom VARCHAR, scope VARCHAR)")
    conn.execute("CREATE VIEW arancel_mx_nom_requirements AS SELECT * FROM nom_t")
    conn.execute("INSERT INTO nom_t VALUES ('85171301', 1, 'NOM-208-SCFI-2016', NULL)")
    if with_scope:
        conn.execute("CREATE TABLE notes_t (chapter VARCHAR, scope_type VARCHAR, scope_value VARCHAR, note_number VARCHAR, text VARCHAR)")
        conn.execute("INSERT INTO notes_t VALUES ('84', 'section', 'XVI', '1', 'Nota de sección'), ('85', 'section', 'XVI', '1', 'Nota de sección')")
    else:
        conn.execute("CREATE TABLE notes_t (chapter VARCHAR, note_number VARCHAR, text VARCHAR)")
    conn.execute("CREATE VIEW arancel_mx_national_notes AS SELECT * FROM notes_t")
    return conn


def test_auxiliary_rows_key_section_notes_by_chapter_and_detect_older_schemas() -> None:
    current = auxiliary_rows(_aux_db(with_scope=True))
    assert current["nom"] == {("85171301", "1", "NOM-208-SCFI-2016"): None}
    notes = current["national_notes"]
    assert isinstance(notes, dict)
    assert set(notes) == {("84", "section", "XVI", "1"), ("85", "section", "XVI", "1")}
    older = auxiliary_rows(_aux_db(with_scope=False))
    assert older["national_notes"] == "older schema without scope_type, scope_value"
    empty = auxiliary_rows(duckdb.connect())
    assert empty == {"nom": "view not present", "national_notes": "view not present"}
