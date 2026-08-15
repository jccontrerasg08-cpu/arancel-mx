from __future__ import annotations

from fastapi.testclient import TestClient

from arancel_mx.api.app import create_app


def _app(valid_settings, fake_dataset):
    return create_app(
        settings=valid_settings,
        dataset_loader=lambda settings: fake_dataset,
    )


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


def test_openapi_keeps_interactive_documentation_enabled(valid_settings, fake_dataset) -> None:
    application = _app(valid_settings, fake_dataset)
    with TestClient(application) as client:
        docs = client.get("/docs")
        redoc = client.get("/redoc")

    assert docs.status_code == 200
    assert redoc.status_code == 200


def test_module_import_does_not_require_dataset_environment(monkeypatch) -> None:
    monkeypatch.delenv("ARANCEL_MX_API_DATASET", raising=False)

    from arancel_mx.api.app import app

    assert app.title == "Arancel MX API"
