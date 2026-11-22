from __future__ import annotations

import json
from pathlib import Path

import duckdb
import pytest

from arancel_mx.cli import main
from arancel_mx.consumer.models import NomRequirement
from arancel_mx.consumer.nom_report import STATE_TEXT, nom_report
from tests.consumer.conftest import create_consumer_duckdb

MILK = NomRequirement(
    fraction8="04021001", numeral=1, numeral_meaning="import_noms", section=None,
    nom="NOM-222-SCFI/SAGARPA-2018", scope="Únicamente: leche descremada.",
    nico=({"nico": "00", "description": "Leche en polvo."},), annex_page=481, source_document_id="annex",
)
OTHER = NomRequirement(
    fraction8="04021099", numeral=1, numeral_meaning="import_noms", section=None,
    nom="NOM-X", scope=None, nico=(), annex_page=482, source_document_id="annex",
)


def test_rows_of_the_fraction_are_listed_and_other_fractions_are_ignored() -> None:
    report = nom_report("04021001", requirements=[OTHER, MILK], annex={"status": "available"}, dataset_version="2026.11.20")
    assert report["state"] == "listed"
    assert [row["nom"] for row in report["requirements"]] == ["NOM-222-SCFI/SAGARPA-2018"]
    assert report["requirements"][0]["nico_match"] is None
    assert "no es una determinación de cumplimiento" in str(report["note"])


def test_a_nico_code_says_whether_each_row_names_that_nico() -> None:
    listed = nom_report("0402100100", requirements=[MILK], annex={"status": "available"}, dataset_version=None)
    other = nom_report("0402100199", requirements=[MILK], annex={"status": "available"}, dataset_version=None)
    open_rows = nom_report("0402109900", requirements=[OTHER], annex={"status": "available"}, dataset_version=None)
    assert listed["requirements"][0]["nico_match"] == "listed"
    assert other["requirements"][0]["nico_match"] == "other_nico"
    assert open_rows["requirements"][0]["nico_match"] == "no_nico_limits"
    # The fraction stays listed: the report shows the row, it does not decide it away.
    assert other["state"] == "listed"


@pytest.mark.parametrize(
    ("annex", "state"),
    [
        ({"status": "available"}, "not_listed"),
        ({"status": "carried_forward", "carried_from": "2026.11.19"}, "not_listed_carried"),
        ({"status": "unavailable"}, "unavailable"),
        ({"status": "not_included"}, "unknown"),
        (None, "unknown"),
    ],
)
def test_an_empty_answer_is_never_reported_as_no_nom(annex: dict[str, str] | None, state: str) -> None:
    report = nom_report("01012101", requirements=[MILK], annex=annex, dataset_version=None)
    assert report["state"] == state
    assert report["requirements"] == []
    assert report["message"] == STATE_TEXT[state]
    assert "no aplica" not in str(report["message"]).lower()


def test_headings_are_not_looked_up_in_the_annex() -> None:
    report = nom_report("0402", requirements=[MILK], annex={"status": "available"}, dataset_version=None)
    assert report["state"] == "not_a_fraction"
    assert report["fraction8"] is None
    assert report["requirements"] == []


def _with_annex(path: Path, status: str) -> Path:
    with duckdb.connect(str(path)) as conn:
        conn.execute(
            "INSERT INTO nom_requirement VALUES ('r1', '01012101', 1, 'import_noms', NULL, 'NOM-051-SCFI', "
            "'Únicamente: reproductores.', '[{\"nico\":\"00\",\"description\":\"Reproductores\"}]', 12, 'fixture-source')"
        )
        conn.execute("CREATE OR REPLACE VIEW arancel_mx_nom_requirements AS SELECT * FROM nom_requirement")
        conn.execute("UPDATE dataset_release SET release_metadata_json = ?", [json.dumps({"nom_annex": {"status": status}})])
    return path


def test_cli_reports_rows_for_a_nico_of_a_local_release(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path = _with_annex(create_consumer_duckdb(tmp_path / "fixture.duckdb"), "available")
    assert main(["nom", "0101.21.01 00", "--dataset", str(path), "--format", "json"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert (report["code"], report["state"]) == ("0101210100", "listed")
    assert [(row["nom"], row["nico_match"]) for row in report["requirements"]] == [("NOM-051-SCFI", "listed")]

    assert main(["nom", "01012101", "--dataset", str(path)]) == 0
    table = capsys.readouterr().out
    assert table.splitlines()[0] == STATE_TEXT["listed"]
    assert "NOM-051-SCFI" in table


def test_cli_says_unknown_when_the_release_does_not_publish_the_annex(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path = create_consumer_duckdb(tmp_path / "fixture.duckdb")
    assert main(["nom", "01012101", "--dataset", str(path)]) == 0
    assert capsys.readouterr().out.strip() == STATE_TEXT["unknown"]
    assert main(["nom", "99999999", "--dataset", str(path)]) != 0
