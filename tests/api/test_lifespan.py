from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from arancel_mx.api.app import create_app
from arancel_mx.consumer.errors import DatasetIntegrityError


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


def test_lifespan_fails_closed_when_dataset_verification_fails(
    valid_settings,
) -> None:
    def loader(settings):
        raise DatasetIntegrityError(f"invalid dataset: {settings.dataset_tag}")

    app = create_app(settings=valid_settings, dataset_loader=loader)

    with pytest.raises(DatasetIntegrityError, match="invalid dataset"):
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

    with pytest.raises(DatasetIntegrityError):
        with TestClient(app):
            pass

    messages = [record.getMessage() for record in caplog.records]
    assert (
        "dataset startup verification failed tag=data-2026.08.15 "
        "error_type=DatasetIntegrityError"
    ) in messages
    assert secret not in "\n".join(messages)
