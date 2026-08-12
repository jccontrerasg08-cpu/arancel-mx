from __future__ import annotations

from pathlib import Path

import pytest

from arancel_mx.sources.vucem import fraction_sheet_url, parse_fraction_sheet


FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "vucem"


def test_parse_fraction_sheet_extracts_tariff_fields() -> None:
    html = (FIXTURES / "buildHojas1.90014002.html").read_text(encoding="utf-8")
    sheet = parse_fraction_sheet(
        html,
        base_url="https://www.ventanillaunica.gob.mx/Clasificador/data/buildHojas1/90014002.html",
    )
    assert sheet.code == "90014002"
    assert sheet.nico_rows[0][0] == "00"


def test_fraction_sheet_url_rejects_invalid_codes() -> None:
    with pytest.raises(ValueError, match="8 digits"):
        fraction_sheet_url("9001")
