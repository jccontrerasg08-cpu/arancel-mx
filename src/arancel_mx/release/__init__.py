"""Verification, metadata, and packaging for tariff release artifacts."""

from __future__ import annotations

from typing import Any

from .metadata import (
    ReleaseProvenance,
    SourceIdentity,
    source_identity_changed,
    source_identity_digest,
    source_identity_from_manifest,
)

_PACKAGE_EXPORTS = {
    "PUBLIC_RELEASE_ASSETS",
    "build_release",
    "prepare_release_archive",
    "verify_publication_bundle",
    "verify_release",
    "verify_sources",
}

__all__ = [
    "PUBLIC_RELEASE_ASSETS",
    "ReleaseProvenance",
    "SourceIdentity",
    "build_release",
    "prepare_release_archive",
    "source_identity_changed",
    "source_identity_digest",
    "source_identity_from_manifest",
    "verify_publication_bundle",
    "verify_release",
    "verify_sources",
]


def __getattr__(name: str) -> Any:
    if name in _PACKAGE_EXPORTS:
        from . import package

        return getattr(package, name)
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")
