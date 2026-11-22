from __future__ import annotations

import os
from pathlib import Path

import duckdb

from arancel_mx.consumer import query
from tests.consumer.conftest import create_consumer_duckdb


def _codes(results) -> list[tuple[str, int, str]]:
    return [(item.record.code, item.score, item.match_kind) for item in results]


def test_repeated_searches_on_one_file_reuse_rows_and_give_the_same_answer(tmp_path: Path) -> None:
    query._SEARCH_ROWS_CACHE.clear()
    path = create_consumer_duckdb(tmp_path / "fixture.duckdb")
    with duckdb.connect(str(path), read_only=True) as conn:
        first = query.search(conn, "raza pura", limit=10)
        assert len(query._SEARCH_ROWS_CACHE) == 1
        cached = next(iter(query._SEARCH_ROWS_CACHE.values()))
        second = query.search(conn, "raza pura", limit=10)
        assert next(iter(query._SEARCH_ROWS_CACHE.values())) is cached
    with duckdb.connect(str(path), read_only=True) as other:
        third = query.search(other, "raza pura", limit=10)
    assert _codes(first) == _codes(second) == _codes(third)
    assert first and first[0].match_kind == "description"


def test_rewriting_the_file_invalidates_the_cached_rows(tmp_path: Path) -> None:
    query._SEARCH_ROWS_CACHE.clear()
    path = create_consumer_duckdb(tmp_path / "fixture.duckdb")
    with duckdb.connect(str(path), read_only=True) as conn:
        assert query.search(conn, "Reproductores", limit=5)
    with duckdb.connect(str(path)) as conn:
        conn.execute("UPDATE canonical_record SET description = 'Caballos de carrera' WHERE code = '01012101'")
    stat = path.stat()
    os.utime(path, ns=(stat.st_atime_ns, stat.st_mtime_ns + 1_000_000_000))
    with duckdb.connect(str(path), read_only=True) as conn:
        assert [item.record.code for item in query.search(conn, "carrera", limit=5)] == ["01012101"]


def test_in_memory_databases_are_never_cached() -> None:
    query._SEARCH_ROWS_CACHE.clear()
    conn = duckdb.connect()
    assert query._database_file(conn) is None


def test_cache_keeps_at_most_two_files(tmp_path: Path) -> None:
    query._SEARCH_ROWS_CACHE.clear()
    for name in ("a", "b", "c"):
        path = create_consumer_duckdb(tmp_path / f"{name}.duckdb")
        with duckdb.connect(str(path), read_only=True) as conn:
            query.search(conn, "raza", limit=1)
    assert len(query._SEARCH_ROWS_CACHE) == 2
    assert not any(key[0].endswith("a.duckdb") for key in query._SEARCH_ROWS_CACHE)
