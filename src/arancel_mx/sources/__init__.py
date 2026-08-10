"""Official-source registry and immutable source captures."""

from arancel_mx.sources.capture import CaptureManifest, can_reuse_parse, capture_document
from arancel_mx.sources.diputados import parse_ligie_ledger
from arancel_mx.sources.http import FetchedDocument, fetch_official_document
from arancel_mx.sources.registry import RegistryEntry, classify_candidate, load_source_registry
from arancel_mx.sources.snice import DownloadTask, discover_snice_documents

__all__ = [
    "CaptureManifest",
    "DownloadTask",
    "FetchedDocument",
    "RegistryEntry",
    "can_reuse_parse",
    "capture_document",
    "classify_candidate",
    "discover_snice_documents",
    "fetch_official_document",
    "load_source_registry",
    "parse_ligie_ledger",
]
