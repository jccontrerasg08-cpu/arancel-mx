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
    assert "GET" in preflight.headers["access-control-allow-methods"]
    assert preflight.headers["x-request-id"]

    assert response.status_code == 200
    assert response.headers["access-control-allow-origin"] == "*"
    assert response.headers.get("access-control-allow-credentials") is None
    assert "x-request-id" in response.headers["access-control-expose-headers"].lower()
    assert response.headers["x-request-id"]
