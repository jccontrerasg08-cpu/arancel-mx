from __future__ import annotations

from typing import Annotated

from fastapi import Query
from fastapi.testclient import TestClient

from arancel_mx.api.app import create_app
from arancel_mx.consumer.errors import (
    DatasetIntegrityError,
    InvalidCodeError,
    QueryError,
    RecordNotFoundError,
)


def _app_with_failure_route(valid_settings, fake_dataset, exc: Exception):
    app = create_app(
        settings=valid_settings,
        dataset_loader=lambda settings: fake_dataset,
    )

    @app.get("/_test/failure")
    def failure():
        raise exc

    return app


def _assert_error(response, *, status: int, code: str, message: str) -> None:
    assert response.status_code == status
    assert response.json() == {
        "error": {
            "code": code,
            "message": message,
            "request_id": "test-err-1",
        }
    }
    assert response.headers["x-request-id"] == "test-err-1"


def test_invalid_code_is_a_sanitized_400(valid_settings, fake_dataset) -> None:
    app = _app_with_failure_route(
        valid_settings,
        fake_dataset,
        InvalidCodeError("private raw code: C:/secret/input"),
    )
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/_test/failure", headers={"X-Request-ID": "test-err-1"})

    _assert_error(
        response,
        status=400,
        code="invalid_code",
        message="Invalid tariff code.",
    )


def test_missing_record_is_a_sanitized_404(valid_settings, fake_dataset) -> None:
    app = _app_with_failure_route(
        valid_settings,
        fake_dataset,
        RecordNotFoundError("missing 12345678 in /private/cache.duckdb"),
    )
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/_test/failure", headers={"X-Request-ID": "test-err-1"})

    _assert_error(
        response,
        status=404,
        code="record_not_found",
        message="Tariff record not found.",
    )


def test_internal_query_inconsistency_is_a_sanitized_503(
    valid_settings,
    fake_dataset,
) -> None:
    app = _app_with_failure_route(
        valid_settings,
        fake_dataset,
        QueryError("multiple current rows: SELECT * FROM private_table"),
    )
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/_test/failure", headers={"X-Request-ID": "test-err-1"})

    _assert_error(
        response,
        status=503,
        code="dataset_inconsistent",
        message="The verified dataset could not satisfy this query safely.",
    )


def test_dataset_failure_is_a_sanitized_503(valid_settings, fake_dataset) -> None:
    app = _app_with_failure_route(
        valid_settings,
        fake_dataset,
        DatasetIntegrityError("sha mismatch at /private/cache.duckdb"),
    )
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/_test/failure", headers={"X-Request-ID": "test-err-1"})

    _assert_error(
        response,
        status=503,
        code="dataset_unavailable",
        message="The verified dataset is unavailable.",
    )


def test_validation_error_uses_the_common_envelope(valid_settings, fake_dataset) -> None:
    app = create_app(
        settings=valid_settings,
        dataset_loader=lambda settings: fake_dataset,
    )

    @app.get("/_test/validation")
    def validation(limit: Annotated[int, Query(ge=1, le=10)]):
        return {"limit": limit}

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get(
            "/_test/validation?limit=0",
            headers={"X-Request-ID": "test-err-1"},
        )

    _assert_error(
        response,
        status=422,
        code="validation_error",
        message="Request validation failed.",
    )


def test_unknown_route_uses_the_common_envelope(valid_settings, fake_dataset) -> None:
    app = create_app(
        settings=valid_settings,
        dataset_loader=lambda settings: fake_dataset,
    )
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/does-not-exist", headers={"X-Request-ID": "test-err-1"})

    _assert_error(
        response,
        status=404,
        code="route_not_found",
        message="Route not found.",
    )


def test_method_not_allowed_uses_the_common_envelope(valid_settings, fake_dataset) -> None:
    app = create_app(
        settings=valid_settings,
        dataset_loader=lambda settings: fake_dataset,
    )
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.post("/v1/meta", headers={"X-Request-ID": "test-err-1"})

    _assert_error(
        response,
        status=405,
        code="method_not_allowed",
        message="Method not allowed.",
    )


def test_unexpected_exception_does_not_leak_internal_details(
    valid_settings,
    fake_dataset,
) -> None:
    secret = "C:/private/warehouse.db SELECT * FROM secrets"
    app = _app_with_failure_route(valid_settings, fake_dataset, RuntimeError(secret))
    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/_test/failure", headers={"X-Request-ID": "test-err-1"})

    _assert_error(
        response,
        status=500,
        code="internal_error",
        message="Internal server error.",
    )
    assert secret not in response.text


def test_unexpected_exception_log_contains_only_request_id_and_type(
    valid_settings,
    fake_dataset,
    caplog,
) -> None:
    secret = "C:/private/warehouse.db SELECT * FROM secrets"
    caplog.set_level("ERROR", logger="arancel_mx.api.app")
    app = _app_with_failure_route(valid_settings, fake_dataset, RuntimeError(secret))

    with TestClient(app, raise_server_exceptions=False) as client:
        response = client.get("/_test/failure", headers={"X-Request-ID": "test-err-1"})

    assert response.status_code == 500
    messages = [record.getMessage() for record in caplog.records]
    assert (
        "unhandled API exception request_id=test-err-1 error_type=RuntimeError"
        in messages
    )
    assert secret not in "\n".join(messages)
