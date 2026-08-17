"""Versioned HTTP wire models for the public API."""

from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, ConfigDict

from arancel_mx.consumer.models import (
    Ficha,
    HsSection,
    NationalNote,
    ProvenanceRecord,
    SearchResult,
    SuggestHit,
    TariffRecord,
)


class FrozenModel(BaseModel):
    """Shared immutable configuration for public wire contracts."""

    model_config = ConfigDict(frozen=True)


class ErrorDetail(FrozenModel):
    """Sanitized error details safe to expose to public clients."""

    code: str
    message: str
    request_id: str


class ErrorEnvelope(FrozenModel):
    """Stable top-level error response shared by handled API failures."""

    error: ErrorDetail


class HealthResponse(FrozenModel):
    """Process-liveness response."""

    status: Literal["ok"]


class ReadyResponse(FrozenModel):
    """Readiness response for a verified loaded dataset."""

    status: Literal["ready"]
    dataset_version: str


class NotReadyResponse(FrozenModel):
    """Readiness response while the verified dataset is unavailable."""

    status: Literal["not_ready"]


class MetaResponse(FrozenModel):
    """Independent API, package, and verified dataset identities."""

    api_version: str
    package_version: str
    dataset_tag: str
    dataset_version: str
    schema_version: str
    read_only: bool
    release_verified: bool
    structural_valid: bool


class RepositoryReleaseResponse(FrozenModel):
    """Public immutable-release reference from repository metadata."""

    tag: str
    publishedAt: str
    url: str


class RepositoryActivityResponse(FrozenModel):
    """Public issue or pull-request reference from repository metadata."""

    number: int
    title: str
    url: str
    updatedAt: str


class RepositoryPipelineResponse(FrozenModel):
    """Public workflow status reference from repository metadata."""

    status: str
    conclusion: str | None
    url: str


class RepositorySnapshotResponse(FrozenModel):
    """Bounded public repository telemetry for the marketing site."""

    stars: int
    observedAt: str
    releases: list[RepositoryReleaseResponse]
    recentPulls: list[RepositoryActivityResponse]
    recentIssues: list[RepositoryActivityResponse]
    pipeline: RepositoryPipelineResponse
    source: str


class RateResponse(FrozenModel):
    """Official tariff-rate representation without reinterpretation."""

    text: str | None
    kind: str | None
    value: float | None


class HierarchyResponse(FrozenModel):
    """Explicit HS/TIGIE/NICO hierarchy preserving string codes."""

    hs2: str | None
    hs4: str | None
    hs6: str | None
    fraccion8: str | None
    nico2: str | None
    nico10: str | None


class TariffResponse(FrozenModel):
    """Versioned HTTP representation of one verified tariff record."""

    code: str
    level: str
    description: str
    unit_name: str | None
    igi: RateResponse
    ige: RateResponse
    parent_code: str | None
    dataset_version: str
    schema_version: str
    effective_from: date | None
    effective_to: date | None
    is_current: bool
    hierarchy: HierarchyResponse
    ligie_version: str | None
    validity_basis: str | None

    @classmethod
    def from_record(cls, record: TariffRecord) -> TariffResponse:
        return cls(
            code=record.code,
            level=record.level,
            description=record.description,
            unit_name=record.unit_name,
            igi=RateResponse(
                text=record.igi_text,
                kind=record.igi_kind,
                value=record.igi_value,
            ),
            ige=RateResponse(
                text=record.ige_text,
                kind=record.ige_kind,
                value=record.ige_value,
            ),
            parent_code=record.parent_code,
            dataset_version=record.dataset_version,
            schema_version=record.schema_version,
            effective_from=record.effective_from,
            effective_to=record.effective_to,
            is_current=record.is_current,
            hierarchy=HierarchyResponse(
                hs2=record.hs2,
                hs4=record.hs4,
                hs6=record.hs6,
                fraccion8=record.fraccion8,
                nico2=record.nico2,
                nico10=record.nico10,
            ),
            ligie_version=record.ligie_version,
            validity_basis=record.validity_basis,
        )


class SectionResponse(FrozenModel):
    """Derived HS section grouping used by ficha responses."""

    roman: str
    name: str
    chapter_from: str
    chapter_to: str
    source: str

    @classmethod
    def from_section(cls, section: HsSection) -> SectionResponse:
        return cls(
            roman=section.roman,
            name=section.name,
            chapter_from=section.chapter_from,
            chapter_to=section.chapter_to,
            source=section.source,
        )


class FichaResponse(FrozenModel):
    """HTTP hierarchy card built from the verified consumer facade."""

    record: TariffResponse
    formatted_code: str
    section: SectionResponse | None
    hierarchy: list[TariffResponse]
    children: list[TariffResponse]

    @classmethod
    def from_ficha(cls, ficha: Ficha) -> FichaResponse:
        return cls(
            record=TariffResponse.from_record(ficha.record),
            formatted_code=ficha.formatted_code,
            section=(
                SectionResponse.from_section(ficha.section)
                if ficha.section is not None
                else None
            ),
            hierarchy=[TariffResponse.from_record(item) for item in ficha.hierarchy],
            children=[TariffResponse.from_record(item) for item in ficha.children],
        )


class ProvenanceResponse(FrozenModel):
    """Recorded source provenance for one tariff record."""

    source_document_id: str
    role: str
    is_primary: bool
    authority: str
    publication_venue: str
    title: str
    source_url: str
    sha256: str
    published_at: date | None
    effective_from: date | None
    effective_to: date | None

    @classmethod
    def from_record(cls, record: ProvenanceRecord) -> ProvenanceResponse:
        return cls(**record.__dict__) if hasattr(record, "__dict__") else cls(
            source_document_id=record.source_document_id,
            role=record.role,
            is_primary=record.is_primary,
            authority=record.authority,
            publication_venue=record.publication_venue,
            title=record.title,
            source_url=record.source_url,
            sha256=record.sha256,
            published_at=record.published_at,
            effective_from=record.effective_from,
            effective_to=record.effective_to,
        )


class SearchResponse(FrozenModel):
    """Deterministic retrieval result including ranking metadata."""

    record: TariffResponse
    score: int
    match_kind: str
    scorer_version: str
    confidence: float

    @classmethod
    def from_result(cls, result: SearchResult) -> SearchResponse:
        return cls(
            record=TariffResponse.from_record(result.record),
            score=result.score,
            match_kind=result.match_kind,
            scorer_version=result.scorer_version,
            confidence=result.confidence,
        )


class NationalNoteResponse(FrozenModel):
    """One materialized official National Note with preserved applicability."""

    chapter: str
    note_number: str
    text: str
    source_document_id: str
    scope_type: str | None
    scope_value: str | None
    applicability_basis: str

    @classmethod
    def from_note(cls, note: NationalNote) -> NationalNoteResponse:
        return cls(
            chapter=note.chapter,
            note_number=note.note_number,
            text=note.text,
            source_document_id=note.source_document_id,
            scope_type=note.scope_type,
            scope_value=note.scope_value,
            applicability_basis=note.applicability_basis,
        )


class SuggestResponse(FrozenModel):
    """Retrieve-only suggestion hit that preserves its disclaimer."""

    search: SearchResponse
    ficha: FichaResponse
    national_notes: list[NationalNoteResponse]
    disclaimer: str

    @classmethod
    def from_hit(cls, hit: SuggestHit) -> SuggestResponse:
        return cls(
            search=SearchResponse.from_result(hit.search),
            ficha=FichaResponse.from_ficha(hit.ficha),
            national_notes=[NationalNoteResponse.from_note(note) for note in hit.national_notes],
            disclaimer=hit.disclaimer,
        )
