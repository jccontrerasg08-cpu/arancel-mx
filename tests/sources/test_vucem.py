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


def test_fraction_sheet_ignores_nico_prefix_false_positives() -> None:
    html = """
    <table>
      <tr><th>Fracción</th><th>Descripción</th><th>IGI</th><th>IGE</th></tr>
      <tr><td>9001400200</td><td>NICO row</td><td>Ex.</td><td>Ex.</td></tr>
    </table>
    """
    with pytest.raises(ValueError, match="missing a tariff row"):
        parse_fraction_sheet(
            html,
            base_url="https://www.ventanillaunica.gob.mx/Clasificador/data/buildHojas1/90014002.html",
        )


def test_fraction_sheet_parses_labeled_hierarchy_row_with_description_digits() -> None:
    """Live VUCEM sheets put 90014002 next to a Fracción label, not in cell 0.

    The official description also contains digits (3 mm / 3.8 mm). Matching the
    whole row as a digit string would either miss the 8-digit identity or
    confuse it with NICO 9001400200.
    """
    html = """
    <table>
      <tr><td>Sección:</td><td>XVIII Instrumentos y aparatos de óptica</td></tr>
      <tr><td>Capítulo:</td><td>90</td></tr>
      <tr><td>Partida:</td><td>9001</td></tr>
      <tr><td>SubPartida:</td><td>900140</td></tr>
      <tr><td>Fracción:</td><td>90014002</td></tr>
      <tr><td>Lentes de cristal oftálmico, sin graduación, destinados a la fabricación de anteojos de seguridad, con espesor igual o superior a 3 mm sin exceder de 3.8 mm.</td></tr>
    </table>
    <table>
      <tr><th>UM</th><th>Arancel</th><th>IVA</th></tr>
      <tr><td>Importación</td><td>5</td><td>16%</td></tr>
      <tr><td>Exportación</td><td>Ex.</td><td>0%</td></tr>
    </table>
    """
    sheet = parse_fraction_sheet(
        html,
        base_url="https://www.ventanillaunica.gob.mx/Clasificador/data/buildHojas1/90014002.html",
    )
    assert sheet.code == "90014002"
    assert "cristal oftálmico" in sheet.description.casefold()
    assert "3.8" in sheet.description


def test_fraction_sheet_url_rejects_invalid_codes() -> None:
    with pytest.raises(ValueError, match="8 digits"):
        fraction_sheet_url("9001")
