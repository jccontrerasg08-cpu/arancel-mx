from decimal import Decimal

import pytest

from arancel_mx.trade_analytics import _columns, build_snapshot, canonical_row, parse_decimal


COLUMNS = ["ANIO", "MES", "TIPO", "PAIS_O_D", "TARIFA", "ESTATUS_CIFRA", "VAL_USD"]


def _row(partner="Estados Unidos", status="", value="100", tariff="0101.21.01", flow="Exportación"):
    return canonical_row(
        {"ANIO": "2025", "MES": "1", "TIPO": flow, "PAIS_O_D": partner, "TARIFA": tariff, "ESTATUS_CIFRA": status, "VAL_USD": value},
        _columns(COLUMNS),
    )


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("1234", "1234"), ("-12.5", "-12.5"), ("+7", "7"), ("0.123", "0.123"), ("1234.567", "1234.567"),
        ("12,5", "12.5"), ("1,234.50", "1234.50"), ("1.234,50", "1234.50"),
        ("1,234,567", "1234567"), ("1.234.567", "1234567"), ("$ 1,234.5", "1234.5"), (1500, "1500"),
    ],
)
def test_parse_decimal_accepts_unambiguous_formats(raw, expected):
    assert parse_decimal(raw) == Decimal(expected)


@pytest.mark.parametrize("raw", ["", "  ", None, "C", "c", "N/D", "NA", "-"])
def test_parse_decimal_returns_none_for_missing_markers(raw):
    assert parse_decimal(raw) is None


@pytest.mark.parametrize(
    "raw",
    ["1,234", "1.234", "12,345", "123.456", "1,23,4", "1.2.3", "1,234.567,8", "1.234,56,7", "abc", "1e5", "NaN", "Infinity", "--5", "(5)", "1,,234", ".5", "5."],
)
def test_parse_decimal_rejects_ambiguous_or_malformed_input(raw):
    with pytest.raises(ValueError):
        parse_decimal(raw)


def test_canonical_row_names_the_malformed_column():
    with pytest.raises(ValueError, match="VAL_USD"):
        _row(value="1,234")


def test_all_confidential_group_has_null_value_not_zero():
    snapshot = build_snapshot([_row(status="C"), _row(status="Confidencial", value="5")], retrieved_at="2026-01-01T00:00:00Z")
    for view in ("partners", "tariff_groups", "monthly"):
        item = snapshot["observations"][view][0]
        assert item["value_usd"] is None
        assert item["confidential_rows"] == 2


def test_group_with_only_unavailable_values_is_null():
    snapshot = build_snapshot([_row(value="")], retrieved_at="2026-01-01T00:00:00Z")
    item = snapshot["observations"]["partners"][0]
    assert item["value_usd"] is None
    assert item["unavailable_value_rows"] == 1


def test_genuine_zero_is_preserved_and_null_ranks_last():
    snapshot = build_snapshot(
        [_row(partner="A", value="0"), _row(partner="B", status="C"), _row(partner="C", value="10")],
        retrieved_at="2026-01-01T00:00:00Z",
    )
    partners = snapshot["observations"]["partners"]
    assert [(p["partner"], p["value_usd"]) for p in partners] == [("C", 10.0), ("A", 0.0), ("B", None)]


def test_empty_input_is_not_loaded():
    snapshot = build_snapshot([], retrieved_at="2026-01-01T00:00:00Z")
    assert snapshot["status"] == "not_loaded"
    assert snapshot["coverage"] == {"period_start": None, "period_end": None, "input_rows": 0}
    assert snapshot["observations"]["partners"] == []


def test_malformed_csv_value_fails_closed(tmp_path):
    from arancel_mx.trade_analytics import read_bcmm_csv

    path = tmp_path / "bcmm.csv"
    path.write_text("ANIO,MES,TIPO,PAIS_O_D,VAL_USD\n2025,1,Exportación,México,\"1,234\"\n", encoding="utf-8")
    with pytest.raises(ValueError, match="VAL_USD"):
        read_bcmm_csv(path)


def test_csv_missing_required_columns_is_rejected(tmp_path):
    from arancel_mx.trade_analytics import read_bcmm_csv

    path = tmp_path / "bad.csv"
    path.write_text("A,B\n1,2\n", encoding="utf-8")
    with pytest.raises(ValueError):
        read_bcmm_csv(path)


def test_snapshot_preserves_confidentiality_instead_of_zeroing_values():
    columns = _columns(["ANIO", "MES", "TIPO", "PAIS_O_D", "TARIFA", "ESTATUS_CIFRA", "VAL_USD"])
    public = canonical_row({"ANIO": "2025", "MES": "1", "TIPO": "Exportación", "PAIS_O_D": "Estados Unidos", "TARIFA": "0101.21.01", "ESTATUS_CIFRA": "", "VAL_USD": "100"}, columns)
    confidential = canonical_row({"ANIO": "2025", "MES": "1", "TIPO": "Exportación", "PAIS_O_D": "Estados Unidos", "TARIFA": "0101.21.02", "ESTATUS_CIFRA": "C", "VAL_USD": "900"}, columns)
    snapshot = build_snapshot([public, confidential], retrieved_at="2026-01-01T00:00:00Z")
    partner = snapshot["observations"]["partners"][0]
    assert partner["value_usd"] == 100.0
    assert partner["confidential_rows"] == 1
