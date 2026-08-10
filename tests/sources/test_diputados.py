from pathlib import Path

from arancel_mx.sources.diputados import parse_ligie_ledger


FIXTURE = Path(__file__).parents[1] / "fixtures" / "diputados" / "ligie_2022.html"
BASE_URL = "https://www.diputados.gob.mx/LeyesBiblio/ref/ligie_2022.htm"


def test_parser_keeps_law_tariff_dates_and_document_families_distinct():
    snapshot = parse_ligie_ledger(FIXTURE.read_text(encoding="utf-8"), BASE_URL)

    assert snapshot.last_law_reform.isoformat() == "2025-12-29"
    assert snapshot.latest_tariff_modification.isoformat() == "2026-04-23"
    assert {document.category for document in snapshot.documents} == {
        "consolidated_text",
        "original",
        "law_reform",
        "tariff_decree",
        "nico_agreement",
        "national_notes",
        "correlation",
    }


def test_official_ref_url_identifies_law_reform_when_visual_section_heading_is_missing():
    html = """
    <html><body>
      <p>Última reforma publicada en el Diario Oficial de la Federación el 29 de diciembre de 2025</p>
      <p>Fracciones arancelarias de la Tarifa de la Ley modificadas por Decreto DOF 23-04-2026</p>
      <table>
        <tr><th>Publicación Original</th></tr>
        <tr>
          <td>02</td>
          <td>DECRETO por el que se reforman diversas fracciones arancelarias</td>
          <td><a href="ligie_2022/LIGIE_2022_ref02_29dic25.pdf">DOF 29-12-2025</a></td>
          <td><a href="ligie_2022/LIGIE_2022_ref02_29dic25.doc">Word</a></td>
        </tr>
        <tr><th>Decretos que modifican la Tarifa de la Ley</th></tr>
        <tr>
          <td>15</td>
          <td>DECRETO por el que se modifica la Tarifa</td>
          <td><a href="ligie_2022/LIGIE_2022_tarifa15_23abr26.pdf">DOF 23-04-2026</a></td>
        </tr>
      </table>
    </body></html>
    """

    snapshot = parse_ligie_ledger(html, BASE_URL)
    reform = next(document for document in snapshot.documents if document.ordinal == "02")

    assert reform.category == "law_reform"
    assert reform.displayed_date.isoformat() == "2025-12-29"
    assert reform.links[0].role == "dof"
    assert reform.links[0].displayed_date.isoformat() == "2025-12-29"
