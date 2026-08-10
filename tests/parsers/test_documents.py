from datetime import date
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Spacer, Table, TableStyle

from arancel_mx.parsers.documents import parse_ligie_pdf_hierarchy


SOURCE = Path(__file__).parents[2] / "src" / "arancel_mx" / "parsers" / "documents.py"


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
