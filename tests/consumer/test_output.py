from __future__ import annotations

from datetime import date
import json
from pathlib import Path

from arancel_mx.consumer.models import Ficha, HsSection, SearchResult, TariffRecord
from arancel_mx.consumer.output import render_csv, render_json, render_path, render_table


def _record() -> TariffRecord:
    return TariffRecord(
        code="01012101",
        level="fraccion8",
        description="Reproductores de raza pura ñ",
        unit_name="Cbza",
        igi_text="10",
        igi_kind="ad_valorem",
        igi_value=10.0,
        ige_text="Ex.",
        ige_kind="exento",
        ige_value=0.0,
        parent_code="010121",
        dataset_version="2026.08.11",
        schema_version="2",
        effective_from=date(2026, 4, 20),
        effective_to=None,
        is_current=True,
    )


def test_json_output_is_utf8_safe_and_deterministic() -> None:
    first = render_json(_record())
    second = render_json(_record())

    assert first == second
    assert "ñ" in first
    assert "\\u00f1" not in first.lower()
    payload = json.loads(first)
    assert list(payload) == sorted(payload)
    assert payload["code"] == "01012101"
    assert payload["effective_from"] == "2026-04-20"
    assert payload["effective_to"] is None


def test_json_output_flattens_search_result_contract() -> None:
    text = render_json(SearchResult(_record(), 1000, "exact_code"))
    payload = json.loads(text)
    assert payload["score"] == 1000
    assert payload["match_kind"] == "exact_code"
    assert payload["record"]["code"] == "01012101"


def test_csv_output_has_stable_headers() -> None:
    text = render_csv((_record(),))
    lines = text.splitlines()

    assert lines[0] == (
        "code,level,description,unit_name,igi_text,igi_kind,igi_value,"
        "ige_text,ige_kind,ige_value,parent_code,dataset_version,schema_version,"
        "effective_from,effective_to,is_current"
    )
    assert lines[1].startswith("01012101,fraccion8,")
    assert text.endswith("\n")


def test_csv_search_result_has_score_and_match_kind_first() -> None:
    text = render_csv((SearchResult(_record(), 700, "code_prefix"),))
    assert text.splitlines()[0].startswith("score,match_kind,code,level,description")
    assert text.splitlines()[1].startswith("700,code_prefix,01012101,")


def test_csv_empty_typed_sequence_still_emits_schema_header() -> None:
    text = render_csv((), empty_schema="search")
    assert text.startswith("score,match_kind,code,level,description")
    assert text.count("\n") == 1


def test_table_output_handles_none_without_literal_python_repr() -> None:
    text = render_table((_record(),))
    assert "01012101" in text
    assert "Reproductores de raza pura ñ" in text
    assert "None" not in text


def test_table_output_empty_sequence_is_explicit() -> None:
    assert render_table(()) == "No results."


def test_path_output_is_plain_text_only(tmp_path: Path) -> None:
    path = tmp_path / "cache con ñ" / "arancel_mx.duckdb"
    assert render_path(path) == str(path)
    assert not render_path(path).startswith("{")
    assert "path=" not in render_path(path)


def _ficha() -> Ficha:
    record = _record()
    return Ficha(
        record=record,
        formatted_code="0101.21.01",
        section=HsSection("I", "Animales vivos y productos del reino animal", "01", "05"),
        hierarchy=(
            TariffRecord(
                code="01",
                level="hs2",
                description="Animales vivos",
                unit_name=None,
                igi_text=None,
                igi_kind=None,
                igi_value=None,
                ige_text=None,
                ige_kind=None,
                ige_value=None,
                parent_code=None,
                dataset_version="2026.08.11",
                schema_version="2",
                effective_from=None,
                effective_to=None,
                is_current=True,
            ),
            record,
        ),
        children=(),
    )


def test_ficha_json_includes_section_source_and_hierarchy() -> None:
    payload = json.loads(render_json(_ficha()))
    assert payload["formatted_code"] == "0101.21.01"
    assert payload["section"]["roman"] == "I"
    assert payload["section"]["source"] == "hs_section_grouping"
    assert payload["hierarchy"][0]["code"] == "01"


def test_ficha_csv_has_stable_headers() -> None:
    text = render_csv((_ficha(),))
    assert text.splitlines()[0] == (
        "section_roman,section_name,code,formatted_code,level,description,"
        "unit_name,igi_text,igi_kind,igi_value,ige_text,ige_kind,ige_value,"
        "parent_code,dataset_version,schema_version"
    )
    assert text.splitlines()[1].startswith("I,Animales vivos")


def test_ficha_table_is_a_human_card() -> None:
    text = render_table(_ficha())
    assert "0101.21.01" in text
    assert "Sección" in text
    assert "Capítulo" in text
    assert "Fracción" in text
    assert "IGI" in text


def test_ficha_table_lists_direct_children() -> None:
    nico = TariffRecord(
        code="0101210100",
        level="nico10",
        description="Reproductores de raza pura.",
        unit_name="Cbza",
        igi_text="10",
        igi_kind="ad_valorem",
        igi_value=10.0,
        ige_text="Ex.",
        ige_kind="exento",
        ige_value=0.0,
        parent_code="01012101",
        dataset_version="2026.08.11",
        schema_version="2",
        effective_from=None,
        effective_to=None,
        is_current=True,
    )
    card = _ficha()
    card = Ficha(
        record=card.record,
        formatted_code=card.formatted_code,
        section=card.section,
        hierarchy=card.hierarchy,
        children=(nico,),
    )
    text = render_table(card)
    assert "Hijos" in text
    assert "NICO" in text
    assert "0101.21.01 00" in text
