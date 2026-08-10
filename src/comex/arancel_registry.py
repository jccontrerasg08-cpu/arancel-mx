"""Versioned authoritative-source registry for the Mexican tariff pipeline."""

from __future__ import annotations

import json
import re
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import urlparse


DEFAULT_REGISTRY_PATH = (
    Path(__file__).resolve().parents[2] / "data" / "arancel_mx" / "source_registry.json"
)


@dataclass(frozen=True)
class RegistryEntry:
    dataset_key: str
    registry_version: str
    canonical_page: str
    allowed_hosts: tuple[str, ...]
    media_types: tuple[str, ...]
    families: tuple[tuple[str, tuple[str, ...]], ...]
    source_role: str
    authoritative_for_tariff: bool
    authoritative_for_discovery: bool
    authoritative_for_consolidated_text: bool
    legal_publication_authority: str


def _page_identity(url: str) -> tuple[str, str]:
    parsed = urlparse(url)
    return parsed.netloc.lower(), parsed.path.rstrip("/").lower()


def load_source_registry(
    path: Path | str = DEFAULT_REGISTRY_PATH,
) -> dict[str, RegistryEntry]:
    payload = json.loads(Path(path).read_text(encoding="utf-8"))
    version = str(payload["registry_version"])
    entries: dict[str, RegistryEntry] = {}
    for key, raw in payload["sources"].items():
        families = tuple(
            (role, tuple(patterns)) for role, patterns in raw["families"].items()
        )
        entries[key] = RegistryEntry(
            dataset_key=key,
            registry_version=version,
            canonical_page=raw["canonical_page"],
            allowed_hosts=tuple(host.lower() for host in raw["allowed_hosts"]),
            media_types=tuple(value.lower() for value in raw["media_types"]),
            families=families,
            source_role=raw["source_role"],
            authoritative_for_tariff=bool(raw["authoritative_for_tariff"]),
            authoritative_for_discovery=bool(raw["authoritative_for_discovery"]),
            authoritative_for_consolidated_text=bool(
                raw["authoritative_for_consolidated_text"]
            ),
            legal_publication_authority=raw["legal_publication_authority"],
        )
    return entries


def classify_candidate(
    entry: RegistryEntry,
    discovery_url: str,
    href: str,
    media_type: str,
) -> str | None:
    """Return the registered family only for a candidate on its canonical page."""
    if _page_identity(discovery_url) != _page_identity(entry.canonical_page):
        return None
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
