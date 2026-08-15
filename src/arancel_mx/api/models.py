"""Versioned HTTP wire models for the public API."""

from __future__ import annotations

from pydantic import BaseModel, ConfigDict


class ErrorDetail(BaseModel):
    """Sanitized error details safe to expose to public clients."""

    model_config = ConfigDict(frozen=True)

    code: str
    message: str
    request_id: str


class ErrorEnvelope(BaseModel):
    """Stable top-level error response shared by handled API failures."""

    model_config = ConfigDict(frozen=True)

    error: ErrorDetail
