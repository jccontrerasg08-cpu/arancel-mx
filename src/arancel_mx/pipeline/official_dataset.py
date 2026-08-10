"""End-to-end construction of the first canonical dataset from official sources."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
import hashlib
import json
from pathlib import Path
import shutil
from typing import Any
from urllib.parse import urlparse

import requests

from arancel_mx.parsers.documents import parse_ligie_pdf_hierarchy
from arancel_mx.parsers.profiles import resolve_workbook_profile
from arancel_mx.parsers.workbooks import (
    parse_ligie_workbook,
    parse_nico_workbook,
    probe_workbook,
)
from arancel_mx.pipeline.build import export_arancel_release, materialize_arancel
from arancel_mx.pipeline.hierarchy import assemble_classifications
from arancel_mx.pipeline.reconcile import (
    discover_registered_sources,
    select_current_document,
)
from arancel_mx.release.package import (
    prepare_release_archive,
    verify_release,
    verify_sources,
)
from arancel_mx.sources.capture import CaptureManifest, capture_document
from arancel_mx.sources.diputados import parse_ligie_ledger
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
from arancel_mx.storage.duckdb import connect, init_tariff_db


SOURCE_IDENTITY = {
    "ligie": ("Secretaría de Economía / SNICE", "SNICE"),
    "nico": ("Secretaría de Economía / SNICE", "SNICE"),
    "diputados_ligie": ("Cámara de Diputados", "Cámara de Diputados"),
}


@dataclass(frozen=True)
class OfficialDatasetConfig:
    work_dir: Path
    output_dir: Path
    effective_as_of: date
    dataset_version: str
    generated_at: datetime
    schema_version: str = "1"
    ligie_version: str = "LIGIE-2022"
    timeout_s: float = 60.0


@dataclass(frozen=True)
class _CapturedSource:
    dataset_key: str
    title: str
    fetched: FetchedDocument
    capture: CaptureManifest
    source_document: dict[str, object]


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
) -> _CapturedSource:
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
    authority, venue = SOURCE_IDENTITY[dataset_key]
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
    return _CapturedSource(dataset_key, title, fetched, capture, source_document)


def _fraction_and_rate_rows(staging_rows, source_id: str, config: OfficialDatasetConfig):
    fractions: list[dict[str, object]] = []
    rates: list[dict[str, object]] = []
    for staging in staging_rows:
        normalized = staging.normalized
        fraction = {
            "level": "fraccion8",
            "code": normalized["code"],
            "description": normalized["description"],
            "ligie_version": config.ligie_version,
            "validity_basis": "observed_snapshot",
            "updated_at": config.effective_as_of,
            "published_at": None,
            "classification_effective_from": None,
            "classification_effective_to": None,
            "source_document_id": source_id,
        }
        rate = {
            "code": normalized["code"],
            "unit_code": normalized.get("unit_code"),
            "unit_name": normalized.get("unit_name"),
            "igi_text": normalized.get("igi_text"),
            "igi_kind": normalized.get("igi_kind"),
            "igi_value": normalized.get("igi_value"),
            "ige_text": normalized.get("ige_text"),
            "ige_kind": normalized.get("ige_kind"),
            "ige_value": normalized.get("ige_value"),
            "ligie_version": config.ligie_version,
            "updated_at": config.effective_as_of,
            "published_at": None,
            "rate_effective_from": None,
            "rate_effective_to": None,
            "source_document_id": source_id,
        }
        fractions.append(fraction)
        rates.append(rate)
    return fractions, rates


def _nico_rows(staging_rows, source_id: str, config: OfficialDatasetConfig):
    return [
        {
            "level": "nico10",
            "code": staging.normalized["nico10"],
            "description": staging.normalized["description"],
            "ligie_version": config.ligie_version,
            "validity_basis": "observed_snapshot",
            "updated_at": config.effective_as_of,
            "published_at": None,
            "classification_effective_from": None,
            "classification_effective_to": None,
            "source_document_id": source_id,
        }
        for staging in staging_rows
    ]


def _release_sources(
    config: OfficialDatasetConfig,
    captured: list[_CapturedSource],
) -> Path:
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


def build_official_dataset(
    config: OfficialDatasetConfig,
    session: Any | None = None,
) -> dict[str, object]:
    """Build one verified release from current registered official sources."""
    if config.timeout_s <= 0:
        raise ValueError("timeout_s must be positive")
    generated_at = _build_timestamp(config.generated_at)
    if config.work_dir.exists() and any(config.work_dir.iterdir()):
        raise FileExistsError(f"Work directory is not empty: {config.work_dir}")
    if config.output_dir.exists():
        raise FileExistsError(f"Output directory already exists: {config.output_dir}")
    config.work_dir.mkdir(parents=True, exist_ok=True)

    client = session or requests.Session()
    registry = load_source_registry()
    diputados_entry = registry["diputados_ligie"]
    ledger_fetch = fetch_official_document(
        client,
        diputados_entry.canonical_page,
        diputados_entry.allowed_hosts,
        ("text/html",),
        timeout_s=config.timeout_s,
    )
    ledger_html = decode_fetched_text(ledger_fetch)
    parse_ligie_ledger(ledger_html, ledger_fetch.final_url)
    consolidated_url = registered_direct_document(
        diputados_entry, "consolidated_text"
    )

    discovery_registry = {key: registry[key] for key in ("ligie", "nico")}
    discovered = discover_registered_sources(discovery_registry, client)
    ligie_document = select_current_document(discovered, "ligie", "ligie_snapshot")
    nico_document = select_current_document(discovered, "nico", "nico_snapshot")

    ligie_source = _capture_source(
        dataset_key="ligie",
        document_role="ligie_snapshot",
        title=ligie_document.title or _filename(ligie_document.source_url),
        url=ligie_document.source_url,
        entry=registry["ligie"],
        config=config,
        session=client,
    )
    nico_source = _capture_source(
        dataset_key="nico",
        document_role="nico_snapshot",
        title=nico_document.title or _filename(nico_document.source_url),
        url=nico_document.source_url,
        entry=registry["nico"],
        config=config,
        session=client,
    )
    diputados_source = _capture_source(
        dataset_key="diputados_ligie",
        document_role="consolidated_text",
        title=f"Texto vigente {config.ligie_version.replace('-', ' ')}",
        url=consolidated_url,
        entry=diputados_entry,
        config=config,
        session=client,
    )
    captured = [ligie_source, nico_source, diputados_source]

    ligie_profile = resolve_workbook_profile(
        probe_workbook(ligie_source.capture.path), "ligie_snapshot"
    )
    ligie_staging = parse_ligie_workbook(
        ligie_source.capture.path,
        {"source_document_id": ligie_source.source_document["source_document_id"]},
        ligie_profile.profile,
    )
    fraction_rows, rate_rows = _fraction_and_rate_rows(
        ligie_staging,
        str(ligie_source.source_document["source_document_id"]),
        config,
    )

    nico_profile = resolve_workbook_profile(
        probe_workbook(nico_source.capture.path), "nico_snapshot"
    )
    nico_staging = parse_nico_workbook(
        nico_source.capture.path,
        {"source_document_id": nico_source.source_document["source_document_id"]},
        nico_profile.profile,
    )
    nico_rows = _nico_rows(
        nico_staging,
        str(nico_source.source_document["source_document_id"]),
        config,
    )

    hs_rows = parse_ligie_pdf_hierarchy(
        diputados_source.capture.path,
        str(diputados_source.source_document["source_document_id"]),
        config.ligie_version,
        published_at=None,
        effective_from=None,
    )
    for row in hs_rows:
        row["updated_at"] = config.effective_as_of
        row["published_at"] = None
        row["validity_basis"] = "observed_snapshot"
    classifications = assemble_classifications(hs_rows, fraction_rows, nico_rows)

    source_documents = sorted(
        (item.source_document for item in captured),
        key=lambda row: str(row["source_document_id"]),
    )
    release = {
        "dataset_version": config.dataset_version,
        "schema_version": config.schema_version,
        "ligie_version": config.ligie_version,
        "effective_as_of": config.effective_as_of,
        "generated_at": generated_at,
    }
    candidate = config.work_dir / "candidate" / "arancel_mx.duckdb"
    init_tariff_db(candidate)
    with connect(candidate) as connection:
        build_summary = materialize_arancel(
            connection,
            source_documents,
            classifications,
            rate_rows,
            release,
        )
        level_counts = dict(
            connection.execute(
                "SELECT level, COUNT(*) FROM arancel_mx GROUP BY level"
            ).fetchall()
        )
        igi_count, ige_count = connection.execute(
            """
            SELECT
                COUNT(*) FILTER (
                    WHERE level = 'fraccion8'
                      AND igi_text IS NOT NULL
                      AND TRIM(igi_text) <> ''
                ),
                COUNT(*) FILTER (
                    WHERE level = 'fraccion8'
                      AND ige_text IS NOT NULL
                      AND TRIM(ige_text) <> ''
                )
            FROM arancel_mx
            """
        ).fetchone()
    if int(build_summary["row_count"]) <= 0:
        raise ValueError("canonical dataset contains no rows")
    if int(level_counts.get("fraccion8", 0)) <= 0:
        raise ValueError("canonical dataset contains no tariff fractions")
    if int(level_counts.get("nico10", 0)) <= 0:
        raise ValueError("canonical dataset contains no NICO rows")
    if int(igi_count) <= 0 or int(ige_count) <= 0:
        raise ValueError("canonical tariff fractions contain no IGI/IGE tariff values")

    export_arancel_release(candidate, config.output_dir)
    source_dir = _release_sources(config, captured)
    source_rows = verify_sources(source_dir)
    prepare_release_archive(
        config.output_dir,
        source_dir,
        config.work_dir / "latest",
    )
    verified = verify_release(config.output_dir)

    return {
        "dataset_version": str(verified["dataset_version"]),
        "schema_version": str(verified["schema_version"]),
        "row_count": int(verified["row_count"]),
        "validation_status": str(verified["validation_status"]),
        "source_count": len(source_rows),
        "output_dir": str(config.output_dir),
    }
