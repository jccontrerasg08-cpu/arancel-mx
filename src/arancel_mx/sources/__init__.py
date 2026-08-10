"""Official-source registry and immutable source captures."""

from arancel_mx.sources.capture import CaptureManifest, can_reuse_parse, capture_document
from arancel_mx.sources.registry import RegistryEntry, classify_candidate, load_source_registry

__all__ = [
    "CaptureManifest",
    "RegistryEntry",
    "can_reuse_parse",
    "capture_document",
    "classify_candidate",
    "load_source_registry",
]
