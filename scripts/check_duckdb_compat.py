"""Read a distributable arancel-mx DuckDB with the installed DuckDB runtime.

This script intentionally imports only ``duckdb`` and the standard library so CI can
run it inside an isolated environment containing an older supported DuckDB release.
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

import duckdb


def probe_database(
    database_path: Path,
    expected_row_count: int | None = None,
) -> dict[str, object]:
    """Open the public database read-only and return basic consumer evidence."""
    database_path = Path(database_path).resolve()
    if not database_path.is_file():
        raise ValueError(f"DuckDB database does not exist: {database_path}")

    with duckdb.connect(str(database_path), read_only=True) as connection:
        row_count = int(
            connection.execute("SELECT COUNT(*) FROM arancel_mx").fetchone()[0]
        )
        columns = [row[0] for row in connection.execute("DESCRIBE arancel_mx").fetchall()]
        release = connection.execute(
            """
            SELECT dataset_version, schema_version, validation_status
            FROM dataset_release
            ORDER BY generated_at DESC
            LIMIT 1
            """
        ).fetchone()

    if release is None:
        raise ValueError("public DuckDB has no dataset_release row")
    if str(release[2]) != "passed":
        raise ValueError("public DuckDB dataset_release is not validated")
    if expected_row_count is not None and row_count != expected_row_count:
        raise ValueError(
            "public DuckDB row count mismatch: "
            f"actual={row_count} expected={expected_row_count}"
        )
    if not columns:
        raise ValueError("public DuckDB arancel_mx view has no columns")

    return {
        "duckdb_version": duckdb.__version__,
        "row_count": row_count,
        "public_column_count": len(columns),
        "dataset_version": str(release[0]),
        "schema_version": str(release[1]),
    }


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Probe an arancel-mx public DuckDB using the installed DuckDB version.",
    )
    parser.add_argument("database", type=Path)
    parser.add_argument("--expected-row-count", type=int)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    result = probe_database(args.database, args.expected_row_count)
    print(json.dumps(result, sort_keys=True, separators=(",", ":")))
    return 0


if __name__ == "__main__":
    sys.exit(main())
