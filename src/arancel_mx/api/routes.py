"""Service-level routes for the public HTTP API."""

from __future__ import annotations

from fastapi import APIRouter, Request

from arancel_mx import __version__
from arancel_mx.api import API_VERSION


router = APIRouter()


@router.get("/")
def root() -> dict[str, str]:
    """Describe the public service and its discovery endpoints."""

    return {
        "name": "arancel-mx",
        "api_version": API_VERSION,
        "docs": "/docs",
        "openapi": "/openapi.json",
        "meta": "/v1/meta",
    }


@router.get("/healthz")
def healthz() -> dict[str, str]:
    """Report process liveness without re-querying the dataset."""

    return {"status": "ok"}


@router.get("/v1/meta")
def metadata(request: Request) -> dict[str, str | bool | None]:
    """Expose independent API, package, and verified dataset identities."""

    dataset = request.app.state.dataset
    settings = request.app.state.settings
    info = dataset.info
    return {
        "api_version": API_VERSION,
        "package_version": __version__,
        "dataset_tag": settings.dataset_tag,
        "dataset_version": info.dataset_version,
        "schema_version": info.schema_version,
        "read_only": True,
        "release_verified": info.release_verified,
        "structural_valid": info.structural_valid,
    }
