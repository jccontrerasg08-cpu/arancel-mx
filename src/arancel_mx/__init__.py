"""Open tools for Mexican tariff data."""

from importlib.metadata import version as _distribution_version

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
    DatasetInfo,
    Ficha,
    HsSection,
    ProvenanceRecord,
    SearchResult,
    TariffRecord,
)

__version__ = _distribution_version("arancel-mx")

__all__ = [
    "ArancelMXError",
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
    "__version__",
]
