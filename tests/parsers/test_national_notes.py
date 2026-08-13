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
