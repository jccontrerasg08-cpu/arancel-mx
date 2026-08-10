"""Capture boundary for registered official tariff inputs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone
import hashlib
from importlib.resources import files
import json
from pathlib import Path
import shutil
from typing import TYPE_CHECKING, Any, Sequence
from urllib.parse import urlparse

import requests

from arancel_mx.pipeline.reconcile import (
    ReconciliationReport,
    discover_registered_sources,
    select_current_document,
)
from arancel_mx.release.metadata import SourceIdentity
from arancel_mx.sources.capture import CaptureManifest, capture_document
from arancel_mx.sources.diputados import LedgerSnapshot, parse_ligie_ledger
from arancel_mx.sources.http import (
    FetchedDocument,
    decode_fetched_text,
    fetch_official_document,
)
from arancel_mx.sources.registry import (
    RegistryEntry,
    load_source_registry,
    registered_direct_document,
)

if TYPE_CHECKING:
    from arancel_mx.pipeline.official_dataset import OfficialDatasetConfig


SOURCE_AUTHORITY = {
    "ligie": ("Secretaría de Economía / SNICE", "SNICE"),
    "nico": ("Secretaría de Economía / SNICE", "SNICE"),
    "diputados_ligie": ("Cámara de Diputados", "Cámara de Diputados"),
}


@dataclass(frozen=True)
class CapturedOfficialSource:
    dataset_key: str
    document_role: str
    title: str
    fetched: FetchedDocument
    capture: CaptureManifest
    source_document: dict[str, object]


@dataclass(frozen=True)
class OfficialInputSnapshot:
    ledger: LedgerSnapshot
    sources: tuple[CapturedOfficialSource, ...]
    identities: tuple[SourceIdentity, ...]
    registry_version: str
    registry_sha256: str
    reconciliation: ReconciliationReport


def _build_timestamp(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("generated_at must be timezone-aware")
    return value.astimezone(timezone.utc).replace(microsecond=0)


def _source_document_id(dataset_key: str, final_url: str, source_sha256: str) -> str:
    payload = f"{dataset_key}\0{final_url}\0{source_sha256}".encode("utf-8")
    return "source-" + hashlib.sha256(payload).hexdigest()


def _filename(url: str) -> str:
    name = Path(urlparse(url).path).name
    if not name:
        raise ValueError(f"official source URL has no filename: {url}")
    return name


def _capture_source(
    *,
    dataset_key: str,
    document_role: str,
    title: str,
    url: str,
    entry: RegistryEntry,
    config: OfficialDatasetConfig,
    session: Any,
) -> CapturedOfficialSource:
    fetched = fetch_official_document(
        session,
        url,
        entry.allowed_hosts,
        entry.media_types,
        timeout_s=config.timeout_s,
    )
    generated_at = _build_timestamp(config.generated_at)
    metadata = {
        "source_id": dataset_key,
        "kind": document_role,
        "observed_at": config.effective_as_of.isoformat(),
        "retrieved_at": generated_at.isoformat().replace("+00:00", "Z"),
        "source_url": fetched.final_url,
        "filename": _filename(fetched.final_url),
        "media_type": fetched.media_type,
        "title": title,
    }
    capture = capture_document(fetched.content, metadata, config.work_dir / "raw")
    source_id = _source_document_id(dataset_key, fetched.final_url, capture.sha256)
    authority, venue = SOURCE_AUTHORITY[dataset_key]
    source_document: dict[str, object] = {
        "source_document_id": source_id,
        "authority": authority,
        "publication_venue": venue,
        "title": title,
        "source_url": fetched.final_url,
        "media_type": fetched.media_type,
        "sha256": capture.sha256,
        "local_path": str(capture.path),
        "published_at": None,
        "effective_from": None,
        "effective_to": None,
        "observed_at": config.effective_as_of,
        "retrieved_at": generated_at,
    }
    return CapturedOfficialSource(
        dataset_key=dataset_key,
        document_role=document_role,
        title=title,
        fetched=fetched,
        capture=capture,
        source_document=source_document,
    )


def _registry_metadata(registry: dict[str, RegistryEntry]) -> tuple[str, str]:
    versions = {entry.registry_version for entry in registry.values()}
    if len(versions) != 1:
        raise ValueError("source registry contains inconsistent registry versions")
    registry_version = next(iter(versions))
    resource = files("arancel_mx.sources").joinpath("source_registry.json")
    registry_sha256 = hashlib.sha256(resource.read_bytes()).hexdigest()
    return registry_version, registry_sha256


def capture_official_inputs(
    config: OfficialDatasetConfig,
    session: Any | None = None,
) -> OfficialInputSnapshot:
    """Discover and capture the registered base inputs before parsing them."""
    if config.timeout_s <= 0:
        raise ValueError("timeout_s must be positive")

    client = session or requests.Session()
    registry = load_source_registry()
    registry_version, registry_sha256 = _registry_metadata(registry)

    diputados_entry = registry["diputados_ligie"]
    ledger_fetch = fetch_official_document(
        client,
        diputados_entry.canonical_page,
        diputados_entry.allowed_hosts,
        ("text/html",),
        timeout_s=config.timeout_s,
    )
    ledger = parse_ligie_ledger(
        decode_fetched_text(ledger_fetch),
        ledger_fetch.final_url,
    )
    consolidated_url = registered_direct_document(
        diputados_entry,
        "consolidated_text",
    )

    discovery_registry = {key: registry[key] for key in ("ligie", "nico")}
    discovered = discover_registered_sources(discovery_registry, client)
    ligie_document = select_current_document(discovered, "ligie", "ligie_snapshot")
    nico_document = select_current_document(discovered, "nico", "nico_snapshot")

    sources = (
        _capture_source(
            dataset_key="ligie",
            document_role="ligie_snapshot",
            title=ligie_document.title or _filename(ligie_document.source_url),
            url=ligie_document.source_url,
            entry=registry["ligie"],
            config=config,
            session=client,
        ),
        _capture_source(
            dataset_key="nico",
            document_role="nico_snapshot",
            title=nico_document.title or _filename(nico_document.source_url),
            url=nico_document.source_url,
            entry=registry["nico"],
            config=config,
            session=client,
        ),
        _capture_source(
            dataset_key="diputados_ligie",
            document_role="consolidated_text",
            title=f"Texto vigente {config.ligie_version.replace('-', ' ')}",
            url=consolidated_url,
            entry=diputados_entry,
            config=config,
            session=client,
        ),
    )
    identities = tuple(
        SourceIdentity(
            dataset_key=source.dataset_key,
            document_role=source.document_role,
            source_url=source.fetched.final_url,
            sha256=source.capture.sha256,
            registry_version=registry_version,
        )
        for source in sources
    )
    reconciliation = ReconciliationReport(
        publishable=False,
        error_codes=("not_evaluated",),
        discrepancies=("legal reconciliation not yet evaluated",),
        legal_document_ids=(),
        proposal_document_ids=(),
        indicator_document_ids=(),
    )
    return OfficialInputSnapshot(
        ledger=ledger,
        sources=sources,
        identities=identities,
        registry_version=registry_version,
        registry_sha256=registry_sha256,
        reconciliation=reconciliation,
    )


def write_release_sources(
    config: OfficialDatasetConfig,
    captured: Sequence[CapturedOfficialSource],
) -> Path:
    """Copy captured base evidence into the verified release-source directory."""
    source_dir = config.work_dir / "release-sources"
    if source_dir.exists():
        raise FileExistsError(f"Release source directory already exists: {source_dir}")
    source_dir.mkdir(parents=True)

    names: dict[str, str] = {}
    for item in captured:
        suffix = Path(urlparse(item.fetched.final_url).path).suffix.lower()
        if item.dataset_key == "ligie":
            names[item.dataset_key] = f"ligie{suffix}"
        elif item.dataset_key == "nico":
            names[item.dataset_key] = f"nico{suffix}"
        elif item.dataset_key == "diputados_ligie":
            names[item.dataset_key] = "ligie-consolidated.pdf"
        else:
            raise ValueError(f"unexpected release source: {item.dataset_key}")

    rows = []
    for item in sorted(captured, key=lambda value: value.dataset_key):
        filename = names[item.dataset_key]
        target = source_dir / filename
        shutil.copyfile(item.capture.path, target)
        source_document = item.source_document
        rows.append(
            {
                "dataset_key": item.dataset_key,
                "filename": filename,
                "media_type": item.fetched.media_type,
                "sha256": item.capture.sha256,
                "source_document_id": source_document["source_document_id"],
                "source_url": source_document["source_url"],
            }
        )
    (source_dir / "source_capture.json").write_text(
        json.dumps(
            rows,
            ensure_ascii=False,
            sort_keys=True,
            separators=(",", ":"),
        )
        + "\n",
        encoding="utf-8",
    )
    return source_dir
