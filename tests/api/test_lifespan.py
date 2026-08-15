from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from arancel_mx.api.app import create_app
from arancel_mx.consumer.errors import DatasetIntegrityError


def _assert_degraded_service(client: TestClient) -> None:
    health = client.get("/healthz")
    ready = client.get("/readyz")
    meta = client.get("/v1/meta")

    assert health.status_code == 200
    assert health.json() == {"status": "ok"}
    assert ready.status_code == 503
    assert ready.json() == {"status": "not_ready"}
    assert meta.status_code == 503
    assert meta.json()["error"]["code"] == "dataset_unavailable"
    assert meta.json()["error"]["message"] == "The verified dataset is unavailable."
    assert meta.json()["error"]["request_id"] == meta.headers["x-request-id"]


def test_lifespan_loads_verified_dataset_once(valid_settings, fake_dataset) -> None:
    calls: list[str] = []

    def loader(settings):
        calls.append(settings.dataset_tag)
        return fake_dataset

    app = create_app(settings=valid_settings, dataset_loader=loader)

    with TestClient(app) as client:
        response = client.get("/readyz")
        assert response.status_code == 200
        assert response.json() == {
            "status": "ready",
            "dataset_version": "2026.08.15",
        }
        assert calls == ["data-2026.08.15"]
        assert app.state.dataset is fake_dataset
        assert app.state.ready is True

    assert app.state.ready is False


def test_dataset_verification_failure_yields_degraded_service(valid_settings) -> None:
    def loader(settings):
        raise DatasetIntegrityError(f"invalid dataset: {settings.dataset_tag}")

    app = create_app(settings=valid_settings, dataset_loader=loader)

    with TestClient(app) as client:
        _assert_degraded_service(client)
        assert app.state.dataset is None
        assert app.state.ready is False
        assert app.state.startup_error == "DatasetIntegrityError"


def test_missing_dataset_configuration_yields_degraded_service(
    monkeypatch,
    fake_dataset,
) -> None:
    monkeypatch.delenv("ARANCEL_MX_API_DATASET", raising=False)
    calls = 0

    def loader(settings):
        nonlocal calls
        calls += 1
        return fake_dataset

    app = create_app(dataset_loader=loader)

    with TestClient(app) as client:
        _assert_degraded_service(client)
        assert app.state.dataset is None
        assert app.state.settings is None
        assert app.state.ready is False
        assert app.state.startup_error == "ValueError"

    assert calls == 0


def test_unexpected_loader_failure_still_aborts_startup(valid_settings) -> None:
    def loader(settings):
        raise RuntimeError("programming defect")

    app = create_app(settings=valid_settings, dataset_loader=loader)

    with pytest.raises(RuntimeError, match="programming defect"):
        with TestClient(app):
            pass

    assert app.state.ready is False


def test_create_app_does_not_load_dataset_before_lifespan(
    valid_settings,
    fake_dataset,
) -> None:
    calls = 0

    def loader(settings):
        nonlocal calls
        calls += 1
        return fake_dataset

    app = create_app(settings=valid_settings, dataset_loader=loader)

    assert calls == 0
    assert app.state.ready is False


def test_lifespan_logs_verified_dataset_identity_without_local_path(
    valid_settings,
    fake_dataset,
    caplog,
) -> None:
    caplog.set_level("INFO", logger="arancel_mx.api.app")
    app = create_app(
        settings=valid_settings,
        dataset_loader=lambda settings: fake_dataset,
    )

    with TestClient(app):
        pass

    messages = [record.getMessage() for record in caplog.records]
    assert "loading verified dataset tag=data-2026.08.15" in messages
    assert (
        "verified dataset ready tag=data-2026.08.15 "
        "dataset_version=2026.08.15 schema_version=2"
    ) in messages
    assert "/verified/arancel_mx.duckdb" not in "\n".join(messages)


def test_lifespan_logs_failure_type_without_exception_payload(
    valid_settings,
    caplog,
) -> None:
    secret = "C:/private/cache/arancel_mx.duckdb"
    caplog.set_level("ERROR", logger="arancel_mx.api.app")

    def loader(settings):
        raise DatasetIntegrityError(f"sha mismatch at {secret}")

    app = create_app(settings=valid_settings, dataset_loader=loader)

    with TestClient(app) as client:
        assert client.get("/readyz").status_code == 503

    messages = [record.getMessage() for record in caplog.records]
    assert (
        "dataset startup verification failed tag=data-2026.08.15 "
        "error_type=DatasetIntegrityError"
    ) in messages
    assert secret not in "\n".join(messages)
