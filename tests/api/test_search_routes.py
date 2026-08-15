from __future__ import annotations

from fastapi.testclient import TestClient

from arancel_mx.api.app import create_app
from arancel_mx.consumer.models import DatasetInfo, Ficha, SearchResult, SuggestHit, TariffRecord


def _record() -> TariffRecord:
    return TariffRecord(
        code="85171301",
        level="fraccion8",
        description="Teléfonos inteligentes.",
        unit_name="Pza",
        igi_text="Ex.",
        igi_kind="exento",
        igi_value=None,
        ige_text="Ex.",
        ige_kind="exento",
        ige_value=None,
        parent_code="851713",
        dataset_version="2026.08.15",
        schema_version="2",
        effective_from=None,
        effective_to=None,
        is_current=True,
        hs2="85",
        hs4="8517",
        hs6="851713",
        fraccion8="85171301",
    )


class SearchDataset:
    info = DatasetInfo(
        dataset_version="2026.08.15",
        schema_version="2",
        path="/verified/arancel_mx.duckdb",
        source="managed-cache",
        structural_valid=True,
        release_verified=True,
        github_digest_state="verified",
    )

    def search(self, text: str, *, limit: int = 20) -> tuple[SearchResult, ...]:
        assert text == "telefonos"
        assert limit == 7
        return (
            SearchResult(
                record=_record(),
                score=910,
                match_kind="description",
                scorer_version="1",
                confidence=0.91,
            ),
        )

    def suggest(self, text: str, *, limit: int = 5) -> tuple[SuggestHit, ...]:
        assert text == "telefonos"
        assert limit == 3
        search = SearchResult(
            record=_record(),
            score=910,
            match_kind="description",
            scorer_version="1",
            confidence=0.91,
        )
        return (
            SuggestHit(
                search=search,
                ficha=Ficha(
                    record=_record(),
                    formatted_code="85.17.13.01",
                    section=None,
                    hierarchy=(_record(),),
                    children=(),
                ),
                national_notes=(),
                disclaimer="Retrieve-only: no afirma una clasificación arancelaria.",
            ),
        )


def _client(valid_settings) -> TestClient:
    dataset = SearchDataset()
    return TestClient(
        create_app(settings=valid_settings, dataset_loader=lambda settings: dataset)
    )


def test_search_serializes_deterministic_ranking_metadata(valid_settings) -> None:
    with _client(valid_settings) as client:
        response = client.get("/v1/search", params={"q": "telefonos", "limit": 7})

    assert response.status_code == 200
    payload = response.json()
    assert payload[0]["record"]["code"] == "85171301"
    assert payload[0]["score"] == 910
    assert payload[0]["match_kind"] == "description"
    assert payload[0]["scorer_version"] == "1"
    assert payload[0]["confidence"] == 0.91


def test_suggest_preserves_retrieve_only_disclaimer(valid_settings) -> None:
    with _client(valid_settings) as client:
        response = client.get("/v1/suggest", params={"q": "telefonos", "limit": 3})

    assert response.status_code == 200
    payload = response.json()
    assert payload[0]["search"]["record"]["code"] == "85171301"
    assert payload[0]["ficha"]["record"]["code"] == "85171301"
    assert payload[0]["disclaimer"] == "Retrieve-only: no afirma una clasificación arancelaria."


def test_search_rejects_empty_or_oversized_queries_and_limits(valid_settings) -> None:
    with _client(valid_settings) as client:
        responses = (
            client.get("/v1/search", params={"q": "", "limit": 20}),
            client.get("/v1/search", params={"q": "x" * 301, "limit": 20}),
            client.get("/v1/search", params={"q": "x", "limit": 0}),
            client.get("/v1/search", params={"q": "x", "limit": 51}),
        )

    assert {response.status_code for response in responses} == {422}
    assert {response.json()["error"]["code"] for response in responses} == {
        "validation_error"
    }


def test_suggest_rejects_empty_or_oversized_queries_and_limits(valid_settings) -> None:
    with _client(valid_settings) as client:
        responses = (
            client.get("/v1/suggest", params={"q": "", "limit": 5}),
            client.get("/v1/suggest", params={"q": "x" * 301, "limit": 5}),
            client.get("/v1/suggest", params={"q": "x", "limit": 0}),
            client.get("/v1/suggest", params={"q": "x", "limit": 21}),
        )

    assert {response.status_code for response in responses} == {422}
    assert {response.json()["error"]["code"] for response in responses} == {
        "validation_error"
    }
