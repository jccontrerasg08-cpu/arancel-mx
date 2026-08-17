"""Capture boundary for registered official tariff inputs."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timezone
import hashlib
from importlib.resources import files
import json
from pathlib import Path
import shutil
from typing import TYPE_CHECKING, Any, Sequence
from urllib.parse import urlparse

from arancel_mx.pipeline.reconcile import (
    ReconciliationReport,
    discover_registered_sources,
    reconcile_legal_instruments,
    select_current_document,
)
from arancel_mx.release.metadata import SourceIdentity
from arancel_mx.sources.capture import CaptureManifest, capture_document
from arancel_mx.sources.diputados import LedgerSnapshot, parse_ligie_ledger
from arancel_mx.sources.http import (
    FetchedDocument,
    build_official_session,
    decode_fetched_text,
    fetch_official_document,
)
from arancel_mx.sources.legal_evidence import (
    RequiredDofEvidence,
    required_dof_evidence,
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
    "national_notes": ("Secretaría de Economía / SHCP", "Diario Oficial de la Federación"),
}
LEGAL_EVIDENCE_HOSTS = (
    "dof.gob.mx",
    "www.dof.gob.mx",
    "diputados.gob.mx",
    "www.diputados.gob.mx",
)
LEGAL_FALLBACK_MEDIA_TYPES = (
    "application/pdf",
    "text/html",
    "application/msword",
)


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


def _source_document_id(identity_key: str, final_url: str, source_sha256: str) -> str:
    payload = f"{identity_key}\0{final_url}\0{source_sha256}".encode("utf-8")
    return "source-" + hashlib.sha256(payload).hexdigest()


def _filename(url: str) -> str:
    name = Path(urlparse(url).path).name
    if not name:
        raise ValueError(f"official source URL has no filename: {url}")
    return name


def _retrieval_timestamp(fetched: FetchedDocument):
    value = fetched.retrieved_at
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("fetched.retrieved_at must be timezone-aware")
    return value.astimezone(timezone.utc).replace(microsecond=0)


def _capture_source(
    *,
    dataset_key: str,
    document_role: str,
    title: str,
    url: str,
    entry: RegistryEntry,
    discovery_url: str | None = None,
    discovery_kind: str | None = None,
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
    retrieved_at = _retrieval_timestamp(fetched)
    metadata = {
        "source_id": dataset_key,
        "kind": document_role,
        "observed_at": config.effective_as_of.isoformat(),
        "retrieved_at": retrieved_at.isoformat().replace("+00:00", "Z"),
        "source_url": fetched.final_url,
        "filename": _filename(fetched.final_url),
        "media_type": fetched.media_type,
        "title": title,
    }
    if discovery_url is not None and discovery_kind is not None:
        metadata["discovery_url"] = discovery_url
        metadata["discovery_kind"] = discovery_kind
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
        "retrieved_at": retrieved_at,
    }
    if discovery_url is not None and discovery_kind is not None:
        source_document["discovery_url"] = discovery_url
        source_document["discovery_kind"] = discovery_kind
    return CapturedOfficialSource(
        dataset_key=dataset_key,
        document_role=document_role,
        title=title,
        fetched=fetched,
        capture=capture,
        source_document=source_document,
    )


def _legal_media_types(evidence: RequiredDofEvidence) -> tuple[str, ...]:
    media_types: list[str] = []
    if evidence.media_type != "application/octet-stream":
        media_types.append(evidence.media_type)
    for media_type in LEGAL_FALLBACK_MEDIA_TYPES:
        if media_type not in media_types:
            media_types.append(media_type)
    return tuple(media_types)


def _capture_ledger(
    fetched: FetchedDocument,
    config: OfficialDatasetConfig,
) -> CapturedOfficialSource:
    """Preserve the exact Diputados ledger bytes that drive legal reconciliation."""
    retrieved_at = _retrieval_timestamp(fetched)
    filename = _filename(fetched.final_url)
    metadata = {
        "source_id": "diputados_ligie",
        "kind": "legal_ledger",
        "observed_at": config.effective_as_of.isoformat(),
        "retrieved_at": retrieved_at.isoformat().replace("+00:00", "Z"),
        "source_url": fetched.final_url,
        "filename": filename,
        "media_type": fetched.media_type,
        "title": "LIGIE registered legal ledger",
    }
    capture = capture_document(fetched.content, metadata, config.work_dir / "raw")
    source_id = _source_document_id(
        "diputados_ligie:legal_ledger",
        fetched.final_url,
        capture.sha256,
    )
    authority, venue = SOURCE_AUTHORITY["diputados_ligie"]
    source_document: dict[str, object] = {
        "source_document_id": source_id,
        "authority": authority,
        "publication_venue": venue,
        "title": "LIGIE registered legal ledger",
        "source_url": fetched.final_url,
        "media_type": fetched.media_type,
        "sha256": capture.sha256,
        "local_path": str(capture.path),
        "published_at": None,
        "effective_from": None,
        "effective_to": None,
        "observed_at": config.effective_as_of,
        "retrieved_at": retrieved_at,
    }
    return CapturedOfficialSource(
        dataset_key="diputados_ligie",
        document_role="legal_ledger",
        title="LIGIE registered legal ledger",
        fetched=fetched,
        capture=capture,
        source_document=source_document,
    )


def _capture_legal_evidence(
    evidence: RequiredDofEvidence,
    config: OfficialDatasetConfig,
    session: Any,
) -> CapturedOfficialSource:
    dataset_key = f"dof_{evidence.role}"
    title = f"DOF evidence {evidence.role} {evidence.published_at.isoformat()}"
    fetched = fetch_official_document(
        session,
        evidence.url,
        LEGAL_EVIDENCE_HOSTS,
        _legal_media_types(evidence),
        timeout_s=config.timeout_s,
    )
    retrieved_at = _retrieval_timestamp(fetched)
    metadata = {
        "source_id": dataset_key,
        "kind": evidence.role,
        "observed_at": config.effective_as_of.isoformat(),
        "retrieved_at": retrieved_at.isoformat().replace("+00:00", "Z"),
        "source_url": fetched.final_url,
        "filename": _filename(fetched.final_url),
        "media_type": fetched.media_type,
        "title": title,
        "published_at": evidence.published_at.isoformat(),
    }
    capture = capture_document(fetched.content, metadata, config.work_dir / "raw")
    source_id = _source_document_id(evidence.role, fetched.final_url, capture.sha256)
    source_document: dict[str, object] = {
        "source_document_id": source_id,
        "authority": "Diario Oficial de la Federación",
        "publication_venue": "Diario Oficial de la Federación",
        "title": title,
        "source_url": fetched.final_url,
        "media_type": fetched.media_type,
        "sha256": capture.sha256,
        "local_path": str(capture.path),
        "published_at": evidence.published_at,
        "effective_from": None,
        "effective_to": None,
        "observed_at": config.effective_as_of,
        "retrieved_at": retrieved_at,
    }
    return CapturedOfficialSource(
        dataset_key=dataset_key,
        document_role=evidence.role,
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


def _reconciliation_record(source: CapturedOfficialSource) -> dict[str, object]:
    source_document = source.source_document
    return {
        "document_id": source_document["source_document_id"],
        "role": source.document_role,
        "published_at": source_document.get("published_at"),
        "source_url": source.fetched.final_url,
        "sha256": source.capture.sha256,
    }


def _reconcile_snapshot(
    ledger: LedgerSnapshot,
    sources: Sequence[CapturedOfficialSource],
) -> ReconciliationReport:
    dof_documents = tuple(
        _reconciliation_record(source)
        for source in sources
        if source.dataset_key in {"dof_law_reform", "dof_tariff_decree"}
    )
    snice_documents = tuple(
        _reconciliation_record(source)
        for source in sources
        if source.dataset_key in {"ligie", "nico"}
    )
    report = reconcile_legal_instruments(ledger, dof_documents, snice_documents)
    if not report.publishable:
        details = "; ".join(report.discrepancies)
        raise ValueError(f"legal reconciliation failed: {details}")
    return report


def capture_official_inputs(
    config: OfficialDatasetConfig,
    session: Any | None = None,
) -> OfficialInputSnapshot:
    """Discover, capture, and reconcile official inputs before parsing them."""
    if config.timeout_s <= 0:
        raise ValueError("timeout_s must be positive")

    client = session or build_official_session()
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
    ledger_source = _capture_ledger(ledger_fetch, config)
    ledger = parse_ligie_ledger(
        decode_fetched_text(ledger_fetch),
        ledger_fetch.final_url,
    )
    legal_requirements = required_dof_evidence(ledger)
    legal_sources = tuple(
        _capture_legal_evidence(evidence, config, client)
        for evidence in legal_requirements
    )
    consolidated_url = registered_direct_document(
        diputados_entry,
        "consolidated_text",
    )
    national_notes_entry = registry["national_notes"]
    national_notes_url = registered_direct_document(
        national_notes_entry,
        "national_notes",
    )

    discovery_registry = {key: registry[key] for key in ("ligie", "nico")}
    discovered = discover_registered_sources(
        discovery_registry,
        client,
        timeout_s=config.timeout_s,
    )
    ligie_document = select_current_document(discovered, "ligie", "ligie_snapshot")
    nico_document = select_current_document(discovered, "nico", "nico_snapshot")

    sources = (
        _capture_source(
            dataset_key="ligie",
            document_role="ligie_snapshot",
            title=ligie_document.title or _filename(ligie_document.source_url),
            url=ligie_document.source_url,
            entry=registry["ligie"],
            discovery_url=ligie_document.discovery_url,
            discovery_kind=ligie_document.discovery_kind,
            config=config,
            session=client,
        ),
        _capture_source(
            dataset_key="nico",
            document_role="nico_snapshot",
            title=nico_document.title or _filename(nico_document.source_url),
            url=nico_document.source_url,
            entry=registry["nico"],
            discovery_url=nico_document.discovery_url,
            discovery_kind=nico_document.discovery_kind,
            config=config,
            session=client,
        ),
        ledger_source,
        _capture_source(
            dataset_key="diputados_ligie",
            document_role="consolidated_text",
            title=f"Texto vigente {config.ligie_version.replace('-', ' ')}",
            url=consolidated_url,
            entry=diputados_entry,
            config=config,
            session=client,
        ),
        _capture_source(
            dataset_key="national_notes",
            document_role="national_notes",
            title="Notas nacionales LIGIE (DOF)",
            url=national_notes_url,
            entry=national_notes_entry,
            config=config,
            session=client,
        ),
        *legal_sources,
    )
    reconciliation = _reconcile_snapshot(ledger, sources)
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
    """Copy captured evidence into the verified release-source directory."""
    source_dir = config.work_dir / "release-sources"
    if source_dir.exists():
        raise FileExistsError(f"Release source directory already exists: {source_dir}")
    source_dir.mkdir(parents=True)

    def release_filename(item: CapturedOfficialSource) -> str:
        suffix = Path(urlparse(item.fetched.final_url).path).suffix.lower()
        key = (item.dataset_key, item.document_role)
        if key == ("ligie", "ligie_snapshot"):
            return f"ligie{suffix}"
        if key == ("nico", "nico_snapshot"):
            return f"nico{suffix}"
        if key == ("diputados_ligie", "legal_ledger"):
            return f"ligie-ledger{suffix or '.html'}"
        if key == ("diputados_ligie", "consolidated_text"):
            return "ligie-consolidated.pdf"
        if key == ("national_notes", "national_notes"):
            return "national-notes.html"
        if key == ("dof_law_reform", "law_reform"):
            return f"dof-law-reform{suffix}"
        if key == ("dof_tariff_decree", "tariff_decree"):
            return f"dof-tariff-decree{suffix}"
        raise ValueError(
            f"unexpected release source: {item.dataset_key}/{item.document_role}"
        )

    rows = []
    used_names: set[str] = set()
    for item in sorted(
        captured,
        key=lambda value: (value.dataset_key, value.document_role),
    ):
        filename = release_filename(item)
        if filename in used_names:
            raise ValueError(f"duplicate release source filename: {filename}")
        used_names.add(filename)
        target = source_dir / filename
        shutil.copyfile(item.capture.path, target)
        source_document = item.source_document
        row: dict[str, object] = {
            "dataset_key": item.dataset_key,
            "document_role": item.document_role,
            "filename": filename,
            "media_type": item.fetched.media_type,
            "sha256": item.capture.sha256,
            "source_document_id": source_document["source_document_id"],
            "source_url": source_document["source_url"],
            "published_at": (
                source_document["published_at"].isoformat()
                if source_document.get("published_at")
                else None
            ),
        }
        if source_document.get("discovery_url") is not None:
            row["discovery_url"] = source_document["discovery_url"]
            row["discovery_kind"] = source_document["discovery_kind"]
        rows.append(row)
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
