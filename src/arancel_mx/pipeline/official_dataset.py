"""End-to-end construction of the first canonical dataset from official sources."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any

from arancel_mx.parsers.documents import parse_ligie_pdf_hierarchy
from arancel_mx.parsers.profiles import resolve_workbook_profile
from arancel_mx.parsers.workbooks import (
    parse_ligie_workbook,
    parse_nico_workbook,
    probe_workbook,
)
from arancel_mx.pipeline.build import export_arancel_release, materialize_arancel
from arancel_mx.pipeline.hierarchy import assemble_classifications
from arancel_mx.pipeline.official_sources import (
    capture_official_inputs,
    write_release_sources,
)
from arancel_mx.release.package import (
    prepare_release_archive,
    verify_release,
    verify_sources,
)
from arancel_mx.storage.duckdb import connect, init_tariff_db


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


def _build_timestamp(value: datetime) -> datetime:
    if value.tzinfo is None or value.utcoffset() is None:
        raise ValueError("generated_at must be timezone-aware")
    return value.astimezone(timezone.utc).replace(microsecond=0)


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

    snapshot = capture_official_inputs(config, session=session)
    sources_by_key = {source.dataset_key: source for source in snapshot.sources}
    ligie_source = sources_by_key["ligie"]
    nico_source = sources_by_key["nico"]
    diputados_source = sources_by_key["diputados_ligie"]

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
        (item.source_document for item in snapshot.sources),
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
    source_dir = write_release_sources(config, snapshot.sources)
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
