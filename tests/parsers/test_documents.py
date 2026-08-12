from datetime import date
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import PageBreak, SimpleDocTemplate, Spacer, Table, TableStyle

from arancel_mx.parsers.documents import (
    _hierarchy_entries_from_table,
    parse_ligie_pdf_hierarchy,
)


SOURCE = Path(__file__).parents[2] / "src" / "arancel_mx" / "parsers" / "documents.py"


def _finished_hierarchy(pages: list[list[list[object]]]) -> dict[str, str]:
    pending_code: str | None = None
    pending_description: list[str] = []
    entries: list[tuple[str, str]] = []
    for table in pages:
        extracted, pending_code, pending_description = _hierarchy_entries_from_table(
            table,
            pending_code=pending_code,
            pending_description=pending_description,
        )
        entries.extend(extracted)
    leftover = " ".join(str(part) for part in pending_description).split()
    if pending_code and leftover:
        entries.append((pending_code, " ".join(leftover)))
    return dict(entries)


def test_pdf_parser_uses_supported_pymupdf_namespace():
    source = SOURCE.read_text(encoding="utf-8")

    assert "import fitz" not in source
    assert "fitz.open(" not in source
    assert "import pymupdf" in source
    assert "pymupdf.open(" in source


def test_pdf_parser_extracts_official_hierarchy(tmp_path):
    path = tmp_path / "ligie.pdf"
    story = [
        Table([["Capítulo 01"], ["Animales vivos"]]),
        Spacer(1, 10),
        Table(
            [
                ["CÓDIGO", "", "DESCRIPCIÓN", "UNIDAD", "IMP.", "EXP."],
                ["01.01", "", "Caballos, asnos, mulos y burdéganos, vivos.", "", "", ""],
                ["0101.21", "--", "Reproductores de raza pura.", "", "", ""],
                ["0101.21.01", "", "Reproductores de raza pura.", "Cbza", "10", "Ex."],
            ],
            colWidths=[70, 20, 280, 50, 40, 40],
            style=TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.black)]),
        ),
    ]
    SimpleDocTemplate(str(path), pagesize=letter).build(story)

    rows = parse_ligie_pdf_hierarchy(
        path, "doc-pdf", "LIGIE-2022", date(2025, 12, 29), None
    )

    assert [row["level"] for row in rows] == ["hs2", "hs4", "hs6"]
    assert [row["code"] for row in rows] == ["01", "0101", "010121"]
    assert rows[0]["description"] == "Animales vivos"


def test_hierarchy_continues_partida_text_across_page_break() -> None:
    page1 = [
        ["CÓDIGO", "", "DESCRIPCIÓN"],
        [
            "11.04",
            "",
            "Granos de cereales trabajados de otro modo (por ejemplo: mondados, "
            "aplastados, en copos, perlados, troceados o quebrantados), excepto el "
            "arroz de la partida 10.06; germen de cereales entero, aplastado, en copos o",
        ],
        ["", "", ""],
    ]
    page2 = [
        ["", "", "molido."],
        ["", "-", "Granos aplastados o en copos:"],
        ["1104.12", "--", "De avena."],
    ]

    by_code = _finished_hierarchy([page1, page2])

    assert by_code["1104"].endswith("en copos o molido.")
    assert "Granos aplastados o en copos" not in by_code["1104"]
    assert by_code["110412"] == "De avena."


def test_hierarchy_does_not_carry_decimal_measurements_as_hs_codes() -> None:
    notes = [
        ["Elemento", "Contenido límite % en peso"],
        ["Bi Bismuto Cu Cobre", "0.1 0.4"],
    ]
    tariff = [
        ["CÓDIGO", "", "DESCRIPCIÓN", "UNIDAD", "CUOTA (ARANCEL)", ""],
        ["", "", "", "", "IMPUESTO DE IMP.", "IMPUESTO DE EXP."],
        ["80.01", "", "Estaño en bruto.", "", "", ""],
    ]

    by_code = _finished_hierarchy([notes, tariff])

    assert "0104" not in by_code
    assert by_code["8001"] == "Estaño en bruto."


def test_hierarchy_does_not_merge_complete_heading_into_next_page() -> None:
    page1 = [
        ["11.03", "", 'Grañones, sémola y "pellets", de cereales.'],
        ["", "", ""],
    ]
    page2 = [["11.04", "", "Granos de cereales trabajados de otro modo."]]

    by_code = _finished_hierarchy([page1, page2])

    assert by_code["1103"] == 'Grañones, sémola y "pellets", de cereales.'
    assert by_code["1104"] == "Granos de cereales trabajados de otro modo."


def test_pdf_parser_joins_heading_split_across_pages(tmp_path: Path) -> None:
    path = tmp_path / "ligie-pagebreak.pdf"
    story = [
        Table(
            [
                ["CÓDIGO", "", "DESCRIPCIÓN"],
                ["11.04", "", "germen de cereales entero, aplastado, en copos o"],
            ],
            colWidths=[70, 20, 400],
            style=TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.black)]),
        ),
        PageBreak(),
        Table(
            [
                ["", "", "molido."],
                ["", "-", "Granos aplastados o en copos:"],
                ["1104.12", "--", "De avena."],
            ],
            colWidths=[70, 20, 400],
            style=TableStyle([("GRID", (0, 0), (-1, -1), 0.5, colors.black)]),
        ),
    ]
    SimpleDocTemplate(str(path), pagesize=letter).build(story)

    rows = parse_ligie_pdf_hierarchy(
        path, "doc-pdf", "LIGIE-2022", date(2025, 12, 29), None
    )
    by_code = {row["code"]: row["description"] for row in rows}

    assert by_code["1104"].endswith("molido.")
    assert "Granos aplastados o en copos" not in by_code["1104"]
    assert by_code["110412"] == "De avena."
