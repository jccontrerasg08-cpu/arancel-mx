#!/usr/bin/env python3
"""Read-only chapter audit against a local verified DuckDB file.

Does not download anything and does not invent missing NICO codes or dates.

Usage:
  arancel-mx data path
  python examples/sql_chapter_audit.py /path/to/arancel_mx.duckdb 85
"""

from __future__ import annotations

import sys

import duckdb


def audit(path: str, chapter: str) -> None:
    if len(chapter) != 2 or not chapter.isdigit():
        raise SystemExit("chapter must be a two-digit HS chapter, for example 85")
    connection = duckdb.connect(path, read_only=True)
    try:
        identity = connection.execute(
            """
            SELECT dataset_version, schema_version, count(*)
            FROM arancel_mx
            WHERE is_current
            GROUP BY 1, 2
            """
        ).fetchall()
        levels = connection.execute(
            """
            SELECT level, count(*)
            FROM arancel_mx
            WHERE is_current AND hs2 = ?
            GROUP BY 1
            ORDER BY 1
            """,
            [chapter],
        ).fetchall()
        gaps = connection.execute(
            """
            SELECT
              count(*) FILTER (
                WHERE level = 'fraccion8' AND rate_effective_from IS NULL
              ) AS undated_fractions,
              count(*) FILTER (
                WHERE level = 'fraccion8'
                  AND NOT EXISTS (
                    SELECT 1 FROM arancel_mx child
                    WHERE child.is_current
                      AND child.level = 'nico10'
                      AND child.fraccion8 = arancel_mx.code
                  )
              ) AS fractions_without_nico
            FROM arancel_mx
            WHERE is_current AND hs2 = ?
            """,
            [chapter],
        ).fetchone()
    finally:
        connection.close()

    print(f"file {path}")
    for version, schema, rows in identity:
        print(f"dataset {version} schema {schema} current_rows {rows}")
    print(f"chapter {chapter}")
    for level, count in levels:
        print(f"  {level} {count}")
    if gaps is None:
        return
    print(f"undated current fractions {gaps[0]}")
    print(f"current fractions without a current NICO {gaps[1]}")
    print("Gaps are reported, not repaired.")


def main() -> None:
    if len(sys.argv) != 3:
        raise SystemExit("usage: sql_chapter_audit.py DUCKDB CHAPTER")
    audit(sys.argv[1], sys.argv[2])


if __name__ == "__main__":
    main()
