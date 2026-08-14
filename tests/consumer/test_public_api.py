from dataclasses import FrozenInstanceError
from datetime import date
from importlib.metadata import version

import pytest

import arancel_mx
from arancel_mx.consumer import Dataset as ConsumerDataset
from arancel_mx.consumer.errors import (
    ArancelMXError,
    DatasetDownloadError,
    DatasetError,
    DatasetIntegrityError,
    DatasetSchemaError,
    DatasetUnavailableError,
    DatasetVersionNotFoundError,
    InvalidCodeError,
    QueryError,
    RecordNotFoundError,
)
from arancel_mx.consumer.models import (
    DatasetInfo,
    Ficha,
    HsSection,
    ProvenanceRecord,
    SearchResult,
    SuggestHit,
    TariffRecord,
)


def test_runtime_version_comes_from_distribution_metadata() -> None:
    assert arancel_mx.__version__ == version("arancel-mx")


def test_consumer_package_reexports_public_types() -> None:
    from arancel_mx.consumer import CompareRow, Dataset, InvalidCodeError

    assert Dataset is arancel_mx.Dataset
    assert Dataset is ConsumerDataset
    assert CompareRow is arancel_mx.CompareRow
    assert InvalidCodeError is arancel_mx.InvalidCodeError
    assert "Dataset" in arancel_mx.consumer.__all__
    assert "CompareRow" in arancel_mx.consumer.__all__
    assert "SuggestHit" in arancel_mx.__all__
    assert "SuggestHit" in arancel_mx.consumer.__all__
    assert arancel_mx.SuggestHit is SuggestHit


def test_exception_hierarchy_is_stable() -> None:
    assert issubclass(DatasetError, ArancelMXError)
    assert issubclass(DatasetUnavailableError, DatasetError)
    assert issubclass(DatasetDownloadError, DatasetError)
    assert issubclass(DatasetIntegrityError, DatasetError)
    assert issubclass(DatasetSchemaError, DatasetError)
    assert issubclass(DatasetVersionNotFoundError, DatasetError)
    assert issubclass(QueryError, ArancelMXError)
    assert issubclass(InvalidCodeError, QueryError)
    assert issubclass(RecordNotFoundError, QueryError)


def test_tariff_record_is_frozen() -> None:
    record = TariffRecord(
        code="01012101",
        level="fraccion8",
        description="Reproductores de raza pura.",
        unit_name="Cbza",
        igi_text="10",
        igi_kind="ad_valorem",
        igi_value=10.0,
        ige_text="Ex.",
        ige_kind="exento",
        ige_value=0.0,
        parent_code="010121",
        dataset_version="2026.08.11",
        schema_version="2",
        effective_from=None,
        effective_to=None,
        is_current=True,
    )
    with pytest.raises(FrozenInstanceError):
        record.code = "x"  # type: ignore[misc]


def test_search_result_constructor_fields_are_contractual() -> None:
    record = TariffRecord(
        code="01012101",
        level="fraccion8",
        description="Reproductores de raza pura.",
        unit_name="Cbza",
        igi_text="10",
        igi_kind="ad_valorem",
        igi_value=10.0,
        ige_text="Ex.",
        ige_kind="exento",
        ige_value=0.0,
        parent_code="010121",
        dataset_version="2026.08.11",
        schema_version="2",
        effective_from=None,
        effective_to=None,
        is_current=True,
    )
    result = SearchResult(record=record, score=100, match_kind="exact_code")
    assert result.record is record
    assert result.score == 100
    assert result.match_kind == "exact_code"
    assert result.scorer_version == "1"
    assert result.confidence == 0.0


def test_provenance_record_constructor_fields_are_contractual() -> None:
    record = ProvenanceRecord(
        source_document_id="snice-ligie-2026-04-20",
        role="primary",
        is_primary=True,
        authority="SNICE",
        publication_venue="SNICE",
        title="LIGIE",
        source_url="https://example.invalid/ligie.xlsx",
        sha256="0" * 64,
        published_at=date(2026, 4, 20),
        effective_from=date(2026, 4, 20),
        effective_to=None,
    )
    assert record.source_document_id == "snice-ligie-2026-04-20"
    assert record.is_primary is True


def test_ficha_and_hs_section_are_frozen_public_models() -> None:
    record = TariffRecord(
        code="01012101",
        level="fraccion8",
        description="Reproductores de raza pura.",
        unit_name="Cbza",
        igi_text="10",
        igi_kind="ad_valorem",
        igi_value=10.0,
        ige_text="Ex.",
        ige_kind="exento",
        ige_value=0.0,
        parent_code="010121",
        dataset_version="2026.08.11",
        schema_version="2",
        effective_from=None,
        effective_to=None,
        is_current=True,
    )
    section = HsSection("I", "Animales vivos y productos del reino animal", "01", "05")
    card = Ficha(
        record=record,
        formatted_code="0101.21.01",
        section=section,
        hierarchy=(record,),
        children=(),
    )
    assert card.section is section
    assert card.section.source == "hs_section_grouping"
    with pytest.raises(FrozenInstanceError):
        card.formatted_code = "x"  # type: ignore[misc]


def test_dataset_info_distinguishes_structural_and_release_integrity() -> None:
    info = DatasetInfo(
        dataset_version="2026.08.11",
        schema_version="2",
        path="/tmp/arancel_mx.duckdb",
        source="local",
        structural_valid=True,
        release_verified=False,
        github_digest_state="unavailable",
    )
    assert info.structural_valid is True
    assert info.release_verified is False
    assert info.github_digest_state == "unavailable"
