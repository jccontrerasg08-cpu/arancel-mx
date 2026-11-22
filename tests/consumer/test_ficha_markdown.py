from __future__ import annotations

from dataclasses import replace
from datetime import date
from pathlib import Path

import pytest

from arancel_mx.cli import main
from arancel_mx.consumer.ficha_markdown import annex_state, escape, ficha_markdown, safe_url
from arancel_mx.consumer.models import Ficha, HsSection, NationalNote, NomRequirement, ProvenanceRecord, TariffRecord
from tests.consumer.conftest import create_consumer_duckdb

RECORD = TariffRecord(
    code="85171301", level="fraccion8", description="Teléfonos inteligentes.", unit_name="Pza",
    igi_text="Ex.", igi_kind="exento", igi_value=0.0, ige_text="Ex.", ige_kind="exento", ige_value=0.0,
    parent_code="851713", dataset_version="2026.11.20", schema_version="2",
    effective_from=date(2022, 12, 12), effective_to=None, is_current=True,
)
FICHA = Ficha(record=RECORD, formatted_code="8517.13.01", section=HsSection(roman="XVI", name="Máquinas", chapter_from="84", chapter_to="85"), hierarchy=(), children=())
NOM = NomRequirement(fraction8="85171301", numeral=3, numeral_meaning="commercial_information_noms", section=None, nom="NOM-024-SCFI-2013", scope="Únicamente: móviles", nico=(), annex_page=743, source_document_id="annex")
SOURCE = ProvenanceRecord(source_document_id="s", role="ligie_snapshot", is_primary=True, authority="SNICE", publication_venue="SNICE", title="Fracciones LIGIE", source_url="https://www.snice.gob.mx/x.xlsx", sha256="a" * 64, published_at=None, effective_from=None, effective_to=None)


def _render(**kwargs: object) -> str:
    options: dict[str, object] = {"generated_at": "2026-11-22T10:00:00+00:00", "release_verified": True}
    options.update(kwargs)
    return ficha_markdown(FICHA, **options)  # type: ignore[arg-type]


def test_card_has_release_literal_values_and_the_not_official_notice() -> None:
    text = _render(provenance=[SOURCE], nom_requirements=[NOM], annex={"status": "available"})
    assert text.startswith("# Ficha arancelaria 8517.13.01\n")
    assert "- **Release de datos:** data-2026.11.20 (verificada)" in text
    assert "| IGI (importación) | Ex. |" in text
    assert "| Vigencia de la tasa publicada | desde 2022-12-12 |" in text
    assert "No es una clasificación arancelaria oficial" in text
    assert "- NOM-024-SCFI-2013 (numeral 3; acotación: Únicamente: móviles; página 743)" in text
    assert "[Fracciones LIGIE](<https://www.snice.gob.mx/x.xlsx>) (SNICE) — SHA-256 `" + "a" * 64 + "`" in text


def test_missing_values_are_not_published_never_zero() -> None:
    record = replace(RECORD, igi_text=None, unit_name="", effective_from=None)
    text = ficha_markdown(replace(FICHA, record=record), generated_at="x", release_verified=False)
    assert "| IGI (importación) | _No publicado en esta release_ |" in text
    assert "| Unidad de medida | _No publicado en esta release_ |" in text
    assert "| Vigencia de la tasa publicada | _No publicado en esta release_ |" in text
    assert "(archivo local, sin verificación remota)" in text
    assert "La release no indica si incluye el Anexo 2.4.1" in text
    assert "La release no registra fuentes para este código." in text


@pytest.mark.parametrize(
    ("annex", "requirements", "code", "state"),
    [
        ({"status": "available"}, [NOM], "85171301", "listed"),
        ({"status": "available"}, [], "85171301", "not_listed"),
        ({"status": "carried_forward", "carried_from": "2026.11.19"}, [], "85171301", "not_listed_carried"),
        ({"status": "unavailable"}, [], "85171301", "unavailable"),
        ({"status": "not_included"}, [], "85171301", "unknown"),
        (None, [], "85171301", "unknown"),
        ({"status": "available"}, [], "8517", "not_a_fraction"),
    ],
)
def test_annex_states_match_the_record_page(annex, requirements, code, state) -> None:
    assert annex_state(annex, requirements, code) == state


def test_carried_annex_names_the_release_and_other_fractions_noms_are_ignored() -> None:
    other = replace(NOM, fraction8="85171302")
    text = _render(nom_requirements=[other], annex={"status": "carried_forward", "carried_from": "2026.11.19"})
    assert "release anterior" in text and "2026.11.19." in text
    assert "NOM-024" not in text


def test_notes_are_ordered_section_first_then_by_number() -> None:
    notes = [
        NationalNote(chapter="85", note_number="10", text="Nota diez", source_document_id="n", scope_type="chapter", scope_value="85"),
        NationalNote(chapter="85", note_number="2", text="Nota dos", source_document_id="n", scope_type="chapter", scope_value="85"),
        NationalNote(chapter="85", note_number="1", text="Nota de sección", source_document_id="n", scope_type="section", scope_value="XVI"),
    ]
    text = _render(national_notes=notes)
    assert text.index("Nota 1 (Sección XVI)") < text.index("Nota 2 (Capítulo 85)") < text.index("Nota 10 (Capítulo 85)")


def test_data_text_cannot_inject_links_html_or_cells() -> None:
    record = replace(RECORD, description="Equipo [x](javascript:alert(1)) <img src=x> | celda\nlínea")
    text = ficha_markdown(replace(FICHA, record=record), generated_at="x", release_verified=True)
    assert "Equipo \\[x\\](javascript:alert(1)) \\<img src=x\\> \\| celda línea" in text
    assert safe_url("javascript:alert(1)") is None
    assert safe_url("https://dof.gob.mx/x") == "https://dof.gob.mx/x"
    assert escape("a_b*c") == "a\\_b\\*c"
    bad = replace(SOURCE, source_url="javascript:alert(1)", title="Fuente")
    assert "- Fuente (SNICE)" in _render(provenance=[bad])


def test_cli_writes_the_markdown_card_for_a_local_dataset(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    path = create_consumer_duckdb(tmp_path / "fixture.duckdb")
    assert main(["ficha", "01012101", "--dataset", str(path), "--format", "markdown"]) == 0
    text = capsys.readouterr().out
    assert text.startswith("# Ficha arancelaria 0101.21.01\n")
    assert "(archivo local, sin verificación remota)" in text
    assert "| IGI (importación) | 10 |" in text
    assert "## NOM del Anexo 2.4.1" in text
