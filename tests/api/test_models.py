from __future__ import annotations

from datetime import date

from arancel_mx.api.models import (
    FichaResponse,
    NationalNoteResponse,
    ProvenanceResponse,
    SearchResponse,
    SuggestResponse,
    TariffResponse,
)
from arancel_mx.consumer.models import (
    Ficha,
    HsSection,
    NationalNote,
    ProvenanceRecord,
    SearchResult,
    SuggestHit,
    TariffRecord,
)


def _nico_record() -> TariffRecord:
    return TariffRecord(
        code="0101210100",
        level="nico10",
        description="Reproductores de raza pura.",
        unit_name="Cbza",
        igi_text="Ex.",
        igi_kind="exento",
        igi_value=None,
        ige_text="Prohibida",
        ige_kind="prohibida",
        ige_value=None,
        parent_code="01012101",
        dataset_version="2026.08.15",
        schema_version="2",
        effective_from=date(2026, 1, 1),
        effective_to=None,
        is_current=True,
        hs2="01",
        hs4="0101",
        hs6="010121",
        fraccion8="01012101",
        nico2="00",
        nico10="0101210100",
        ligie_version="2022",
        validity_basis="published",
    )


def test_tariff_wire_model_preserves_nico_strings_and_official_text() -> None:
    payload = TariffResponse.from_record(_nico_record()).model_dump(mode="json")

    assert payload["code"] == "0101210100"
    assert payload["parent_code"] == "01012101"
    assert payload["hierarchy"] == {
        "hs2": "01",
        "hs4": "0101",
        "hs6": "010121",
        "fraccion8": "01012101",
        "nico2": "00",
        "nico10": "0101210100",
    }
    assert payload["igi"] == {"text": "Ex.", "kind": "exento", "value": None}
    assert payload["ige"] == {
        "text": "Prohibida",
        "kind": "prohibida",
        "value": None,
    }
    assert payload["effective_from"] == "2026-01-01"
    assert payload["is_current"] is True


def test_ficha_wire_model_preserves_explicit_hierarchy() -> None:
    record = _nico_record()
    ficha = Ficha(
        record=record,
        formatted_code="01.01.21.01.00",
        section=HsSection(
            roman="I",
            name="Animales vivos y productos del reino animal",
            chapter_from="01",
            chapter_to="05",
        ),
        hierarchy=(record,),
        children=(),
    )

    payload = FichaResponse.from_ficha(ficha).model_dump(mode="json")

    assert payload["formatted_code"] == "01.01.21.01.00"
    assert payload["section"]["roman"] == "I"
    assert payload["hierarchy"][0]["code"] == "0101210100"
    assert payload["children"] == []


def test_provenance_wire_model_preserves_source_fields() -> None:
    record = ProvenanceRecord(
        source_document_id="dof-1",
        role="legal_basis",
        is_primary=True,
        authority="DOF",
        publication_venue="Diario Oficial de la Federación",
        title="Decreto",
        source_url="https://www.dof.gob.mx/example",
        sha256="a" * 64,
        published_at=date(2022, 6, 7),
        effective_from=date(2022, 6, 8),
        effective_to=None,
    )

    payload = ProvenanceResponse.from_record(record).model_dump(mode="json")

    assert payload["source_document_id"] == "dof-1"
    assert payload["is_primary"] is True
    assert payload["published_at"] == "2022-06-07"
    assert payload["sha256"] == "a" * 64


def test_search_and_suggest_wire_models_keep_retrieval_metadata() -> None:
    record = _nico_record()
    search = SearchResult(
        record=record,
        score=1000,
        match_kind="exact_code",
        scorer_version="1",
        confidence=1.0,
    )
    ficha = Ficha(
        record=record,
        formatted_code="01.01.21.01.00",
        section=None,
        hierarchy=(record,),
        children=(),
    )
    note = NationalNote(
        chapter="01",
        note_number="1",
        text="Nota oficial.",
        source_document_id="dof-notes",
    )
    hit = SuggestHit(
        search=search,
        ficha=ficha,
        national_notes=(note,),
        disclaimer="This is not a classification.",
    )

    search_payload = SearchResponse.from_result(search).model_dump(mode="json")
    suggest_payload = SuggestResponse.from_hit(hit).model_dump(mode="json")

    assert search_payload["match_kind"] == "exact_code"
    assert search_payload["scorer_version"] == "1"
    assert search_payload["confidence"] == 1.0
    assert suggest_payload["disclaimer"] == "This is not a classification."
    assert suggest_payload["national_notes"] == [
        NationalNoteResponse.from_note(note).model_dump(mode="json")
    ]
