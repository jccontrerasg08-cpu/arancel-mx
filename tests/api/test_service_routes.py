from __future__ import annotations

from fastapi.testclient import TestClient

from arancel_mx.api.app import create_app


def _client(valid_settings, fake_dataset) -> TestClient:
    return TestClient(
        create_app(
            settings=valid_settings,
            dataset_loader=lambda settings: fake_dataset,
        )
    )


def test_root_describes_public_api(valid_settings, fake_dataset) -> None:
    with _client(valid_settings, fake_dataset) as client:
        response = client.get("/")

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


def test_meta_keeps_api_package_and_dataset_versions_separate(
    valid_settings,
    fake_dataset,
) -> None:
    with _client(valid_settings, fake_dataset) as client:
        response = client.get("/v1/meta")

    assert response.status_code == 200
    assert response.json() == {
        "api_version": "1",
        "package_version": "0.2.1",
        "dataset_tag": "data-2026.08.15",
        "dataset_version": "2026.08.15",
        "schema_version": "2",
        "read_only": True,
        "release_verified": True,
        "structural_valid": True,
    }


def test_request_id_is_generated_and_returned(valid_settings, fake_dataset) -> None:
    with _client(valid_settings, fake_dataset) as client:
        response = client.get("/healthz")

    request_id = response.headers["x-request-id"]
    assert len(request_id) == 32
    assert request_id.isascii()
    assert request_id.isalnum()


def test_safe_request_id_is_propagated(valid_settings, fake_dataset) -> None:
    with _client(valid_settings, fake_dataset) as client:
        response = client.get("/healthz", headers={"X-Request-ID": "client-req-123"})

    assert response.headers["x-request-id"] == "client-req-123"


def test_overlong_request_id_is_replaced(valid_settings, fake_dataset) -> None:
    incoming = "x" * 129
    with _client(valid_settings, fake_dataset) as client:
        response = client.get("/healthz", headers={"X-Request-ID": incoming})

    assert response.headers["x-request-id"] != incoming
    assert len(response.headers["x-request-id"]) == 32


def test_public_cors_allows_get_without_credentials(valid_settings, fake_dataset) -> None:
    with _client(valid_settings, fake_dataset) as client:
        response = client.options(
            "/v1/meta",
            headers={
                "Origin": "https://example.com",
                "Access-Control-Request-Method": "GET",
            },
        )

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "*"
    assert response.headers.get("access-control-allow-credentials") is None
    assert "GET" in response.headers["access-control-allow-methods"]
    assert "x-request-id" in response.headers["access-control-expose-headers"].lower()
    assert response.headers["x-request-id"]
