"""Public consumer-facing types, exceptions, and Dataset facade."""

from arancel_mx.consumer.dataset import Dataset
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
    CompareRow,
    DatasetInfo,
    Ficha,
    HsSection,
    ProvenanceRecord,
    SearchResult,
    TariffRecord,
)

__all__ = [
    "ArancelMXError",
    "CompareRow",
    "Dataset",
    "DatasetDownloadError",
    "DatasetError",
    "DatasetInfo",
    "DatasetIntegrityError",
    "DatasetSchemaError",
    "DatasetUnavailableError",
    "DatasetVersionNotFoundError",
    "Ficha",
    "HsSection",
    "InvalidCodeError",
    "ProvenanceRecord",
    "QueryError",
    "RecordNotFoundError",
    "SearchResult",
    "TariffRecord",
]
