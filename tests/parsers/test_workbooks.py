from openpyxl import Workbook
import pytest

from arancel_mx.parsers.workbooks import (
    WorkbookProfile,
    parse_indicator_workbook,
    parse_ligie_workbook,
    parse_nico_workbook,
    probe_workbook,
)


SOURCE = {"source_document_id": "src-1"}


def make_workbook(tmp_path, name, rows):
    path = tmp_path / name
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "Datos"
    for row in rows:
        sheet.append(row)
    workbook.save(path)
    return path


def test_probe_is_bounded_and_reports_sheet_samples(tmp_path):
    path = make_workbook(
        tmp_path,
        "probe.xlsx",
        [["nota"], ["Fracción", "Descripción"], ["01012101", "Caballos"]],
    )

    probe = probe_workbook(path, sample_rows=2)

    assert probe.sheet_names == ("Datos",)
    assert len(probe.samples["Datos"]) == 2


def test_nico_parser_preserves_zeroes_in_split_columns(tmp_path):
    path = make_workbook(
        tmp_path,
        "nico.xlsx",
        [["Fracción", "NICO", "Descripción"], ["01012101", 0, "Reproductores"]],
    )
    profile = WorkbookProfile(
        sheet="Datos",
        header_row=1,
        columns={
            "fraccion8": "Fracción",
            "nico2": "NICO",
            "description": "Descripción",
        },
    )

    row = parse_nico_workbook(path, SOURCE, profile)[0]

    assert row.normalized["nico10"] == "0101210100"
    assert row.raw["nico2"] == "0"
    assert (row.sheet, row.row_number) == ("Datos", 2)


def test_ligie_parser_rejects_complete_short_code(tmp_path):
    path = make_workbook(
        tmp_path,
        "ligie.xlsx",
        [
            ["Fracción", "Descripción", "IGI", "IGE"],
            ["1012101", "Inválida", "10%", "Ex."],
        ],
    )
    profile = WorkbookProfile(
        sheet="Datos",
        header_row=1,
        columns={
            "code": "Fracción",
            "description": "Descripción",
            "igi": "IGI",
            "ige": "IGE",
        },
    )

    with pytest.raises(ValueError, match="width"):
        parse_ligie_workbook(path, SOURCE, profile)


def test_indicator_rows_remain_analytical(tmp_path):
    path = make_workbook(
        tmp_path,
        "indicator.xlsx",
        [["Año", "Indicador", "Valor"], [2025, "Arancel ponderado", 6.4]],
    )
    profile = WorkbookProfile(
        sheet="Datos",
        header_row=1,
        columns={"period": "Año", "indicator": "Indicador", "value": "Valor"},
    )

    row = parse_indicator_workbook(path, SOURCE, profile)[0]

    assert row.domain == "analytics"
    assert row.normalized["value"] == "6.4"
