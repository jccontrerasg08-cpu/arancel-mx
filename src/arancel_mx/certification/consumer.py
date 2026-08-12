"""Read-only certification for the distributable DuckDB consumer contract."""

from __future__ import annotations

from collections.abc import Mapping
from pathlib import Path

import duckdb

from arancel_mx.domain.normalization import PUBLIC_COLUMNS
from arancel_mx.storage.duckdb import connect


_CORE_TABLES = {
    "source_document",
    "hs_code",
    "tariff_fraction",
    "nico",
    "tariff_rate",
    "canonical_record",
    "record_provenance",
    "dataset_release",
}

_CHECKS = (
    "core_objects",
    "public_columns",
    "release_metadata",
    "row_count",
    "record_ids",
    "hierarchy",
    "value_origin",
)


def _require_core_objects(connection) -> None:
    rows = connection.execute(
        """
        SELECT table_name, table_type
        FROM information_schema.tables
        WHERE table_schema = 'main'
        """
    ).fetchall()
    tables = {name for name, kind in rows if kind == "BASE TABLE"}
    views = {name for name, kind in rows if kind == "VIEW"}
    missing = sorted(_CORE_TABLES - tables)
    if "arancel_mx" not in views:
        missing.append("arancel_mx (view)")
    if missing:
        raise ValueError("missing core DuckDB objects: " + ", ".join(missing))


def _require_public_columns(connection) -> None:
    columns = [row[0] for row in connection.execute("DESCRIBE arancel_mx").fetchall()]
    if columns != list(PUBLIC_COLUMNS):
        raise ValueError("public DuckDB columns do not match PUBLIC_COLUMNS")


def _require_release_metadata(connection, manifest: Mapping[str, object]) -> int:
    release_count = int(
        connection.execute("SELECT COUNT(*) FROM dataset_release").fetchone()[0]
    )
    if release_count != 1:
        raise ValueError(
            f"public DuckDB must contain exactly one dataset_release row, got {release_count}"
        )

    row = connection.execute(
        """
        SELECT dataset_version, schema_version, ligie_version, effective_as_of,
               row_count, validation_status
        FROM dataset_release
        """
    ).fetchone()
    if row is None:
        raise ValueError("public DuckDB is missing dataset_release metadata")

    actual = {
        "dataset_version": str(row[0]),
        "schema_version": str(row[1]),
        "ligie_version": str(row[2]),
        "effective_as_of": str(row[3]),
        "validation_status": str(row[5]),
    }
    expected = {
        "dataset_version": str(manifest.get("dataset_version")),
        "schema_version": str(manifest.get("schema_version")),
        "ligie_version": str(manifest.get("ligie_version")),
        "effective_as_of": str(manifest.get("effective_as_of")),
        "validation_status": str(manifest.get("validation_status")),
    }
    if actual["validation_status"] != "passed":
        raise ValueError("public DuckDB dataset_release is not validated")
    if actual != expected:
        raise ValueError(
            f"public DuckDB release metadata mismatch: actual={actual!r} expected={expected!r}"
        )
    return int(row[4])


def _require_row_count(connection, manifest: Mapping[str, object], release_count: int) -> None:
    manifest_count = manifest.get("row_count")
    if not isinstance(manifest_count, int) or isinstance(manifest_count, bool):
        raise ValueError("manifest row count must be an integer")
    public_count = int(connection.execute("SELECT COUNT(*) FROM arancel_mx").fetchone()[0])
    if public_count != manifest_count or public_count != release_count:
        raise ValueError(
            "public DuckDB row count mismatch: "
            f"view={public_count} manifest={manifest_count} release={release_count}"
        )


def _require_record_ids(connection) -> None:
    duplicate_count, invalid_count = connection.execute(
        """
        SELECT COUNT(*) - COUNT(DISTINCT record_id),
               count(*) FILTER (
                   WHERE record_id IS NULL OR trim(record_id) = ''
               )
        FROM arancel_mx
        """
    ).fetchone()
    if int(duplicate_count) or int(invalid_count):
        raise ValueError(
            "public DuckDB record_id integrity failure: "
            f"duplicates={int(duplicate_count)} invalid={int(invalid_count)}"
        )


def _require_hierarchy(connection) -> None:
    failures = {
        "hs4_without_hs2": connection.execute(
            """
            SELECT COUNT(*) FROM arancel_mx child
            WHERE child.level='hs4' AND child.is_current
              AND NOT EXISTS (
                  SELECT 1 FROM arancel_mx parent
                  WHERE parent.level='hs2' AND parent.is_current
                    AND parent.code=child.hs2
                    AND parent.ligie_version=child.ligie_version
              )
            """
        ).fetchone()[0],
        "hs6_without_hs4": connection.execute(
            """
            SELECT COUNT(*) FROM arancel_mx child
            WHERE child.level='hs6' AND child.is_current
              AND NOT EXISTS (
                  SELECT 1 FROM arancel_mx parent
                  WHERE parent.level='hs4' AND parent.is_current
                    AND parent.code=child.hs4
                    AND parent.ligie_version=child.ligie_version
              )
            """
        ).fetchone()[0],
        "fraction_without_hs6": connection.execute(
            """
            SELECT COUNT(*) FROM arancel_mx child
            WHERE child.level='fraccion8' AND child.is_current
              AND NOT EXISTS (
                  SELECT 1 FROM arancel_mx parent
                  WHERE parent.level='hs6' AND parent.is_current
                    AND parent.code=child.hs6
                    AND parent.ligie_version=child.ligie_version
              )
            """
        ).fetchone()[0],
        "nico_without_fraction": connection.execute(
            """
            SELECT COUNT(*) FROM arancel_mx child
            WHERE child.level='nico10' AND child.is_current
              AND NOT EXISTS (
                  SELECT 1 FROM arancel_mx parent
                  WHERE parent.level='fraccion8' AND parent.is_current
                    AND parent.code=child.fraccion8
                    AND parent.ligie_version=child.ligie_version
              )
            """
        ).fetchone()[0],
    }
    failed = {name: int(value) for name, value in failures.items() if int(value)}
    if failed:
        raise ValueError(f"public DuckDB hierarchy failure: {failed}")


def _require_value_origin(connection) -> None:
    hs_values = int(
        connection.execute(
            """
            SELECT COUNT(*) FROM arancel_mx
            WHERE level IN ('hs2', 'hs4', 'hs6')
              AND (
                  values_from_level IS NOT NULL
                  OR unit_code IS NOT NULL OR unit_name IS NOT NULL
                  OR igi_text IS NOT NULL OR igi_kind IS NOT NULL OR igi_value IS NOT NULL
                  OR ige_text IS NOT NULL OR ige_kind IS NOT NULL OR ige_value IS NOT NULL
              )
            """
        ).fetchone()[0]
    )
    tariff_origin = int(
        connection.execute(
            """
            SELECT COUNT(*) FROM arancel_mx
            WHERE level IN ('fraccion8', 'nico10')
              AND values_from_level IS DISTINCT FROM 'fraccion8'
            """
        ).fetchone()[0]
    )
    if hs_values or tariff_origin:
        raise ValueError(
            "public DuckDB value origin failure: "
            f"hs_values={hs_values} tariff_origin={tariff_origin}"
        )


def certify_duckdb(
    database_path: Path,
    manifest: Mapping[str, object],
) -> tuple[str, ...]:
    """Certify the public DuckDB file without mutating it."""
    database_path = Path(database_path).resolve()
    if not database_path.is_file():
        raise ValueError(f"public DuckDB does not exist: {database_path}")
    if not isinstance(manifest, Mapping):
        raise ValueError("manifest must be a mapping")

    try:
        with connect(database_path, read_only=True) as connection:
            _require_core_objects(connection)
            _require_public_columns(connection)
            release_count = _require_release_metadata(connection, manifest)
            _require_row_count(connection, manifest, release_count)
            _require_record_ids(connection)
            _require_hierarchy(connection)
            _require_value_origin(connection)
    except duckdb.Error as exc:
        raise ValueError(f"public DuckDB is not readable: {database_path}: {exc}") from exc
    return _CHECKS
