"""End-to-end construction of the canonical dataset from official sources."""

from __future__ import annotations

from collections import Counter
from collections.abc import Mapping
from dataclasses import asdict, dataclass
from datetime import date, datetime, timezone
from pathlib import Path
from typing import Any, Literal

from arancel_mx.parsers.documents import (
    parse_ligie_pdf_hierarchy,
    parse_national_notes_html,
)
from arancel_mx.parsers.profiles import resolve_workbook_profile
from arancel_mx.parsers.workbooks import (
    parse_ligie_workbook,
    parse_nico_workbook,
    probe_workbook,
)
from arancel_mx.pipeline.build import export_arancel_release, materialize_arancel
from arancel_mx.pipeline.hierarchy import assemble_classifications
from arancel_mx.pipeline.nico_coverage import nico_coverage_report
from arancel_mx.pipeline.official_sources import (
    OfficialInputSnapshot,
    capture_official_inputs,
    write_release_sources,
)
from arancel_mx.release.metadata import (
    ReleaseProvenance,
    source_identity_changed,
    source_identity_from_manifest,
)
from arancel_mx.release.package import (
    prepare_release_archive,
    verify_release,
    verify_sources,
)
from arancel_mx.sources.http import decode_fetched_text
from arancel_mx.storage.duckdb import connect, init_tariff_db


RELEASE_LEVELS = ("hs2", "hs4", "hs6", "fraccion8", "nico10")
_LEGACY_BASELINE_VERSION = "2026.08.10"


@dataclass(frozen=True)
class OfficialDatasetConfig:
    work_dir: Path
    output_dir: Path
    effective_as_of: date
    dataset_version: str
    generated_at: datetime
    schema_version: str = "2"
    ligie_version: str = "LIGIE-2022"
    timeout_s: float = 60.0
    git_commit_sha: str = "local"
    github_run_id: str = "local"
    github_run_attempt: str = "local"
    github_workflow_ref: str = "local"
    github_artifact_name: str = "local"

    def provenance(self) -> ReleaseProvenance:
        return ReleaseProvenance(
            git_commit_sha=self.git_commit_sha,
            github_run_id=self.github_run_id,
            github_run_attempt=self.github_run_attempt,
            github_workflow_ref=self.github_workflow_ref,
            github_artifact_name=self.github_artifact_name,
        )


@dataclass(frozen=True)
class OfficialBuildResult:
    status: Literal["no_change", "built"]
    dataset_version: str
    schema_version: str
    row_count: int
    validation_status: str
    source_count: int
    output_dir: str | None

    def to_dict(self) -> dict[str, object]:
        return asdict(self)


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
        has_tariff_values = any(
            value not in (None, "")
            for value in (
                normalized.get("igi_text"),
                normalized.get("ige_text"),
                normalized.get("igi_value"),
                normalized.get("ige_value"),
            )
        )
        if has_tariff_values:
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


def _level_counts(classifications: list[dict[str, object]]) -> dict[str, int]:
    counts = Counter(str(row["level"]) for row in classifications)
    return {level: int(counts.get(level, 0)) for level in RELEASE_LEVELS}


def _required_source(
    snapshot: OfficialInputSnapshot,
    dataset_key: str,
    document_role: str,
):
    matches = [
        source
        for source in snapshot.sources
        if source.dataset_key == dataset_key and source.document_role == document_role
    ]
    if len(matches) != 1:
        raise ValueError(
            "official snapshot must contain exactly one source "
            f"{dataset_key}/{document_role}; found {len(matches)}"
        )
    return matches[0]


def _release_metadata(
    config: OfficialDatasetConfig,
    snapshot: OfficialInputSnapshot,
    classifications: list[dict[str, object]],
) -> dict[str, object]:
    metadata: dict[str, object] = {
        "registry_version": snapshot.registry_version,
        "registry_sha256": snapshot.registry_sha256,
        **config.provenance().to_dict(),
        "level_counts": _level_counts(classifications),
        "reconciliation": asdict(snapshot.reconciliation),
        "nico_coverage": nico_coverage_report(
            classifications,
            [identity.to_dict() for identity in snapshot.identities],
        ),
        "source_identity": [
            identity.to_dict()
            for identity in sorted(
                snapshot.identities,
                key=lambda item: (
                    item.dataset_key,
                    item.document_role,
                    item.source_url,
                    item.sha256,
                    item.registry_version,
                ),
            )
        ],
    }
    return metadata


def _no_change_result(
    config: OfficialDatasetConfig,
    previous_manifest: Mapping[str, object],
    source_count: int,
) -> dict[str, object]:
    validation_status = str(previous_manifest.get("validation_status", ""))
    if validation_status != "passed":
        raise ValueError("previous manifest must describe a passed release")
    row_count = previous_manifest.get("row_count")
    if not isinstance(row_count, int) or isinstance(row_count, bool) or row_count <= 0:
        raise ValueError("previous manifest must contain a positive row_count")
    return OfficialBuildResult(
        status="no_change",
        dataset_version=config.dataset_version,
        schema_version=config.schema_version,
        row_count=row_count,
        validation_status=validation_status,
        source_count=source_count,
        output_dir=None,
    ).to_dict()


def _is_legacy_baseline(previous_manifest: Mapping[str, object]) -> bool:
    status = previous_manifest.get("baseline_status")
    if status != "legacy_baseline":
        return False
    if (
        previous_manifest.get("dataset_version") != _LEGACY_BASELINE_VERSION
        or previous_manifest.get("schema_version") != "1"
        or previous_manifest.get("validation_status") != "passed"
    ):
        raise ValueError("invalid legacy_baseline manifest marker")
    row_count = previous_manifest.get("row_count")
    if not isinstance(row_count, int) or isinstance(row_count, bool) or row_count <= 0:
        raise ValueError("invalid legacy_baseline manifest row_count")
    return True


def build_official_dataset(
    config: OfficialDatasetConfig,
    session: Any | None = None,
    previous_manifest: Mapping[str, object] | None = None,
) -> dict[str, object]:
    """Build one verified release, or stop after a reconciled no-change check."""
    if config.timeout_s <= 0:
        raise ValueError("timeout_s must be positive")
    generated_at = _build_timestamp(config.generated_at)
    if config.work_dir.exists() and any(config.work_dir.iterdir()):
        raise FileExistsError(f"Work directory is not empty: {config.work_dir}")
    if config.output_dir.exists():
        raise FileExistsError(f"Output directory already exists: {config.output_dir}")
    config.work_dir.mkdir(parents=True, exist_ok=True)

    # capture_official_inputs() includes the mandatory legal reconciliation gate.
    # Only a successfully reconciled current snapshot is eligible for no-change.
    snapshot = capture_official_inputs(config, session=session)
    if previous_manifest is not None and not _is_legacy_baseline(previous_manifest):
        previous_identity = source_identity_from_manifest(previous_manifest)
        if not source_identity_changed(snapshot.identities, previous_identity):
            return _no_change_result(
                config,
                previous_manifest,
                source_count=len(snapshot.identities),
            )

    # A marked schema-v1 baseline deliberately reaches the full build. The schema
    # and provenance upgrade itself is a meaningful release change even if tariff
    # rows would otherwise be logically identical.
    ligie_source = _required_source(snapshot, "ligie", "ligie_snapshot")
    nico_source = _required_source(snapshot, "nico", "nico_snapshot")
    diputados_source = _required_source(
        snapshot, "diputados_ligie", "consolidated_text"
    )
    notes_source = _required_source(snapshot, "national_notes", "national_notes")
    national_notes = parse_national_notes_html(
        decode_fetched_text(notes_source.fetched),
        str(notes_source.source_document["source_document_id"]),
    )

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
        "release_metadata": _release_metadata(config, snapshot, classifications),
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
            national_notes=national_notes,
        )
        level_counts = dict(
            connection.execute(
                "SELECT level, COUNT(*) FROM arancel_mx GROUP BY level"
            ).fetchall()
        )
        duty_counts = connection.execute(
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
        if duty_counts is None:
            raise ValueError("canonical duty-count query returned no row")
        igi_count, ige_count = duty_counts
    row_count = build_summary.get("row_count")
    if not isinstance(row_count, int) or isinstance(row_count, bool) or row_count <= 0:
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

    return OfficialBuildResult(
        status="built",
        dataset_version=str(verified["dataset_version"]),
        schema_version=str(verified["schema_version"]),
        row_count=int(verified["row_count"]),
        validation_status=str(verified["validation_status"]),
        source_count=len(source_rows),
        output_dir=str(config.output_dir),
    ).to_dict()
