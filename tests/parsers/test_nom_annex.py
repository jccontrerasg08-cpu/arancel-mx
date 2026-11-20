"""Annex 2.4.1 reader: rows laid out like the real PDF (fraction x~91, NICO x~140, description x~161, NOM column after the rule)."""

import pytest

from arancel_mx.parsers.nom_annex import AnnexPage, AnnexParseError, parse_annex, requirement_rows

RULE = (375.8, 100.0, 700.0)


class Page:
    """Builds words in reading order: each call is one text line of one block."""

    def __init__(self) -> None:
        self.words: list[tuple] = []
        self.block = 0

    def line(self, x: float, y: float, text: str) -> "Page":
        self.block += 1
        for index, token in enumerate(text.split()):
            self.words.append(
                (
                    x + index * 30,
                    y,
                    x + index * 30 + 25,
                    y + 8,
                    token,
                    self.block,
                    0,
                    index,
                )
            )
        return self

    def header(self, y: float = 60.0) -> "Page":
        self.line(91, y, "Fracción")
        self.line(91, y + 10, "arancelaria/N")
        self.line(130, y + 10, "ICO")
        self.line(161, y + 10, "Descripción")
        self.line(380, y + 10, "NOM")
        return self

    def page(self) -> AnnexPage:
        return AnnexPage(tuple(self.words), (RULE,))


def test_numeral_one_row_with_nico_and_scope() -> None:
    page = Page().line(91, 20, "1.-").header()
    page.line(91, 120, "0101.21.01").line(161, 120, "Reproductores de raza pura").line(
        380, 120, "NOM-EM-004-SAG/ZOO-2020"
    )
    page.line(140, 140, "00").line(161, 140, "Para reproducción").line(
        380, 140, "Únicamente: para cría"
    )
    result = parse_annex([page.page()])
    (record,) = result.records
    assert (record.numeral, record.fraction, record.description) == (
        1,
        "01012101",
        "Reproductores de raza pura",
    )
    assert [(r.nom, r.scope) for r in record.requirements] == [
        ("NOM-EM-004-SAG/ZOO-2020", "Únicamente: para cría")
    ]
    assert [(n.nico, n.description) for n in record.nico] == [
        ("00", "Para reproducción")
    ]


def test_numeral_three_takes_the_nom_from_the_section_heading() -> None:
    page = Page().line(91, 20, "3.-").line(299, 40, "I.")
    page.line(
        91,
        52,
        "Norma Oficial Mexicana NOM-004-SE-2021, Etiquetado de textiles (cancela a la NOM-004-SCFI-2006):",
    )
    page.header(80)
    page.line(91, 130, "6109.10.01").line(161, 130, "Playeras")
    result = parse_annex([page.page()])
    (record,) = result.records
    assert record.section == "I"
    assert [r.nom for r in record.requirements] == ["NOM-004-SE-2021"]
    assert record.superseded_noms == ("NOM-004-SCFI-2006",)


def test_wrapped_nom_code_is_joined() -> None:
    page = Page().line(91, 20, "2.-").header()
    page.line(91, 120, "2710.12.99").line(161, 120, "Gasolinas").line(
        380, 120, "NOM-016-CRE-"
    )
    page.line(380, 131, "2016")
    (record,) = parse_annex([page.page()]).records
    assert [r.nom for r in record.requirements] == ["NOM-016-CRE-2016"]


def test_text_in_fraction_column_that_is_not_a_fraction_fails() -> None:
    page = Page().line(91, 20, "1.-").header().line(91, 120, "0101.2")
    with pytest.raises(AnnexParseError, match="fraction column"):
        parse_annex([page.page()])


def test_nom_text_without_a_code_fails() -> None:
    page = Page().line(91, 20, "1.-").header()
    page.line(91, 120, "0101.21.01").line(161, 120, "Caballos").line(
        380, 120, "Norma pendiente"
    )
    with pytest.raises(AnnexParseError, match="no NOM code"):
        parse_annex([page.page()])


def test_unreadable_nom_code_fails() -> None:
    page = Page().line(91, 20, "1.-").header()
    page.line(91, 120, "0101.21.01").line(161, 120, "Caballos").line(
        380, 120, "NOM-XX-2020"
    )
    with pytest.raises(AnnexParseError, match="unreadable NOM"):
        parse_annex([page.page()])


def test_numeral_three_section_without_nom_in_heading_fails() -> None:
    page = (
        Page()
        .line(91, 20, "3.-")
        .line(299, 40, "I.")
        .line(91, 52, "Titulo sin norma:")
        .header(80)
    )
    page.line(91, 130, "6109.10.01").line(161, 130, "Playeras")
    with pytest.raises(AnnexParseError, match="heading"):
        parse_annex([page.page()])


def test_table_before_any_numeral_fails() -> None:
    page = Page().header().line(91, 120, "0101.21.01")
    with pytest.raises(AnnexParseError, match="before any numeral"):
        parse_annex([page.page()])


def test_empty_numeral_five_keeps_its_text_apart() -> None:
    page = (
        Page().line(91, 20, "5.-").header().line(161, 120, "Sin fracciones por ahora.")
    )
    result = parse_annex([page.page()])
    assert result.records == ()
    assert any("Sin fracciones" in text for _, text in result.free_text)


def test_fraction_row_without_any_nom_fails() -> None:
    page = Page().line(91, 20, "1.-").header()
    page.line(91, 120, "0101.21.01").line(161, 120, "Caballos")
    with pytest.raises(AnnexParseError, match="no NOM code"):
        parse_annex([page.page()])


def test_numeral_five_fraction_row_is_parsed_not_dropped() -> None:
    page = Page().line(91, 20, "5.-").header()
    page.line(91, 120, "2710.12.99").line(161, 120, "Gasolinas").line(380, 120, "NOM-EM-001-CRE-2026")
    (record,) = parse_annex([page.page()]).records
    assert (record.numeral, [r.nom for r in record.requirements]) == (5, ["NOM-EM-001-CRE-2026"])


def test_requirement_rows_expand_one_row_per_nom_and_keep_numeral_and_scope() -> None:
    page = Page().line(91, 20, "3.-").line(299, 40, "I.")
    page.line(91, 52, "Norma Oficial Mexicana NOM-004-SE-2021 y NOM-050-SCFI-2004:")
    page.header(80)
    page.line(91, 130, "6109.10.01").line(161, 130, "Playeras").line(380, 130, "Excepto: usadas")
    rows = requirement_rows(parse_annex([page.page()]), source_document_id="doc-annex")
    assert [(r["fraction8"], r["numeral"], r["numeral_meaning"], r["section"], r["nom"], r["scope"]) for r in rows] == [
        ("61091001", 3, "commercial_information_noms", "I", "NOM-004-SE-2021", "Excepto: usadas"),
        ("61091001", 3, "commercial_information_noms", "I", "NOM-050-SCFI-2004", "Excepto: usadas"),
    ]
    assert {r["source_document_id"] for r in rows} == {"doc-annex"}


def test_locate_annex_pages_finds_the_heading_and_stops_before_the_next_annex(tmp_path) -> None:
    from arancel_mx.parsers.nom_annex import locate_annex_pages
    from tests.pipeline.annex_fixture import annex_pdf_bytes

    pdf = tmp_path / "reglas.pdf"
    pdf.write_bytes(annex_pdf_bytes())
    assert locate_annex_pages(pdf) == (2, 2)


def test_locate_annex_pages_fails_when_the_annex_is_missing(tmp_path) -> None:
    import pymupdf

    from arancel_mx.parsers.nom_annex import locate_annex_pages

    document = pymupdf.open()
    document.new_page().insert_text((91, 80), "ANEXO 2.5.1")
    pdf = tmp_path / "sin-anexo.pdf"
    document.save(pdf)
    with pytest.raises(AnnexParseError, match="heading not found"):
        locate_annex_pages(pdf)


def test_a_requirement_repeated_in_the_annex_is_kept_once_with_every_nico_line() -> None:
    page = Page().line(91, 20, "1.-").header()
    page.line(91, 120, "0101.21.01").line(161, 120, "Caballos").line(380, 120, "NOM-EM-004-SAG/ZOO-2020")
    page.line(140, 140, "00").line(161, 140, "Primero")
    page.line(91, 160, "0101.21.01").line(161, 160, "Caballos").line(380, 160, "NOM-EM-004-SAG/ZOO-2020")
    page.line(140, 180, "01").line(161, 180, "Segundo")
    rows = requirement_rows(parse_annex([page.page()]), source_document_id="doc-annex")
    assert len(rows) == 1
    assert [line["nico"] for line in rows[0]["nico"]] == ["00", "01"]


def test_the_span_keeps_a_page_where_the_next_annex_starts_midway_and_trims_it(tmp_path) -> None:
    import pymupdf

    from arancel_mx.parsers.nom_annex import locate_annex_span, read_annex_pages

    document = pymupdf.open()
    first = document.new_page()
    first.insert_text((91, 30), "Cola del anexo anterior")
    first.insert_text((91, 200), "ANEXO 2.4.1")
    first.insert_text((91, 220), "1.-")
    second = document.new_page()
    second.insert_text((91, 30), "texto del anexo")
    second.insert_text((91, 400), "ANEXO 2.5.1")
    second.insert_text((91, 430), "Texto del siguiente anexo")
    pdf = tmp_path / "mitad.pdf"
    document.save(pdf)

    span = locate_annex_span(pdf)

    assert (span.first_page, span.last_page) == (1, 2)
    assert span.start_y > 150 and span.end_y is not None and span.end_y > 300
    pages = read_annex_pages(pdf, span.first_page, span.last_page, start_y=span.start_y, end_y=span.end_y)
    texts = {word[4] for page in pages for word in page.words}
    assert "anterior" not in texts and "siguiente" not in texts
    assert "texto" in texts and "1.-" in texts
