"""Public consumer-facing types and exceptions."""

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
from arancel_mx.consumer.models import DatasetInfo, ProvenanceRecord, SearchResult, TariffRecord

__all__ = [
    "ArancelMXError",
    "DatasetDownloadError",
    "DatasetError",
    "DatasetInfo",
    "DatasetIntegrityError",
    "DatasetSchemaError",
    "DatasetUnavailableError",
    "DatasetVersionNotFoundError",
    "InvalidCodeError",
    "ProvenanceRecord",
    "QueryError",
    "RecordNotFoundError",
    "SearchResult",
    "TariffRecord",
]
