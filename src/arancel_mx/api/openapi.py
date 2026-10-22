"""Reusable OpenAPI response contracts for the public v1 service."""

from __future__ import annotations

from typing import Any, Final

from arancel_mx.api.models import ErrorEnvelope


def _error(description: str) -> dict[str, Any]:
    return {"model": ErrorEnvelope, "description": description}


LOOKUP_ERROR_RESPONSES: Final[dict[int | str, dict[str, Any]]] = {
    400: _error("Invalid tariff code."),
    404: _error("Tariff record not found."),
    422: _error("Request validation failed."),
    503: _error("Verified dataset unavailable or inconsistent."),
    500: _error("Internal server error."),
}

RETRIEVAL_ERROR_RESPONSES: Final[dict[int | str, dict[str, Any]]] = {
    422: _error("Request validation failed."),
    503: _error("Verified dataset unavailable or inconsistent."),
    500: _error("Internal server error."),
}

META_ERROR_RESPONSES: Final[dict[int | str, dict[str, Any]]] = {
    503: _error("Verified dataset unavailable."),
    500: _error("Internal server error."),
}
