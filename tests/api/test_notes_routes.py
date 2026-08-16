from __future__ import annotations

from fastapi.testclient import TestClient

from arancel_mx.api.app import create_app
from arancel_mx.consumer.models import DatasetInfo, NationalNote, TariffRecord


def _chapter(code: str, description: str) -> TariffRecord:
    return TariffRecord(
        code=code,
        level="hs2",
        description=description,
        unit_name=None,
        igi_text=None,
        igi_kind=None,
        igi_value=None,
        ige_text=None,
        ige_kind=None,
        ige_value=None,
        parent_code=None,
        dataset_version="2026.08.15",
        schema_version="2",
        effective_from=None,
        effective_to=None,
        is_current=True,
        hs2=code,
    )


class NotesDataset:
    info = DatasetInfo(
        dataset_version="2026.08.15",
        schema_version="2",
        path="/verified/arancel_mx.duckdb",
        source="managed-cache",
        structural_valid=True,
        release_verified=True,
        github_digest_state="verified",
    )

    def chapters(self) -> tuple[TariffRecord, ...]:
        return (
            _chapter("01", "Animales vivos."),
            _chapter("85", "Máquinas, aparatos y material eléctrico."),
        )

    def national_notes(self, chapter: str) -> tuple[NationalNote, ...]:
        assert chapter == "85"
        return (
            NationalNote(
                chapter="85",
                note_number="1",
                text="Texto oficial de la nota nacional.",
                source_document_id="dof-national-notes",
                scope_type="section",
                scope_value="XVI",
                applicability_basis="explicit",
            ),
        )


def _client(valid_settings) -> TestClient:
    dataset = NotesDataset()
    return TestClient(
        create_app(settings=valid_settings, dataset_loader=lambda settings: dataset)
    )


def test_chapters_return_current_hs2_records(valid_settings) -> None:
    with _client(valid_settings) as client:
        response = client.get("/v1/chapters")

    assert response.status_code == 200
    payload = response.json()
    assert [row["code"] for row in payload] == ["01", "85"]
    assert all(row["level"] == "hs2" for row in payload)


def test_national_notes_return_only_requested_two_digit_chapter(valid_settings) -> None:
    with _client(valid_settings) as client:
        response = client.get("/v1/chapters/85/national-notes")

    assert response.status_code == 200
    payload = response.json()
    assert payload == [
        {
            "chapter": "85",
            "note_number": "1",
            "text": "Texto oficial de la nota nacional.",
            "source_document_id": "dof-national-notes",
            "scope_type": "section",
            "scope_value": "XVI",
            "applicability_basis": "explicit",
        }
    ]


def test_national_notes_reject_invalid_chapter_shape_at_transport_boundary(valid_settings) -> None:
    with _client(valid_settings) as client:
        responses = (
            client.get("/v1/chapters/8/national-notes"),
            client.get("/v1/chapters/8501/national-notes"),
            client.get("/v1/chapters/ab/national-notes"),
        )

    assert {response.status_code for response in responses} == {422}
    assert {response.json()["error"]["code"] for response in responses} == {
        "validation_error"
    }
