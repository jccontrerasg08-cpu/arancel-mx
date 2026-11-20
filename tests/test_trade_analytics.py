from decimal import Decimal

from arancel_mx.trade_analytics import _columns, build_snapshot, canonical_row, parse_decimal


def test_parse_decimal_accepts_common_official_formats():
    assert parse_decimal("1,234.50") == Decimal("1234.50")
    assert parse_decimal("1.234,50") == Decimal("1234.50")
    assert parse_decimal("C") is None


def test_snapshot_preserves_confidentiality_instead_of_zeroing_values():
    columns = _columns(["ANIO", "MES", "TIPO", "PAIS_O_D", "TARIFA", "ESTATUS_CIFRA", "VAL_USD"])
    public = canonical_row({"ANIO": "2025", "MES": "1", "TIPO": "Exportación", "PAIS_O_D": "Estados Unidos", "TARIFA": "0101.21.01", "ESTATUS_CIFRA": "", "VAL_USD": "100"}, columns)
    confidential = canonical_row({"ANIO": "2025", "MES": "1", "TIPO": "Exportación", "PAIS_O_D": "Estados Unidos", "TARIFA": "0101.21.02", "ESTATUS_CIFRA": "C", "VAL_USD": "900"}, columns)
    snapshot = build_snapshot([public, confidential], retrieved_at="2026-01-01T00:00:00Z")
    partner = snapshot["observations"]["partners"][0]
    assert partner["value_usd"] == 100.0
    assert partner["confidential_rows"] == 1
