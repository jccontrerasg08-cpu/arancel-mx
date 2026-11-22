"""Local Parquet or SQLite export of the public views of one dataset release.

The export is a derived convenience copy for analytics tools. It is not one of
the six canonical release assets and never replaces them: the manifest written
next to the files names the DuckDB it came from, its SHA-256, whether that
release passed remote verification, and the SHA-256 and row count of every
Parquet file. Column types are kept as DuckDB stores them, so rate text stays
text, NULL stays NULL and dates stay dates.
"""

from __future__ import annotations

import hashlib
import json
import sqlite3
from collections.abc import Mapping
from datetime import date, datetime
from decimal import Decimal
from pathlib import Path
from typing import Any

EXPORT_POLICY_VERSION = "parquet-export-v1"

# Public views exported when the release ships them, with a stable sort key so
# two exports of the same release hold the rows in the same order.
EXPORT_VIEWS: tuple[tuple[str, str], ...] = (
    ("arancel_mx", "code, record_version"),
    ("arancel_mx_nom_requirements", "ALL"),
    ("arancel_mx_national_notes", "ALL"),
    ("arancel_mx_weighted_indicators", "ALL"),
)

NOT_A_RELEASE_ASSET = (
    "Derived local copy of the public views. It is not a canonical release asset: "
    "verify the release itself (manifest.json and SHA256SUMS) before relying on it."
)


def sha256_file(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        for block in iter(lambda: handle.read(1 << 20), b""):
            digest.update(block)
    return digest.hexdigest()


def _present_views(connection: Any) -> set[str]:
    rows = connection.execute(
        "SELECT table_name FROM information_schema.tables WHERE table_type = 'VIEW'"
    ).fetchall()
    return {str(row[0]) for row in rows}


def _quote_path(path: Path) -> str:
    return "'" + str(path).replace("'", "''") + "'"


def export_parquet(
    connection: Any,
    out_dir: Path,
    *,
    source_path: Path,
    info: Mapping[str, object],
) -> dict[str, object]:
    """Write one Parquet file per public view and return the export manifest.

    ``out_dir`` must not exist or must be empty, so an export never mixes files
    from two releases. Views the release does not ship are listed as skipped,
    not written as empty files.
    """

    if out_dir.exists() and any(out_dir.iterdir()):
        raise FileExistsError(f"{out_dir} is not empty")
    out_dir.mkdir(parents=True, exist_ok=True)
    present = _present_views(connection)
    files: list[dict[str, object]] = []
    skipped: list[dict[str, str]] = []
    for view, order in EXPORT_VIEWS:
        if view not in present:
            skipped.append({"view": view, "reason": "view not present in this release"})
            continue
        target = out_dir / f"{view}.parquet"
        connection.execute(
            # view and order come from EXPORT_VIEWS, never from user input.
            f"COPY (SELECT * FROM {view} ORDER BY {order}) TO {_quote_path(target)} "  # noqa: S608
            "(FORMAT PARQUET, COMPRESSION ZSTD)"
        )
        rows = connection.execute(f"SELECT count(*) FROM {view}").fetchone()[0]  # noqa: S608
        files.append(
            {
                "view": view,
                "path": target.name,
                "rows": int(rows),
                "sha256": sha256_file(target),
            }
        )
    manifest: dict[str, object] = {
        "policy_version": EXPORT_POLICY_VERSION,
        "format": "parquet",
        "dataset_version": info.get("dataset_version"),
        "release_verified": bool(info.get("release_verified")),
        "source": {"file": source_path.name, "sha256": sha256_file(source_path)},
        "files": files,
        "skipped": skipped,
        "note": NOT_A_RELEASE_ASSET,
    }
    (out_dir / "export-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return manifest


SQLITE_FILE = "arancel_mx.sqlite"
COLUMNS_TABLE = "_export_columns"


def _sqlite_type(duckdb_type: str) -> str:
    """SQLite storage for one DuckDB column type; anything exact or dated stays text."""

    kind = duckdb_type.upper()
    if kind in {"TINYINT", "SMALLINT", "INTEGER", "BIGINT", "BOOLEAN"}:
        return "INTEGER"
    if kind in {"FLOAT", "DOUBLE", "REAL"}:
        return "REAL"
    # VARCHAR, DECIMAL (kept as its exact text, never a float), DATE and TIMESTAMP (ISO 8601).
    return "TEXT"


def _sqlite_value(value: object) -> object:
    if value is None or isinstance(value, (str, int, float)):
        return int(value) if isinstance(value, bool) else value
    if isinstance(value, Decimal):
        return format(value, "f")
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    return str(value)


def _quote_identifier(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def export_sqlite(
    connection: Any,
    out_dir: Path,
    *,
    source_path: Path,
    info: Mapping[str, object],
) -> dict[str, object]:
    """Write the public views into one SQLite file and return the export manifest.

    Text, NULL, integers and booleans keep their values; DECIMAL is stored as its exact
    text and DATE/TIMESTAMP as ISO 8601 text, so no rate or date is rounded or reformatted
    by a float. The mapping is written into the file itself, in ``_export_columns``.
    """

    if out_dir.exists() and any(out_dir.iterdir()):
        raise FileExistsError(f"{out_dir} is not empty")
    out_dir.mkdir(parents=True, exist_ok=True)
    present = _present_views(connection)
    target = out_dir / SQLITE_FILE
    files: list[dict[str, object]] = []
    skipped: list[dict[str, str]] = []
    database = sqlite3.connect(target)
    try:
        database.execute(
            f"CREATE TABLE {COLUMNS_TABLE} (view TEXT NOT NULL, position INTEGER NOT NULL, "
            "column_name TEXT NOT NULL, duckdb_type TEXT NOT NULL, sqlite_type TEXT NOT NULL)"
        )
        for view, order in EXPORT_VIEWS:
            if view not in present:
                skipped.append(
                    {"view": view, "reason": "view not present in this release"}
                )
                continue
            columns = [
                (str(row[0]), str(row[1]))
                for row in connection.execute(
                    f"DESCRIBE SELECT * FROM {view}"  # noqa: S608
                ).fetchall()
            ]
            definition = ", ".join(
                f"{_quote_identifier(name)} {_sqlite_type(kind)}"
                for name, kind in columns
            )
            database.execute(f"CREATE TABLE {_quote_identifier(view)} ({definition})")
            database.executemany(
                f"INSERT INTO {COLUMNS_TABLE} VALUES (?, ?, ?, ?, ?)",  # noqa: S608
                [
                    (view, index, name, kind, _sqlite_type(kind))
                    for index, (name, kind) in enumerate(columns)
                ],
            )
            # view and order come from EXPORT_VIEWS, never from user input.
            rows = connection.execute(
                f"SELECT * FROM {view} ORDER BY {order}"  # noqa: S608
            ).fetchall()
            placeholders = ", ".join("?" for _ in columns)
            database.executemany(
                f"INSERT INTO {_quote_identifier(view)} VALUES ({placeholders})",  # noqa: S608
                [tuple(_sqlite_value(value) for value in row) for row in rows],
            )
            files.append(
                {"view": view, "path": SQLITE_FILE, "table": view, "rows": len(rows)}
            )
        database.commit()
    finally:
        database.close()
    manifest: dict[str, object] = {
        "policy_version": EXPORT_POLICY_VERSION,
        "format": "sqlite",
        "dataset_version": info.get("dataset_version"),
        "release_verified": bool(info.get("release_verified")),
        "source": {"file": source_path.name, "sha256": sha256_file(source_path)},
        "database": {"path": SQLITE_FILE, "sha256": sha256_file(target)},
        "files": files,
        "skipped": skipped,
        "note": NOT_A_RELEASE_ASSET,
    }
    (out_dir / "export-manifest.json").write_text(
        json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return manifest
