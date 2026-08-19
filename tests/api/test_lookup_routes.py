from __future__ import annotations

from datetime import date

from fastapi.testclient import TestClient

from arancel_mx.api.app import create_app
from arancel_mx.consumer.errors import InvalidCodeError, RecordNotFoundError
from arancel_mx.consumer.models import (
    DatasetInfo,
    Ficha,
    ProvenanceRecord,
    TariffRecord,
)


def _record(code: str = "0101210100") -> TariffRecord:
    if code == "01":
        return TariffRecord(
            code="01",
            level="hs2",
            description="Animales vivos.",
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
            effective_from=date(2026, 1, 1),
            effective_to=None,
            is_current=True,
            hs2="01",
        )
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


class LookupDataset:
    info = DatasetInfo(
        dataset_version="2026.08.15",
        schema_version="2",
        path="/verified/arancel_mx.duckdb",
        source="managed-cache",
        structural_valid=True,
        release_verified=True,
        github_digest_state="verified",
    )

    def lookup(self, code: str) -> TariffRecord:
        if code == "bad":
            raise InvalidCodeError("internal parser details")
        if code == "99999999":
            raise RecordNotFoundError("internal database details")
        return _record(code)

    def ficha(self, code: str) -> Ficha:
        record = self.lookup(code)
        return Ficha(
            record=record,
            formatted_code="01.01.21.01.00",
            section=None,
            hierarchy=(record,),
            children=(),
        )

    def parent(self, code: str) -> TariffRecord | None:
        if code == "01":
            return None
        return TariffRecord(
            **{
                **_record().__dict__,
            }
        ) if hasattr(_record(), "__dict__") else TariffRecord(
            code="01012101",
            level="fraccion8",
            description="Reproductores de raza pura.",
            unit_name="Cbza",
            igi_text="Ex.",
            igi_kind="exento",
            igi_value=None,
            ige_text="Prohibida",
            ige_kind="prohibida",
            ige_value=None,
            parent_code="010121",
            dataset_version="2026.08.15",
            schema_version="2",
            effective_from=date(2026, 1, 1),
            effective_to=None,
            is_current=True,
            hs2="01",
            hs4="0101",
            hs6="010121",
            fraccion8="01012101",
        )

    def children(self, code: str) -> tuple[TariffRecord, ...]:
        return (_record(),) if code == "01012101" else ()

    def provenance(self, code: str) -> tuple[ProvenanceRecord, ...]:
        return (
            ProvenanceRecord(
                source_document_id="dof-primary",
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
            ),
            ProvenanceRecord(
                source_document_id="snice-operational",
                role="operational_structure",
                is_primary=False,
                authority="SNICE",
                publication_venue="SNICE",
                title="LIGIE estructurada",
                source_url="https://www.snice.gob.mx/example",
                sha256="b" * 64,
                published_at=date(2026, 8, 10),
                effective_from=None,
                effective_to=None,
            ),
        )


def _client(valid_settings) -> TestClient:
    dataset = LookupDataset()
    return TestClient(
        create_app(settings=valid_settings, dataset_loader=lambda settings: dataset)
    )


def test_lookup_preserves_nico_strings_without_exposing_rates(valid_settings) -> None:
    with _client(valid_settings) as client:
        response = client.get("/v1/lookup/0101210100")

    assert response.status_code == 200
    payload = response.json()
    assert payload["code"] == "0101210100"
    assert payload["parent_code"] == "01012101"
    assert payload["hierarchy"]["nico2"] == "00"
    assert payload["hierarchy"]["fraccion8"] == "01012101"
    assert payload["igi"] is None
    assert payload["ige"] is None


def test_ficha_uses_existing_consumer_hierarchy(valid_settings) -> None:
    with _client(valid_settings) as client:
        response = client.get("/v1/ficha/0101210100")

    assert response.status_code == 200
    payload = response.json()
    assert payload["formatted_code"] == "01.01.21.01.00"
    assert payload["record"]["code"] == "0101210100"
    assert payload["hierarchy"][0]["code"] == "0101210100"


def test_parent_returns_null_for_hs2_and_mx8_for_nico(valid_settings) -> None:
    with _client(valid_settings) as client:
        root = client.get("/v1/codes/01/parent")
        nico = client.get("/v1/codes/0101210100/parent")

    assert root.status_code == 200
    assert root.json() is None
    assert nico.status_code == 200
    assert nico.json()["code"] == "01012101"
    assert nico.json()["level"] == "fraccion8"


def test_children_return_direct_current_rows(valid_settings) -> None:
    with _client(valid_settings) as client:
        response = client.get("/v1/codes/01012101/children")

    assert response.status_code == 200
    assert [row["code"] for row in response.json()] == ["0101210100"]


def test_provenance_preserves_consumer_order(valid_settings) -> None:
    with _client(valid_settings) as client:
        response = client.get("/v1/codes/0101210100/provenance")

    assert response.status_code == 200
    payload = response.json()
    assert [row["source_document_id"] for row in payload] == [
        "dof-primary",
        "snice-operational",
    ]
    assert payload[0]["is_primary"] is True


def test_lookup_maps_invalid_and_missing_codes_without_internal_details(valid_settings) -> None:
    with _client(valid_settings) as client:
        invalid = client.get("/v1/lookup/bad")
        missing = client.get("/v1/lookup/99999999")

    assert invalid.status_code == 400
    assert invalid.json()["error"]["code"] == "invalid_code"
    assert "internal" not in invalid.text.lower()
    assert missing.status_code == 404
    assert missing.json()["error"]["code"] == "record_not_found"
    assert "database" not in missing.text.lower()
