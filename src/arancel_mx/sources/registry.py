"""Versioned authoritative-source registry for the Mexican tariff pipeline."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from importlib.resources import files
from pathlib import Path
from urllib.parse import urlparse


@dataclass(frozen=True)
class RegistryEntry:
    dataset_key: str
    registry_version: str
    canonical_page: str
    corpus_index_pages: tuple[str, ...]
    allowed_hosts: tuple[str, ...]
    media_types: tuple[str, ...]
    families: tuple[tuple[str, tuple[str, ...]], ...]
    direct_documents: tuple[tuple[str, str], ...]
    source_role: str
    authoritative_for_tariff: bool
    authoritative_for_discovery: bool
    authoritative_for_consolidated_text: bool
    legal_publication_authority: str


def _page_identity(url: str) -> tuple[str, str]:
    parsed = urlparse(url)
    return parsed.netloc.lower(), parsed.path.rstrip("/").lower()


def _validate_registered_url(url: str, allowed_hosts: tuple[str, ...]) -> str:
    parsed = urlparse(url)
    if parsed.scheme.lower() != "https":
        raise ValueError(f"registered source URL must use HTTPS: {url}")
    if (parsed.hostname or "").lower() not in allowed_hosts:
        raise ValueError(f"registered source URL host is not allowed: {url}")
    return url


def load_source_registry(
    path: Path | str | None = None,
) -> dict[str, RegistryEntry]:
    if path is None:
        resource = files("arancel_mx.sources").joinpath("source_registry.json")
        with resource.open("r", encoding="utf-8") as handle:
            payload = json.load(handle)
    else:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    version = str(payload["registry_version"])
    entries: dict[str, RegistryEntry] = {}
    for key, raw in payload["sources"].items():
        allowed_hosts = tuple(host.lower() for host in raw["allowed_hosts"])
        canonical_page = _validate_registered_url(raw["canonical_page"], allowed_hosts)
        corpus_index_pages = tuple(
            _validate_registered_url(str(url), allowed_hosts)
            for url in raw.get("corpus_index_pages", ())
        )
        families = tuple(
            (role, tuple(patterns)) for role, patterns in raw["families"].items()
        )
        direct_documents = tuple(
            (
                str(role),
                _validate_registered_url(str(url), allowed_hosts),
            )
            for role, url in raw.get("direct_documents", {}).items()
        )
        entries[key] = RegistryEntry(
            dataset_key=key,
            registry_version=version,
            canonical_page=canonical_page,
            corpus_index_pages=corpus_index_pages,
            allowed_hosts=allowed_hosts,
            media_types=tuple(value.lower() for value in raw["media_types"]),
            families=families,
            direct_documents=direct_documents,
            source_role=raw["source_role"],
            authoritative_for_tariff=bool(raw["authoritative_for_tariff"]),
            authoritative_for_discovery=bool(raw["authoritative_for_discovery"]),
            authoritative_for_consolidated_text=bool(
                raw["authoritative_for_consolidated_text"]
            ),
            legal_publication_authority=raw["legal_publication_authority"],
        )
    return entries


def registered_direct_document(entry: RegistryEntry, role: str) -> str:
    """Return one explicitly registered direct document without guessing a URL."""
    matches = [url for registered_role, url in entry.direct_documents if registered_role == role]
    if len(matches) != 1:
        raise ValueError(
            f"registered direct document is missing or ambiguous: {entry.dataset_key}:{role}"
        )
    return matches[0]


def _classify_family(
    entry: RegistryEntry,
    href: str,
    media_type: str,
) -> str | None:
    parsed_href = urlparse(href)
    if parsed_href.netloc and parsed_href.netloc.lower() not in entry.allowed_hosts:
        return None
    if media_type.split(";", 1)[0].strip().lower() not in entry.media_types:
        return None
    filename = Path(parsed_href.path).name.upper()
    for role, patterns in entry.families:
        if any(re.fullmatch(pattern, filename, flags=re.IGNORECASE) for pattern in patterns):
            return role
    return None


def classify_candidate(
    entry: RegistryEntry,
    discovery_url: str,
    href: str,
    media_type: str,
) -> str | None:
    """Return the registered family only for a candidate on its canonical page."""
    if _page_identity(discovery_url) != _page_identity(entry.canonical_page):
        return None
    return _classify_family(entry, href, media_type)


def classify_corpus_candidate(
    entry: RegistryEntry,
    discovery_url: str,
    href: str,
    media_type: str,
) -> str | None:
    """Return a family only for a candidate from an explicitly registered corpus index."""
    if _page_identity(discovery_url) not in {
        _page_identity(url) for url in entry.corpus_index_pages
    }:
        return None
    return _classify_family(entry, href, media_type)
