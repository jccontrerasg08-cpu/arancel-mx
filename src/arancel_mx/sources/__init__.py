"""Official-source registry and immutable source captures."""

from arancel_mx.sources.capture import CaptureManifest, capture_document
from arancel_mx.sources.diputados import parse_ligie_ledger
from arancel_mx.sources.http import FetchedDocument, fetch_official_document
from arancel_mx.sources.legal_evidence import RequiredDofEvidence, required_dof_evidence
from arancel_mx.sources.registry import RegistryEntry, classify_candidate, load_source_registry

__all__ = [
    "CaptureManifest",
    "FetchedDocument",
    "RegistryEntry",
    "RequiredDofEvidence",
    "capture_document",
    "classify_candidate",
    "fetch_official_document",
    "load_source_registry",
    "parse_ligie_ledger",
    "required_dof_evidence",
]
