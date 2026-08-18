from __future__ import annotations

import re

from fastapi.testclient import TestClient

from arancel_mx.api.app import create_app


def _client(valid_settings, fake_dataset) -> TestClient:
    return TestClient(
        create_app(
            settings=valid_settings,
            dataset_loader=lambda settings: fake_dataset,
        )
    )


def test_root_serves_the_public_marketing_site(valid_settings, fake_dataset) -> None:
    with _client(valid_settings, fake_dataset) as client:
        response = client.get("/")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert '<div id="root"></div>' in response.text
    asset = re.search(r'(/assets/index-[^"]+\.js)', response.text)
    assert asset is not None
    with _client(valid_settings, fake_dataset) as client:
        asset_response = client.get(asset.group(1))
    assert asset_response.status_code == 200
    assert "javascript" in asset_response.headers["content-type"]


def test_v1_describes_public_api(valid_settings, fake_dataset) -> None:
    with _client(valid_settings, fake_dataset) as client:
        response = client.get("/v1")

    assert response.status_code == 200
    assert response.json() == {
        "name": "arancel-mx",
        "api_version": "1",
        "docs": "/docs",
        "openapi": "/openapi.json",
        "meta": "/v1/meta",
    }


def test_healthz_reports_process_health(valid_settings, fake_dataset) -> None:
    with _client(valid_settings, fake_dataset) as client:
        response = client.get("/healthz")

    assert response.status_code == 200
    assert response.json() == {"status": "ok"}


def test_readyz_reports_verified_dataset_version(valid_settings, fake_dataset) -> None:
    with _client(valid_settings, fake_dataset) as client:
        response = client.get("/readyz")

    assert response.status_code == 200
    assert response.json() == {
        "status": "ready",
        "dataset_version": "2026.08.15",
    }


def test_meta_keeps_api_package_and_dataset_versions_separate(
    valid_settings,
    fake_dataset,
) -> None:
    with _client(valid_settings, fake_dataset) as client:
        response = client.get("/v1/meta")

    assert response.status_code == 200
    assert response.json() == {
        "api_version": "1",
        "package_version": "0.3.3",
        "dataset_tag": "data-2026.08.15",
        "dataset_version": "2026.08.15",
        "schema_version": "2",
        "read_only": True,
        "release_verified": True,
        "structural_valid": True,
    }


def test_repository_snapshot_uses_documented_fallback_without_token(
    valid_settings,
    fake_dataset,
    monkeypatch,
) -> None:
    import arancel_mx.api.repository as repository

    monkeypatch.setattr(
        repository.requests,
        "get",
        lambda *args, **kwargs: (_ for _ in ()).throw(
            AssertionError("no network without token")
        ),
    )
    with _client(valid_settings, fake_dataset) as client:
        response = client.get("/v1/repository")

    assert response.status_code == 200
    assert response.json()["source"] == "snapshot"
    assert response.json()["pipeline"]["conclusion"] == "success"


def test_request_id_is_generated_and_returned(valid_settings, fake_dataset) -> None:
    with _client(valid_settings, fake_dataset) as client:
        response = client.get("/healthz")

    request_id = response.headers["x-request-id"]
    assert len(request_id) == 32
    assert request_id.isascii()
    assert request_id.isalnum()


def test_incoming_request_id_cannot_spoof_server_identity(
    valid_settings,
    fake_dataset,
) -> None:
    incoming = "client-req-123"
    with _client(valid_settings, fake_dataset) as client:
        first = client.get("/healthz", headers={"X-Request-ID": incoming})
        second = client.get("/healthz", headers={"X-Request-ID": incoming})

    first_id = first.headers["x-request-id"]
    second_id = second.headers["x-request-id"]
    assert first_id != incoming
    assert second_id != incoming
    assert first_id != second_id
    assert len(first_id) == 32
    assert len(second_id) == 32
    assert first_id.isalnum()
    assert second_id.isalnum()


def test_overlong_request_id_is_replaced(valid_settings, fake_dataset) -> None:
    incoming = "x" * 129
    with _client(valid_settings, fake_dataset) as client:
        response = client.get("/healthz", headers={"X-Request-ID": incoming})

    assert response.headers["x-request-id"] != incoming
    assert len(response.headers["x-request-id"]) == 32


def test_public_cors_allows_get_without_credentials(valid_settings, fake_dataset) -> None:
    with _client(valid_settings, fake_dataset) as client:
        preflight = client.options(
            "/v1/meta",
            headers={
                "Origin": "https://example.com",
                "Access-Control-Request-Method": "GET",
            },
        )
        response = client.get(
            "/v1/meta",
            headers={"Origin": "https://example.com"},
        )

    assert preflight.status_code == 200
    assert preflight.headers["access-control-allow-origin"] == "*"
    assert preflight.headers.get("access-control-allow-credentials") is None
    allowed_methods = {
        method.strip()
        for method in preflight.headers["access-control-allow-methods"].split(",")
    }
    assert "GET" in allowed_methods
    assert allowed_methods <= {"GET", "OPTIONS"}
    assert preflight.headers["x-request-id"]

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "*"
    assert response.headers.get("access-control-allow-credentials") is None
    assert "x-request-id" in response.headers["access-control-expose-headers"].lower()
    assert response.headers["x-request-id"]


def test_explorer_serves_the_public_search_page(valid_settings, fake_dataset) -> None:
    with _client(valid_settings, fake_dataset) as client:
        response = client.get("/app")

    assert response.status_code == 200
    assert response.headers["content-type"].startswith("text/html")
    assert 'data-testid="search-input"' in response.text
    assert 'data-testid="search-submit"' in response.text
    assert "No clasifica mercancías" in response.text


def test_marketing_documentation_route_preserves_fastapi_docs(valid_settings, fake_dataset) -> None:
    with _client(valid_settings, fake_dataset) as client:
        marketing = client.get("/documentation")
        api_docs = client.get("/docs")

    assert marketing.status_code == 200
    assert '<div id="root"></div>' in marketing.text
    assert api_docs.status_code == 200
    assert "Swagger UI" in api_docs.text


def test_new_marketing_deep_links_serve_the_public_shell(valid_settings, fake_dataset) -> None:
    with _client(valid_settings, fake_dataset) as client:
        responses = [
            client.get(path)
            for path in ("/records", "/chapters", "/changes", "/moa", "/trade-context")
        ]

    assert all(response.status_code == 200 for response in responses)
    assert all('<div id="root"></div>' in response.text for response in responses)


def test_vercel_entrypoint_resolves_the_public_application() -> None:
    from src.arancel_mx.api.app import app as vercel_app

    assert vercel_app.title == "Arancel MX API"


def test_explorer_serves_durable_client_routes(valid_settings, fake_dataset) -> None:
    with _client(valid_settings, fake_dataset) as client:
        record = client.get("/app/record/85171301")
        chapter = client.get("/app/chapter/85")

    assert record.status_code == 200
    assert chapter.status_code == 200
    assert 'data-testid="snapshot-list"' in record.text
    assert "Guardar ficha local" in record.text
    assert "Vigencia y evidencia registrada" in record.text
