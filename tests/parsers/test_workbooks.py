from pathlib import Path

from openpyxl import Workbook
import pytest
import xlrd

from arancel_mx.domain.normalization import normalize_code
from arancel_mx.parsers import workbooks
from arancel_mx.parsers.profiles import resolve_workbook_profile
from arancel_mx.parsers.workbooks import (
    WorkbookProfile,
    parse_indicator_workbook,
    parse_ligie_workbook,
    parse_nico_workbook,
    probe_workbook,
)

XLS_NUMERIC_SHORT = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "workbooks"
    / "ligie-numeric-short-code.xls"
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


def test_probe_stops_reading_after_sample_bound(tmp_path, monkeypatch):
    path = make_workbook(tmp_path, "probe.xlsx", [["h"]] + [[str(i)] for i in range(50)])
    seen: list[object] = []
    original = workbooks._iter_openpyxl_rows

    def wrapped(path, sheet_name=None, max_rows=None):
        assert max_rows == 3
        for item in original(path, sheet_name, max_rows=max_rows):
            seen.append(item)
            yield item

    monkeypatch.setattr(workbooks, "_iter_openpyxl_rows", wrapped)
    probe = probe_workbook(path, sample_rows=3)

    assert len(seen) == 3
    assert len(probe.samples["Datos"]) == 3


def test_probe_stops_reading_xls_after_sample_bound(monkeypatch):
    book = xlrd.open_workbook(str(XLS_NUMERIC_SHORT))
    assert book.sheet_by_index(0).nrows > 1
    seen: list[object] = []
    original = workbooks._iter_xlrd_rows

    def wrapped(path, sheet_name=None, max_rows=None):
        assert max_rows == 1
        for item in original(path, sheet_name, max_rows=max_rows):
            seen.append(item)
            yield item

    monkeypatch.setattr(workbooks, "_iter_xlrd_rows", wrapped)
    probe = probe_workbook(XLS_NUMERIC_SHORT, sample_rows=1)

    assert len(seen) == 1
    assert len(probe.samples["Datos"]) == 1


def test_excel_engine_selects_registered_reader_by_suffix():
    assert workbooks._excel_engine(Path("source.xls")) == "xlrd"
    assert workbooks._excel_engine(Path("source.xlsx")) == "openpyxl"

    with pytest.raises(ValueError, match="unsupported workbook format"):
        workbooks._excel_engine(Path("source.csv"))


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


def test_cell_keeps_integral_xlrd_floats_at_their_digit_width():
    assert workbooks._cell(1012101.0) == "1012101"
    assert workbooks._cell(10.5) == "10.5"
    with pytest.raises(ValueError, match="length"):
        normalize_code(workbooks._cell(1012101.0))
    assert normalize_code("1012101.0") == "10121010"


def test_ligie_parser_rejects_xlrd_numeric_short_code():
    book = xlrd.open_workbook(str(XLS_NUMERIC_SHORT))
    value = book.sheet_by_index(0).cell_value(1, 0)
    assert value == 1012101.0
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
        parse_ligie_workbook(XLS_NUMERIC_SHORT, SOURCE, profile)


def test_ligie_parser_omits_unregistered_unit_fields(tmp_path):
    path = make_workbook(
        tmp_path,
        "ligie.xlsx",
        [
            ["Fracción", "Descripción", "IGI", "IGE"],
            ["01012101", "Reproductores", "10", "Ex."],
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

    row = parse_ligie_workbook(path, SOURCE, profile)[0]

    assert "unit_code" not in row.normalized
    assert "unit_name" not in row.normalized


def test_ligie_parser_reads_two_row_tariff_header_from_resolved_profile(tmp_path):
    path = tmp_path / "current-ligie.xlsx"
    workbook = Workbook()
    sheet = workbook.active
    sheet.title = "FA"
    for _ in range(6):
        sheet.append([None])
    sheet.append(
        [None, None, "Fracción Arancelaria", "Descripción", "Unidad de Medida", "Arancel %", None]
    )
    sheet.append([None, None, None, None, None, "IMP.", "EXP."])
    sheet.append([None, None, "0101.21.01", "Reproductores", "Cbza", "10", "Ex."])
    workbook.save(path)

    profile = resolve_workbook_profile(probe_workbook(path), "ligie_snapshot").profile
    row = parse_ligie_workbook(path, SOURCE, profile)[0]

    assert (row.sheet, row.row_number) == ("FA", 9)
    assert row.normalized["code"] == "01012101"
    assert row.normalized["unit_name"] == "Cbza"
    assert row.normalized["igi_text"] == "10"
    assert row.normalized["igi_kind"] == "ad_valorem"
    assert str(row.normalized["igi_value"]) == "10"
    assert row.normalized["ige_text"] == "Ex."
    assert row.normalized["ige_kind"] == "exento"
    assert str(row.normalized["ige_value"]) == "0"


def test_ligie_parser_preserves_units_and_forward_fills_registered_columns(tmp_path):
    path = make_workbook(
        tmp_path,
        "ligie.xlsx",
        [
            ["Fracción", "Descripción", "Clave unidad", "Unidad", "IGI", "IGE"],
            ["01012101", "Primera", "01", "Cabeza", "10", "Ex."],
            ["01012102", "Segunda", "02", None, "10", "Ex."],
        ],
    )
    profile = WorkbookProfile(
        sheet="Datos",
        header_row=1,
        columns={
            "code": "Fracción",
            "description": "Descripción",
            "unit_code": "Clave unidad",
            "unit_name": "Unidad",
            "igi": "IGI",
            "ige": "IGE",
        },
        forward_fill=("unit_name",),
    )

    rows = parse_ligie_workbook(path, SOURCE, profile)

    assert rows[0].normalized["unit_code"] == "01"
    assert rows[0].normalized["unit_name"] == "Cabeza"
    assert rows[1].normalized["unit_code"] == "02"
    assert rows[1].normalized["unit_name"] == "Cabeza"


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
