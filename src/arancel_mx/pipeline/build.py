"""Transactional materialization of the canonical ``arancel_mx`` dataset."""

from __future__ import annotations

import csv
from datetime import date, datetime, timezone
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
from typing import Any, Mapping, Sequence

import duckdb

from arancel_mx.domain.normalization import PUBLIC_COLUMNS, canonical_json, consolidate_records
from arancel_mx.storage.duckdb import ensure_tariff_schema, init_tariff_db


PUBLIC_INTERNAL_TABLES = (
    "source_document",
    "hs_code",
    "tariff_fraction",
    "nico",
    "tariff_rate",
    "canonical_record",
    "record_provenance",
    "dataset_release",
    "nico_version",
    "nico_amendment",
    "nico_amendment_line",
    "nico_proposal_batch",
    "nico_proposal",
    "national_note",
    "national_note_version",
    "national_note_amendment",
    "national_note_applicability",
    "indicator_methodology",
    "weighted_tariff_indicator",
)

RELEASE_LEVELS = ("hs2", "hs4", "hs6", "fraccion8", "nico10")
RELEASE_METADATA_FIELDS = (
    "registry_version",
    "registry_sha256",
    "git_commit_sha",
    "github_run_id",
    "github_run_attempt",
    "github_workflow_ref",
    "github_artifact_name",
    "reconciliation",
    "source_identity",
)


def _identifier(prefix: str, row: Mapping[str, object]) -> str:
    supplied = row.get(f"{prefix}_revision_id") or row.get("classification_id")
    if supplied:
        return str(supplied)
    return hashlib.sha256(canonical_json(row).encode("utf-8")).hexdigest()


def _required(value: object, label: str) -> object:
    if value is None or (isinstance(value, str) and not value.strip()):
        raise ValueError(f"Missing required {label}")
    return value


def _validated_release_metadata(release: Mapping[str, object]) -> dict[str, object]:
    raw = _required(release.get("release_metadata"), "release.release_metadata")
    if not isinstance(raw, Mapping):
        raise ValueError("release.release_metadata must be an object")
    metadata = dict(raw)
    for field in RELEASE_METADATA_FIELDS:
        _required(metadata.get(field), f"release.release_metadata.{field}")
    reconciliation = metadata["reconciliation"]
    if not isinstance(reconciliation, Mapping):
        raise ValueError("release.release_metadata.reconciliation must be an object")
    if reconciliation.get("publishable") is not True:
        raise ValueError("release.release_metadata.reconciliation must be publishable")
    source_identity = metadata["source_identity"]
    if not isinstance(source_identity, Sequence) or isinstance(source_identity, (str, bytes)):
        raise ValueError("release.release_metadata.source_identity must be a list")
    canonical_json(metadata)
    return metadata


def _validate_inputs(
    source_documents: Sequence[Mapping[str, object]],
    classifications: Sequence[Mapping[str, object]],
    rates: Sequence[Mapping[str, object]],
    release: Mapping[str, object],
) -> tuple[dict[str, Mapping[str, object]], dict[str, object]]:
    for field in (
        "dataset_version",
        "schema_version",
        "ligie_version",
        "effective_as_of",
        "generated_at",
    ):
        _required(release.get(field), f"release.{field}")
    if not isinstance(release["effective_as_of"], date):
        raise ValueError("release.effective_as_of must be a date")
    release_metadata = _validated_release_metadata(release)

    by_id: dict[str, Mapping[str, object]] = {}
    for document in source_documents:
        source_id = str(_required(document.get("source_document_id"), "source_document_id"))
        if source_id in by_id:
            raise ValueError(f"Duplicate source document: {source_id}")
        for field in (
            "authority",
            "publication_venue",
            "title",
            "source_url",
            "sha256",
            "observed_at",
            "retrieved_at",
        ):
            _required(document.get(field), f"source_document.{field}")
        by_id[source_id] = document

    for row in [*classifications, *rates]:
        source_id = str(_required(row.get("source_document_id"), "row.source_document_id"))
        if source_id not in by_id:
            raise ValueError(f"Unknown source document: {source_id}")
    return by_id, release_metadata


def _insert_sources(
    conn: duckdb.DuckDBPyConnection,
    documents: Sequence[Mapping[str, object]],
) -> None:
    if not documents:
        return
    conn.executemany(
        """
        INSERT INTO source_document VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        [
            [
                row["source_document_id"],
                row["authority"],
                row["publication_venue"],
                row["title"],
                row["source_url"],
                row.get("media_type"),
                row["sha256"],
                row.get("local_path"),
                row.get("published_at"),
                row.get("effective_from"),
                row.get("effective_to"),
                row["observed_at"],
                row["retrieved_at"],
            ]
            for row in documents
        ],
    )


def _insert_classifications(
    conn: duckdb.DuckDBPyConnection,
    classifications: Sequence[Mapping[str, object]],
) -> None:
    hs_rows: list[list[object]] = []
    fraction_rows: list[list[object]] = []
    nico_rows: list[list[object]] = []
    for row in classifications:
        level = row["level"]
        code = str(row["code"])
        common = [
            row["description"],
            row["ligie_version"],
            row["validity_basis"],
            row.get("updated_at"),
            row.get("published_at"),
            row.get("classification_effective_from"),
            row.get("classification_effective_to"),
            row["source_document_id"],
        ]
        if level in {"hs2", "hs4", "hs6"}:
            hs_rows.append(
                [
                    _identifier("classification", row),
                    code,
                    level,
                    code[:2],
                    code[:4] if len(code) >= 4 else None,
                    code[:6] if len(code) >= 6 else None,
                    *common,
                ]
            )
        elif level == "fraccion8":
            fraction_rows.append(
                [
                    _identifier("fraction", row),
                    code,
                    code[:2],
                    code[:4],
                    code[:6],
                    *common,
                ]
            )
        elif level == "nico10":
            nico_rows.append(
                [
                    _identifier("nico", row),
                    code,
                    code[:8],
                    code[8:],
                    *common,
                ]
            )
        else:
            raise ValueError(f"Unsupported classification level: {level}")

    if hs_rows:
        conn.executemany(
            "INSERT INTO hs_code VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            hs_rows,
        )
    if fraction_rows:
        conn.executemany(
            "INSERT INTO tariff_fraction VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            fraction_rows,
        )
    if nico_rows:
        conn.executemany(
            "INSERT INTO nico VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            nico_rows,
        )


def _insert_rates(
    conn: duckdb.DuckDBPyConnection,
    rates: Sequence[Mapping[str, object]],
) -> None:
    if not rates:
        return
    conn.executemany(
        "INSERT INTO tariff_rate VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        [
            [
                _identifier("rate", row),
                row["code"],
                row.get("unit_code"),
                row.get("unit_name"),
                row.get("igi_text"),
                row.get("igi_kind"),
                row.get("igi_value"),
                row.get("ige_text"),
                row.get("ige_kind"),
                row.get("ige_value"),
                row["ligie_version"],
                row.get("updated_at"),
                row.get("published_at"),
                row.get("rate_effective_from"),
                row.get("rate_effective_to"),
                row["source_document_id"],
            ]
            for row in rates
        ],
    )


def _insert_national_notes(
    conn: duckdb.DuckDBPyConnection,
    notes: Sequence[Mapping[str, object]],
) -> None:
    for row in notes:
        note_number = str(row.get("note_number") or "").strip()
        text = str(row.get("text") or "").strip()
        source_id = str(row.get("source_document_id") or "").strip()
        if not note_number or not text or not source_id:
            raise ValueError("national notes require note_number, text, and source_document_id")
        note_id = str(
            row.get("national_note_id")
            or hashlib.sha256(canonical_json([row.get("chapter"), note_number]).encode("utf-8")).hexdigest()
        )
        conn.execute(
            "INSERT INTO national_note VALUES (?, ?, ?)",
            [note_id, row.get("chapter"), note_number],
        )
        version_id = str(
            row.get("national_note_version_id")
            or hashlib.sha256(canonical_json([note_id, text, source_id]).encode("utf-8")).hexdigest()
        )
        conn.execute(
            "INSERT INTO national_note_version VALUES (?, ?, ?, ?, ?, ?)",
            [
                version_id,
                note_id,
                text,
                row.get("effective_from"),
                row.get("effective_to"),
                source_id,
            ],
        )


def _build_view(conn: duckdb.DuckDBPyConnection) -> None:
    conn.execute(
        """
        CREATE OR REPLACE VIEW arancel_mx AS
        WITH provenance AS (
            SELECT record_id,
                   to_json(list(DISTINCT source_document_id ORDER BY source_document_id))::VARCHAR
                       AS source_document_ids_json,
                   count(DISTINCT source_document_id) AS source_count
            FROM record_provenance
            GROUP BY record_id
        )
        SELECT c.*, s.authority AS primary_source_authority,
               s.source_url AS primary_source_url,
               p.source_document_ids_json, p.source_count
        FROM canonical_record c
        JOIN source_document s
          ON s.source_document_id = c.primary_source_document_id
        JOIN provenance p ON p.record_id = c.record_id
        """
    )
    columns = [row[0] for row in conn.execute("DESCRIBE arancel_mx").fetchall()]
    if columns != list(PUBLIC_COLUMNS):
        raise ValueError(f"Public view columns do not match contract: {columns}")
    conn.execute(
        """CREATE OR REPLACE VIEW arancel_mx_national_notes AS
           SELECT n.national_note_id, n.chapter, n.note_number,
                  v.national_note_version_id, v.text, v.effective_from,
                  v.effective_to, v.source_document_id
           FROM national_note n
           JOIN national_note_version v USING (national_note_id)"""
    )


def _validate_database(conn: duckdb.DuckDBPyConnection) -> dict[str, object]:
    checks = {
        "duplicate_record_ids": conn.execute(
            "SELECT COUNT(*) - COUNT(DISTINCT record_id) FROM arancel_mx"
        ).fetchone()[0],
        "missing_required_values": conn.execute(
            """
            SELECT COUNT(*) FROM arancel_mx
            WHERE description IS NULL OR trim(description) = ''
               OR ligie_version IS NULL OR dataset_version IS NULL OR schema_version IS NULL
               OR primary_source_authority IS NULL OR trim(primary_source_authority) = ''
               OR primary_source_url IS NULL OR trim(primary_source_url) = ''
            """
        ).fetchone()[0],
        "invalid_hierarchy": conn.execute(
            """
            SELECT COUNT(*) FROM arancel_mx
            WHERE hs2 <> left(code, 2)
               OR (hs4 IS NOT NULL AND hs4 <> left(code, 4))
               OR (hs6 IS NOT NULL AND hs6 <> left(code, 6))
               OR (fraccion8 IS NOT NULL AND fraccion8 <> left(code, 8))
               OR (nico10 IS NOT NULL AND (nico10 <> code OR nico2 <> right(code, 2)))
            """
        ).fetchone()[0],
        "reversed_intervals": conn.execute(
            "SELECT COUNT(*) FROM arancel_mx WHERE effective_from > effective_to"
        ).fetchone()[0],
        "provenance_count_mismatch": conn.execute(
            """
            SELECT COUNT(*) FROM arancel_mx
            WHERE source_count <> json_array_length(source_document_ids_json)
            """
        ).fetchone()[0],
        "current_nico_without_parent": conn.execute(
            """
            SELECT COUNT(*) FROM arancel_mx n
            WHERE n.level = 'nico10' AND n.is_current
              AND NOT EXISTS (
                  SELECT 1 FROM arancel_mx f
                  WHERE f.level = 'fraccion8' AND f.code = n.fraccion8
                    AND f.ligie_version = n.ligie_version AND f.is_current
              )
            """
        ).fetchone()[0],
        "non_contiguous_versions": conn.execute(
            """
            SELECT COUNT(*) FROM (
                SELECT level, code, ligie_version, count(*) AS rows,
                       min(record_version) AS first_version,
                       max(record_version) AS last_version,
                       count(DISTINCT record_version) AS distinct_versions
                FROM arancel_mx
                GROUP BY level, code, ligie_version
                HAVING first_version <> 1 OR last_version <> rows
                    OR distinct_versions <> rows
            )
            """
        ).fetchone()[0],
        "overlapping_intervals": conn.execute(
            """
            SELECT COUNT(*) FROM (
                SELECT *, row_number() OVER timeline AS position,
                       lag(effective_to) OVER timeline AS previous_end
                FROM arancel_mx
                WINDOW timeline AS (
                    PARTITION BY level, code, ligie_version
                    ORDER BY effective_from NULLS FIRST, record_version
                )
            )
            WHERE position > 1
              AND (previous_end IS NULL OR effective_from IS NULL
                   OR effective_from <= previous_end)
            """
        ).fetchone()[0],
        "invalid_duty_values": conn.execute(
            """
            SELECT COUNT(*) FROM arancel_mx
            WHERE (igi_kind = 'prohibida' AND igi_value IS NOT NULL)
               OR (ige_kind = 'prohibida' AND ige_value IS NOT NULL)
               OR (igi_kind IN ('especifica', 'compuesta', 'desconocida') AND igi_value IS NOT NULL)
               OR (ige_kind IN ('especifica', 'compuesta', 'desconocida') AND ige_value IS NOT NULL)
            """
        ).fetchone()[0],
        "invalid_value_origin": conn.execute(
            """
            SELECT COUNT(*) FROM arancel_mx
            WHERE (level IN ('hs2', 'hs4', 'hs6') AND
                   (values_from_level IS NOT NULL OR unit_code IS NOT NULL
                    OR igi_text IS NOT NULL OR ige_text IS NOT NULL))
               OR (level IN ('fraccion8', 'nico10') AND values_from_level <> 'fraccion8')
            """
        ).fetchone()[0],
        "primary_source_count": conn.execute(
            """
            SELECT COUNT(*) FROM (
                SELECT c.record_id,
                       count(*) FILTER (WHERE p.is_primary) AS primary_count
                FROM canonical_record c
                LEFT JOIN record_provenance p ON p.record_id = c.record_id
                GROUP BY c.record_id
                HAVING primary_count <> 1
            )
            """
        ).fetchone()[0],
        "duplicate_current_records": conn.execute(
            """
            SELECT COUNT(*) FROM (
                SELECT code
                FROM arancel_mx
                WHERE is_current
                GROUP BY code
                HAVING COUNT(*) > 1
            )
            """
        ).fetchone()[0],
        "missing_public_metadata": conn.execute(
            """
            SELECT COUNT(*) FROM arancel_mx
            WHERE updated_at IS NULL OR ligie_version IS NULL
               OR dataset_version IS NULL OR schema_version IS NULL
            """
        ).fetchone()[0],
        "fraction_without_hs6_parent": conn.execute(
            """
            SELECT COUNT(*) FROM arancel_mx f
            WHERE f.level = 'fraccion8' AND f.is_current
              AND NOT EXISTS (
                  SELECT 1 FROM arancel_mx h
                  WHERE h.level = 'hs6' AND h.is_current
                    AND h.code = f.hs6 AND h.ligie_version = f.ligie_version
              )
            """
        ).fetchone()[0],
        "hs6_without_hs4_parent": conn.execute(
            """
            SELECT COUNT(*) FROM arancel_mx h6
            WHERE h6.level = 'hs6' AND h6.is_current
              AND NOT EXISTS (
                  SELECT 1 FROM arancel_mx h4
                  WHERE h4.level = 'hs4' AND h4.is_current
                    AND h4.code = h6.hs4 AND h4.ligie_version = h6.ligie_version
              )
            """
        ).fetchone()[0],
        "hs4_without_hs2_parent": conn.execute(
            """
            SELECT COUNT(*) FROM arancel_mx h4
            WHERE h4.level = 'hs4' AND h4.is_current
              AND NOT EXISTS (
                  SELECT 1 FROM arancel_mx h2
                  WHERE h2.level = 'hs2' AND h2.is_current
                    AND h2.code = h4.hs2 AND h2.ligie_version = h4.ligie_version
              )
            """
        ).fetchone()[0],
        "nico_parent_value_mismatch": conn.execute(
            """
            SELECT COUNT(*) FROM arancel_mx n
            JOIN arancel_mx f ON f.level = 'fraccion8' AND f.is_current
              AND f.code = n.fraccion8 AND f.ligie_version = n.ligie_version
            WHERE n.level = 'nico10' AND n.is_current
              AND (n.unit_code IS DISTINCT FROM f.unit_code
                OR n.unit_name IS DISTINCT FROM f.unit_name
                OR n.igi_text IS DISTINCT FROM f.igi_text
                OR n.igi_kind IS DISTINCT FROM f.igi_kind
                OR n.igi_value IS DISTINCT FROM f.igi_value
                OR n.ige_text IS DISTINCT FROM f.ige_text
                OR n.ige_kind IS DISTINCT FROM f.ige_kind
                OR n.ige_value IS DISTINCT FROM f.ige_value)
            """
        ).fetchone()[0],
    }
    failed = {name: int(count) for name, count in checks.items() if count}
    if failed:
        raise ValueError(f"Canonical database validation failed: {failed}")
    return {
        "status": "passed",
        "checks": {name: int(value) for name, value in checks.items()},
    }


def _release_level_counts(conn: duckdb.DuckDBPyConnection) -> dict[str, int]:
    counts = dict(
        conn.execute("SELECT level, COUNT(*) FROM arancel_mx GROUP BY level").fetchall()
    )
    return {level: int(counts.get(level, 0)) for level in RELEASE_LEVELS}


def materialize_arancel(
    conn: duckdb.DuckDBPyConnection,
    source_documents: Sequence[Mapping[str, object]],
    classifications: Sequence[Mapping[str, object]],
    rates: Sequence[Mapping[str, object]],
    release: Mapping[str, object],
    national_notes: Sequence[Mapping[str, object]] = (),
) -> dict[str, object]:
    """Replace canonical data only after the complete candidate validates."""
    documents_by_id, release_metadata = _validate_inputs(
        source_documents,
        classifications,
        rates,
        release,
    )
    records = consolidate_records(list(classifications), list(rates), release)
    rate_source_ids = {str(row["source_document_id"]) for row in rates}
    nico_source_ids = {
        str(row["source_document_id"])
        for row in classifications
        if row.get("level") == "nico10"
    }

    conn.execute("BEGIN TRANSACTION")
    try:
        ensure_tariff_schema(conn)
        conn.execute("DROP VIEW IF EXISTS arancel_mx")
        conn.execute("DROP VIEW IF EXISTS arancel_mx_national_notes")
        for table in reversed(PUBLIC_INTERNAL_TABLES):
            conn.execute(f"DELETE FROM {table}")
        _insert_sources(conn, source_documents)
        _insert_classifications(conn, classifications)
        _insert_rates(conn, rates)
        _insert_national_notes(conn, national_notes)

        canonical_rows: list[list[object]] = []
        provenance_rows: list[list[object]] = []
        for row in records:
            primary_id = str(row["primary_source_document_id"])
            primary = documents_by_id[primary_id]
            row["observed_at"] = primary["observed_at"]
            row["retrieved_at"] = primary["retrieved_at"]
            canonical_rows.append([row[column] for column in PUBLIC_COLUMNS[:40]])
            source_ids = json.loads(str(row["source_document_ids_json"]))
            for source_id in source_ids:
                if source_id in nico_source_ids and row["level"] == "nico10":
                    role = "nico"
                elif source_id in rate_source_ids:
                    role = "rate"
                else:
                    role = "base"
                provenance_rows.append(
                    [row["record_id"], source_id, role, source_id == primary_id]
                )

        if canonical_rows:
            placeholders = ", ".join("?" for _ in PUBLIC_COLUMNS[:40])
            conn.executemany(
                f"INSERT INTO canonical_record VALUES ({placeholders})",
                canonical_rows,
            )
        if provenance_rows:
            conn.executemany(
                "INSERT INTO record_provenance VALUES (?, ?, ?, ?)",
                provenance_rows,
            )
        _build_view(conn)
        validation = _validate_database(conn)
        row_count = int(conn.execute("SELECT COUNT(*) FROM arancel_mx").fetchone()[0])
        source_documents_json = canonical_json(
            [
                {
                    key: value
                    for key, value in documents_by_id[source_id].items()
                    if key != "local_path"
                }
                for source_id in sorted(documents_by_id)
            ]
        )
        stored_metadata = dict(release_metadata)
        stored_metadata["level_counts"] = _release_level_counts(conn)
        conn.execute(
            "INSERT INTO dataset_release VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                release["dataset_version"],
                release["schema_version"],
                release["ligie_version"],
                release["effective_as_of"],
                release["generated_at"],
                row_count,
                "passed",
                canonical_json(validation),
                source_documents_json,
                canonical_json(stored_metadata),
            ],
        )
        conn.execute("COMMIT")
    except Exception:
        conn.execute("ROLLBACK")
        raise

    return {
        "dataset_version": release["dataset_version"],
        "row_count": row_count,
        "validation_status": "passed",
        "validation_results": validation,
        "release_metadata": stored_metadata,
    }


def _decimal_text(value: Decimal) -> str:
    text = format(value, "f")
    return text.rstrip("0").rstrip(".") if "." in text else text


def _timestamp_text(value: datetime) -> str:
    if value.tzinfo is None:
        value = value.replace(tzinfo=timezone.utc)
    return (
        value.astimezone(timezone.utc)
        .replace(microsecond=0)
        .isoformat()
        .replace("+00:00", "Z")
    )


def _json_text(value: object) -> str:
    if value is None:
        return "null"
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, Decimal):
        return _decimal_text(value)
    if isinstance(value, datetime):
        return json.dumps(_timestamp_text(value), ensure_ascii=False)
    if isinstance(value, date):
        return json.dumps(value.isoformat())
    if isinstance(value, (int, float)):
        return str(value)
    if isinstance(value, str):
        return json.dumps(value, ensure_ascii=False)
    if isinstance(value, Mapping):
        return "{" + ",".join(
            f"{json.dumps(str(key), ensure_ascii=False)}:{_json_text(item)}"
            for key, item in value.items()
        ) + "}"
    if isinstance(value, Sequence):
        return "[" + ",".join(_json_text(item) for item in value) + "]"
    raise TypeError(f"Unsupported JSON value: {type(value).__name__}")


def _csv_text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, Decimal):
        return _decimal_text(value)
    if isinstance(value, datetime):
        return _timestamp_text(value)
    if isinstance(value, date):
        return value.isoformat()
    return str(value)


def _sha256(path: Path) -> str:
    with path.open("rb") as stream:
        return hashlib.file_digest(stream, "sha256").hexdigest()


def _create_public_database(source_path: Path, target_path: Path) -> None:
    """Copy only canonical tariff tables into the distributable DuckDB."""
    init_tariff_db(target_path)
    with duckdb.connect(str(target_path)) as conn:
        escaped_source = str(source_path).replace("'", "''")
        conn.execute(f"ATTACH '{escaped_source}' AS upstream (READ_ONLY)")
        for table in PUBLIC_INTERNAL_TABLES:
            conn.execute(f"INSERT INTO {table} SELECT * FROM upstream.{table}")
        unwanted = [
            row[0]
            for row in conn.execute(
                """
                SELECT table_name FROM information_schema.tables
                WHERE table_catalog=current_database()
                  AND table_schema='main' AND table_type='BASE TABLE'
                """
            ).fetchall()
            if row[0] not in PUBLIC_INTERNAL_TABLES
        ]
        for table in unwanted:
            conn.execute(f'DROP TABLE "{table}"')
        conn.execute("DETACH upstream")
        _build_view(conn)
        conn.execute(
            """CREATE OR REPLACE VIEW nico_proposals AS
               SELECT p.*, b.observed_at, b.published_at, b.source_document_id,
                      b.source_sha256
               FROM nico_proposal p
               JOIN nico_proposal_batch b USING (proposal_batch_id)"""
        )
        conn.execute(
            """CREATE OR REPLACE VIEW arancel_mx_weighted_indicators AS
               SELECT i.*, m.title AS methodology_title, m.version AS methodology_version,
                      m.extraction_status, m.formula_json
               FROM weighted_tariff_indicator i
               LEFT JOIN indicator_methodology m USING (methodology_id)"""
        )


def _export_arancel_release(
    database_path: Path | str,
    output_dir: Path | str,
) -> dict[str, object]:
    """Export one immutable, cross-format-equivalent canonical release."""
    database_path = Path(database_path).resolve()
    output_dir = Path(output_dir).resolve()
    if output_dir.exists():
        raise FileExistsError(f"Release directory already exists: {output_dir}")
    output_dir.mkdir(parents=True)

    order = (
        "ORDER BY code, effective_from NULLS FIRST, effective_to NULLS LAST, "
        "record_version, record_id"
    )
    with duckdb.connect(str(database_path), read_only=True) as conn:
        columns = [row[0] for row in conn.execute("DESCRIBE arancel_mx").fetchall()]
        if columns != list(PUBLIC_COLUMNS):
            raise ValueError("Cannot export a database with a non-canonical arancel_mx view")
        tuples = conn.execute(f"SELECT * FROM arancel_mx {order}").fetchall()
        rows = [dict(zip(columns, values, strict=True)) for values in tuples]
        release_row = conn.execute(
            """
            SELECT dataset_version, schema_version, ligie_version, effective_as_of,
                   generated_at, row_count, validation_status, validation_results_json,
                   release_metadata_json
            FROM dataset_release ORDER BY generated_at DESC LIMIT 1
            """
        ).fetchone()
        if release_row is None or release_row[6] != "passed":
            raise ValueError("Only a validated dataset release can be exported")
        release_metadata = json.loads(release_row[8])
        if not isinstance(release_metadata, dict):
            raise ValueError("Release metadata is not a JSON object")
        source_columns = [
            row[0] for row in conn.execute("DESCRIBE source_document").fetchall()
        ]
        source_rows = conn.execute(
            "SELECT * FROM source_document ORDER BY source_document_id"
        ).fetchall()
        sources = [
            {
                key: value
                for key, value in zip(source_columns, values, strict=True)
                if key != "local_path"
            }
            for values in source_rows
        ]

    if int(release_row[5]) != len(rows):
        raise ValueError("Release row count does not match arancel_mx")

    duckdb_path = output_dir / "arancel_mx.duckdb"
    csv_path = output_dir / "arancel_mx.csv"
    json_path = output_dir / "arancel_mx.json"
    _create_public_database(database_path, duckdb_path)
    with csv_path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.writer(stream, lineterminator="\r\n")
        writer.writerow(columns)
        writer.writerows([_csv_text(row[column]) for column in columns] for row in rows)
    json_path.write_text(_json_text(rows) + "\n", encoding="utf-8", newline="")

    with csv_path.open("r", encoding="utf-8", newline="") as stream:
        csv_rows = list(csv.reader(stream))
    json_rows = json.loads(json_path.read_text(encoding="utf-8"), parse_float=Decimal)
    if (
        csv_rows[0] != columns
        or len(csv_rows) - 1 != len(rows)
        or len(json_rows) != len(rows)
    ):
        raise ValueError("Exported formats differ in columns or row count")
    expected_csv = [[_csv_text(row[column]) for column in columns] for row in rows]
    if csv_rows[1:] != expected_csv:
        raise ValueError("CSV values differ from the DuckDB view")
    if [list(row) for row in json_rows] != [columns for _ in rows]:
        raise ValueError("JSON key order differs from the canonical contract")
    if [row["record_id"] for row in json_rows] != [row["record_id"] for row in rows]:
        raise ValueError("JSON keys differ from the DuckDB view")
    if [row["record_hash"] for row in json_rows] != [row["record_hash"] for row in rows]:
        raise ValueError("JSON record hashes differ from the DuckDB view")

    artifact_hashes = {
        path.name: _sha256(path) for path in (duckdb_path, csv_path, json_path)
    }
    manifest: dict[str, Any] = {
        "dataset_version": release_row[0],
        "schema_version": release_row[1],
        "ligie_version": release_row[2],
        "effective_as_of": release_row[3],
        "generated_at": release_row[4],
        "row_count": len(rows),
        "validation_status": release_row[6],
        "validation_results": json.loads(release_row[7]) if release_row[7] else None,
        "source_documents": sources,
        "artifact_sha256": artifact_hashes,
    }
    for field in (
        "registry_version",
        "registry_sha256",
        "git_commit_sha",
        "github_run_id",
        "github_run_attempt",
        "github_workflow_ref",
        "github_artifact_name",
        "level_counts",
        "reconciliation",
        "source_identity",
    ):
        if field not in release_metadata:
            raise ValueError(f"Release metadata missing {field}")
        manifest[field] = release_metadata[field]

    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(
        _json_text(manifest) + "\n",
        encoding="utf-8",
        newline="",
    )
    checksum_paths = [duckdb_path, csv_path, json_path, manifest_path]
    checksum_lines = [f"{_sha256(path)}  {path.name}\r\n" for path in checksum_paths]
    (output_dir / "SHA256SUMS").write_text(
        "".join(checksum_lines),
        encoding="ascii",
        newline="",
    )
    return manifest


def export_arancel_release(
    database_path: Path | str,
    output_dir: Path | str,
) -> dict[str, object]:
    """Stage a complete release, then publish its directory atomically."""
    final_dir = Path(output_dir).resolve()
    if final_dir.exists():
        raise FileExistsError(f"Release directory already exists: {final_dir}")
    final_dir.parent.mkdir(parents=True, exist_ok=True)
    staging = Path(tempfile.mkdtemp(prefix=f".{final_dir.name}-", dir=final_dir.parent))
    staging.rmdir()
    try:
        manifest = _export_arancel_release(database_path, staging)
        staging.replace(final_dir)
        return manifest
    except Exception:
        if staging.exists():
            shutil.rmtree(staging)
        raise
