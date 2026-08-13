"""Immutable public models returned by the consumer API."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date
from typing import Literal


@dataclass(frozen=True, slots=True)
class TariffRecord:
    """Current public tariff row returned by ``Dataset.lookup``.

    JSON/wire aliases: ``fraction8`` ↔ ``fraccion8``, ``classification10`` ↔ ``nico10``.
    A 10-digit ``fraction`` field is invalid in downstream apps; this record uses
    ``fraccion8`` + ``nico2``.
    """

    code: str
    level: str
    description: str
    unit_name: str | None
    igi_text: str | None
    igi_kind: str | None
    igi_value: float | None
    ige_text: str | None
    ige_kind: str | None
    ige_value: float | None
    parent_code: str | None
    dataset_version: str
    schema_version: str
    effective_from: date | None
    effective_to: date | None
    is_current: bool
    hs2: str | None = None
    hs4: str | None = None
    hs6: str | None = None
    fraccion8: str | None = None
    nico2: str | None = None
    nico10: str | None = None
    ligie_version: str | None = None
    validity_basis: str | None = None


@dataclass(frozen=True, slots=True)
class SearchResult:
    record: TariffRecord
    score: int
    match_kind: Literal["exact_code", "code_prefix", "description"]


@dataclass(frozen=True, slots=True)
class ProvenanceRecord:
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


@dataclass(frozen=True, slots=True)
class HsSection:
    """HS/LIGIE section grouping derived from chapter number, not a captured source."""

    roman: str
    name: str
    chapter_from: str
    chapter_to: str
    source: Literal["hs_section_grouping"] = "hs_section_grouping"


@dataclass(frozen=True, slots=True)
class Ficha:
    """SIICEX-style tariff card built only from the verified official dataset."""

    record: TariffRecord
    formatted_code: str
    section: HsSection | None
    hierarchy: tuple[TariffRecord, ...]
    children: tuple[TariffRecord, ...]


@dataclass(frozen=True, slots=True)
class CompareRow:
    """One field compared between the GitHub/CLI dataset and a third-party page."""

    code: str
    level: str
    field: str
    dataset: str | None
    other: str | None
    other_source: str
    match: bool | None
    note: str = ""


@dataclass(frozen=True, slots=True)
class DatasetInfo:
    dataset_version: str | None
    schema_version: str | None
    path: str
    source: Literal["managed-cache", "local"]
    structural_valid: bool
    release_verified: bool
    github_digest_state: Literal["verified", "unavailable", "not_applicable"]
