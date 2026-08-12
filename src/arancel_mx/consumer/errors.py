"""Documented consumer exception hierarchy."""


class ArancelMXError(Exception):
    """Base class for documented consumer failures."""


class DatasetError(ArancelMXError):
    """Base class for dataset discovery, download, and integrity failures."""


class DatasetUnavailableError(DatasetError):
    """Raised when no usable dataset is available."""


class DatasetDownloadError(DatasetError):
    """Raised when a dataset cannot be retrieved."""


class DatasetIntegrityError(DatasetError):
    """Raised when downloaded dataset material fails integrity checks."""


class DatasetSchemaError(DatasetError):
    """Raised when a dataset schema is unsupported or inconsistent."""


class DatasetVersionNotFoundError(DatasetError):
    """Raised when a requested data release does not exist."""


class QueryError(ArancelMXError):
    """Base class for public query failures."""


class InvalidCodeError(QueryError):
    """Raised when a tariff code is syntactically invalid."""


class RecordNotFoundError(QueryError):
    """Raised when a valid code is absent from the selected dataset."""
