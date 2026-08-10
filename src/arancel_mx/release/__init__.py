"""Verification, metadata, and packaging for tariff release artifacts."""

from .metadata import (
    ReleaseProvenance,
    SourceIdentity,
    source_identity_changed,
    source_identity_digest,
    source_identity_from_manifest,
)
from .package import (
    build_release,
    prepare_release_archive,
    verify_release,
    verify_sources,
)

__all__ = [
    "ReleaseProvenance",
    "SourceIdentity",
    "build_release",
    "prepare_release_archive",
    "source_identity_changed",
    "source_identity_digest",
    "source_identity_from_manifest",
    "verify_release",
    "verify_sources",
]
