"""Service-level routes for the public HTTP API."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, Path, Query, Request

from arancel_mx import __version__
from arancel_mx.api import API_VERSION
from arancel_mx.api.dependencies import get_dataset
from arancel_mx.api.models import (
    FichaResponse,
    NationalNoteResponse,
    ProvenanceResponse,
    SearchResponse,
    SuggestResponse,
    TariffResponse,
)
from arancel_mx.consumer import Dataset


router = APIRouter()
DatasetDependency = Annotated[Dataset, Depends(get_dataset)]
SearchText = Annotated[str, Query(min_length=1, max_length=300)]
SearchLimit = Annotated[int, Query(ge=1, le=50)]
SuggestLimit = Annotated[int, Query(ge=1, le=20)]
ChapterPath = Annotated[str, Path(pattern=r"^\d{2}$")]


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
def metadata(
    request: Request,
    dataset: DatasetDependency,
) -> dict[str, str | bool | None]:
    """Expose independent API, package, and verified dataset identities."""

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


@router.get("/v1/lookup/{code}", response_model=TariffResponse, tags=["tariff"])
def lookup(code: str, dataset: DatasetDependency) -> TariffResponse:
    """Return one exact current tariff record from the verified dataset."""

    return TariffResponse.from_record(dataset.lookup(code))


@router.get("/v1/ficha/{code}", response_model=FichaResponse, tags=["tariff"])
def ficha(code: str, dataset: DatasetDependency) -> FichaResponse:
    """Return the existing verified hierarchy card for one code."""

    return FichaResponse.from_ficha(dataset.ficha(code))


@router.get("/v1/search", response_model=list[SearchResponse], tags=["retrieval"])
def search(
    q: SearchText,
    dataset: DatasetDependency,
    limit: SearchLimit = 20,
) -> list[SearchResponse]:
    """Return deterministic retrieve-only search results from verified data."""

    return [SearchResponse.from_result(result) for result in dataset.search(q, limit=limit)]


@router.get("/v1/suggest", response_model=list[SuggestResponse], tags=["retrieval"])
def suggest(
    q: SearchText,
    dataset: DatasetDependency,
    limit: SuggestLimit = 5,
) -> list[SuggestResponse]:
    """Return bounded evidence candidates without claiming classification."""

    return [SuggestResponse.from_hit(hit) for hit in dataset.suggest(q, limit=limit)]


@router.get("/v1/chapters", response_model=list[TariffResponse], tags=["hierarchy"])
def chapters(dataset: DatasetDependency) -> list[TariffResponse]:
    """Return current HS2 chapters from the verified dataset."""

    return [TariffResponse.from_record(record) for record in dataset.chapters()]


@router.get(
    "/v1/chapters/{chapter}/national-notes",
    response_model=list[NationalNoteResponse],
    tags=["legal-notes"],
)
def national_notes(
    chapter: ChapterPath,
    dataset: DatasetDependency,
) -> list[NationalNoteResponse]:
    """Return materialized official National Notes for one two-digit chapter."""

    return [
        NationalNoteResponse.from_note(note)
        for note in dataset.national_notes(chapter)
    ]


@router.get(
    "/v1/codes/{code}/parent",
    response_model=TariffResponse | None,
    tags=["hierarchy"],
)
def parent(code: str, dataset: DatasetDependency) -> TariffResponse | None:
    """Return the direct verified parent, or null for an HS2 chapter."""

    record = dataset.parent(code)
    return TariffResponse.from_record(record) if record is not None else None


@router.get(
    "/v1/codes/{code}/children",
    response_model=list[TariffResponse],
    tags=["hierarchy"],
)
def children(code: str, dataset: DatasetDependency) -> list[TariffResponse]:
    """Return direct current children from the verified hierarchy."""

    return [TariffResponse.from_record(record) for record in dataset.children(code)]


@router.get(
    "/v1/codes/{code}/provenance",
    response_model=list[ProvenanceResponse],
    tags=["provenance"],
)
def provenance(code: str, dataset: DatasetDependency) -> list[ProvenanceResponse]:
    """Return recorded source provenance in consumer-defined order."""

    return [
        ProvenanceResponse.from_record(record)
        for record in dataset.provenance(code)
    ]
