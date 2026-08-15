from pathlib import Path

import pytest

from arancel_mx.parsers.documents import parse_national_notes_html

HTML = """
<html><head><script>void 0</script></head><body>
<h2>Capítulo 01</h2>
<p>1. Los animales vivos de este capítulo.</p>
<p>2. Se entiende por reproductores<br>de raza pura.</p>
<h2>Capítulo 02</h2>
<p>1. Carne y despojos comestibles.</p>
</body></html>
"""


def test_parse_national_notes_html_extracts_numbered_notes_by_chapter():
    rows = parse_national_notes_html(HTML, "doc-notes")
    assert [(row["chapter"], row["note_number"], row["text"]) for row in rows] == [
        ("01", "1", "Los animales vivos de este capítulo."),
        ("01", "2", "Se entiende por reproductores de raza pura."),
        ("02", "1", "Carne y despojos comestibles."),
    ]
    assert all(row["source_document_id"] == "doc-notes" for row in rows)


def test_parse_national_notes_html_rejects_empty_or_unnumbered_input():
    with pytest.raises(ValueError, match="source_document_id"):
        parse_national_notes_html(HTML, "")
    with pytest.raises(ValueError, match="no numbered notes"):
        parse_national_notes_html("<p>Capítulo 01 sin notas.</p>", "doc-notes")
    with pytest.raises(ValueError, match="missing text"):
        parse_national_notes_html("<p>Capítulo 01</p><p>1. </p>", "doc-notes")


def test_parse_national_notes_html_does_not_split_on_inline_chapter_references():
    html = """
    <h2>Capítulo 01</h2>
    <p>1. Véase el Capítulo 02 para esta regla complementaria del mismo título.</p>
    <h2>Capítulo 02</h2>
    <p>1. Carne y despojos comestibles.</p>
    """
    rows = parse_national_notes_html(html, "doc-notes")
    assert [(row["chapter"], row["note_number"]) for row in rows] == [("01", "1"), ("02", "1")]
    assert "Capítulo 02" in rows[0]["text"]


def test_parse_national_notes_html_handles_official_dof_section_and_chapter_scopes():
    html = (
        Path(__file__).parents[1] / "fixtures" / "dof" / "national-notes-2022.html"
    ).read_text(encoding="utf-8")

    rows = parse_national_notes_html(html, "official-dof-notes")

    section_i = [
        row
        for row in rows
        if row["scope_type"] == "section" and row["scope_value"] == "I"
    ]
    assert [row["chapter"] for row in section_i] == ["01", "02", "03", "04", "05"]
    assert all(row["note_number"] == "1" for row in section_i)

    section_vi = [
        row
        for row in rows
        if row["scope_type"] == "section" and row["scope_value"] == "VI"
    ]
    assert [row["chapter"] for row in section_vi] == [f"{number:02d}" for number in range(28, 39)]

    chapter_29 = [
        row
        for row in rows
        if row["scope_type"] == "chapter" and row["scope_value"] == "29"
    ]
    assert [(row["chapter"], row["note_number"]) for row in chapter_29] == [("29", "1")]

    chapter_97 = [row for row in rows if row["chapter"] == "97"]
    assert len(chapter_97) == 1
    assert "Artículo Segundo" not in chapter_97[0]["text"]
    assert chapter_97[0]["source_document_id"] == "official-dof-notes"
