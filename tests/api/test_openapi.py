from __future__ import annotations

import importlib

from fastapi.testclient import TestClient

from arancel_mx.api.app import create_app


def _app(valid_settings, fake_dataset):
    return create_app(
        settings=valid_settings,
        dataset_loader=lambda settings: fake_dataset,
    )


def _json_schema(response_spec: dict) -> dict:
    return response_spec["content"]["application/json"]["schema"]


def test_application_defines_no_mutation_routes(valid_settings, fake_dataset) -> None:
    application = _app(valid_settings, fake_dataset)
    forbidden = {"POST", "PUT", "PATCH", "DELETE"}

    for route in application.routes:
        methods = set(getattr(route, "methods", set()) or set())
        assert not (methods & forbidden), (route.path, methods)


def test_openapi_documents_version_and_non_classification_boundary(
    valid_settings,
    fake_dataset,
) -> None:
    application = _app(valid_settings, fake_dataset)
    with TestClient(application) as client:
        response = client.get("/openapi.json")

    assert response.status_code == 200
    payload = response.json()
    assert payload["info"]["title"] == "Arancel MX API"
    description = payload["info"]["description"].lower()
    assert "/v1" in description
    assert "legal advice" in description or "asesoría legal" in description
    assert "does not classify" in description or "no clasifica" in description


def test_openapi_exposes_typed_metadata_contract(valid_settings, fake_dataset) -> None:
    application = _app(valid_settings, fake_dataset)
    with TestClient(application) as client:
        payload = client.get("/openapi.json").json()

    schemas = payload["components"]["schemas"]
    assert "MetaResponse" in schemas
    meta_schema = payload["paths"]["/v1/meta"]["get"]["responses"]["200"]["content"][
        "application/json"
    ]["schema"]
    assert meta_schema == {"$ref": "#/components/schemas/MetaResponse"}


def test_openapi_documents_sanitized_error_envelope(
    valid_settings,
    fake_dataset,
) -> None:
    application = _app(valid_settings, fake_dataset)
    with TestClient(application) as client:
        payload = client.get("/openapi.json").json()

    assert "ErrorEnvelope" in payload["components"]["schemas"]
    lookup = payload["paths"]["/v1/lookup/{code}"]["get"]["responses"]
    for status in ("400", "404", "422", "503", "500"):
        assert _json_schema(lookup[status]) == {
            "$ref": "#/components/schemas/ErrorEnvelope"
        }
    search = payload["paths"]["/v1/search"]["get"]["responses"]
    for status in ("422", "503", "500"):
        assert _json_schema(search[status]) == {
            "$ref": "#/components/schemas/ErrorEnvelope"
        }


def test_openapi_types_health_and_readiness(valid_settings, fake_dataset) -> None:
    application = _app(valid_settings, fake_dataset)
    with TestClient(application) as client:
        payload = client.get("/openapi.json").json()

    health = payload["paths"]["/healthz"]["get"]["responses"]
    ready = payload["paths"]["/readyz"]["get"]["responses"]
    assert _json_schema(health["200"]) == {
        "$ref": "#/components/schemas/HealthResponse"
    }
    assert _json_schema(ready["200"]) == {
        "$ref": "#/components/schemas/ReadyResponse"
    }
    assert _json_schema(ready["503"]) == {
        "$ref": "#/components/schemas/NotReadyResponse"
    }


def test_openapi_keeps_interactive_documentation_enabled(valid_settings, fake_dataset) -> None:
    application = _app(valid_settings, fake_dataset)
    with TestClient(application) as client:
        docs = client.get("/docs")
        redoc = client.get("/redoc")

    assert docs.status_code == 200
    assert redoc.status_code == 200


def test_module_import_does_not_require_dataset_environment(monkeypatch) -> None:
    monkeypatch.delenv("ARANCEL_MX_API_DATASET", raising=False)

    module = importlib.import_module("arancel_mx.api.app")
    reloaded = importlib.reload(module)

    assert reloaded.app.title == "Arancel MX API"
