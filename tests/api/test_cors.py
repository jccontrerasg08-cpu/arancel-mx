from dataclasses import replace

from fastapi.testclient import TestClient

from arancel_mx.api.app import create_app


def test_settings_default_to_no_cross_origin_origins() -> None:
    from arancel_mx.api.config import load_settings

    settings = load_settings({"ARANCEL_MX_API_DATASET": "data-2026.08.15"})

    assert settings.cors_origins == ()


def test_api_does_not_emit_cors_headers_without_an_explicit_allowlist(
    valid_settings, fake_dataset
) -> None:
    app = create_app(
        settings=valid_settings,
        dataset_loader=lambda settings: fake_dataset,
    )

    with TestClient(app) as client:
        response = client.get("/v1/meta", headers={"Origin": "https://untrusted.example"})

    assert response.status_code == 200
    assert "access-control-allow-origin" not in response.headers


def test_api_allows_only_declared_https_origins(valid_settings, fake_dataset) -> None:
    settings = replace(
        valid_settings,
        cors_origins=("https://portal.example",),
    )
    app = create_app(
        settings=settings,
        dataset_loader=lambda settings: fake_dataset,
    )

    with TestClient(app) as client:
        allowed = client.get("/v1/meta", headers={"Origin": "https://portal.example"})
        rejected = client.get("/v1/meta", headers={"Origin": "https://untrusted.example"})

    assert allowed.headers["access-control-allow-origin"] == "https://portal.example"
    assert "access-control-allow-origin" not in rejected.headers


import pytest


@pytest.mark.parametrize(
    "origins",
    ["*", "http://portal.example", "https://portal.example/path", "https://"],
)
def test_settings_reject_non_origin_or_non_https_cors_values(origins: str) -> None:
    from arancel_mx.api.config import load_settings

    with pytest.raises(ValueError, match="ARANCEL_MX_API_CORS_ORIGINS"):
        load_settings(
            {
                "ARANCEL_MX_API_DATASET": "data-2026.08.15",
                "ARANCEL_MX_API_CORS_ORIGINS": origins,
            }
        )


def test_cors_preflight_allows_only_declared_get_origin(valid_settings, fake_dataset) -> None:
    settings = replace(valid_settings, cors_origins=("https://portal.example",))
    app = create_app(
        settings=settings,
        dataset_loader=lambda settings: fake_dataset,
    )

    with TestClient(app) as client:
        allowed = client.options(
            "/v1/meta",
            headers={
                "Origin": "https://portal.example",
                "Access-Control-Request-Method": "GET",
                "Access-Control-Request-Headers": "X-Request-ID",
            },
        )
        rejected = client.options(
            "/v1/meta",
            headers={
                "Origin": "https://untrusted.example",
                "Access-Control-Request-Method": "GET",
            },
        )

    assert allowed.status_code == 204
    assert allowed.headers["access-control-allow-origin"] == "https://portal.example"
    assert allowed.headers["access-control-allow-methods"] == "GET, OPTIONS"
    assert "access-control-allow-origin" not in rejected.headers
