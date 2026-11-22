from __future__ import annotations

import json
import sqlite3
from pathlib import Path

import duckdb
import pytest

from arancel_mx.cli import build_parser, main
from arancel_mx.consumer.export import (
    EXPORT_VIEWS,
    export_parquet,
    export_sqlite,
    sha256_file,
)
from tests.consumer.conftest import create_consumer_duckdb


def _export(
    tmp_path: Path, source: Path, *, verified: bool = False
) -> tuple[Path, dict[str, object]]:
    out = tmp_path / "export"
    with duckdb.connect(str(source), read_only=True) as conn:
        manifest = export_parquet(
            conn,
            out,
            source_path=source,
            info={"dataset_version": "2026.08.11", "release_verified": verified},
        )
    return out, manifest


def test_parquet_rows_are_identical_to_the_release_view(tmp_path: Path) -> None:
    source = create_consumer_duckdb(tmp_path / "arancel_mx.duckdb")
    with duckdb.connect(str(source)) as conn:
        # A rate that is not a number and a value the release does not publish.
        conn.execute(
            "UPDATE canonical_record SET igi_text = 'Ex.' WHERE code = '01012101'"
        )
        conn.execute(
            "UPDATE canonical_record SET ige_text = NULL WHERE code = '01012101'"
        )
    out, manifest = _export(tmp_path, source)
    target = out / "arancel_mx.parquet"
    with duckdb.connect(str(source), read_only=True) as conn:
        conn.execute(
            "CREATE TEMP TABLE exported AS SELECT * FROM read_parquet(?)", [str(target)]
        )
        only_view = conn.execute(
            "SELECT count(*) FROM (SELECT * FROM arancel_mx EXCEPT ALL SELECT * FROM exported)"
        ).fetchone()[0]
        only_file = conn.execute(
            "SELECT count(*) FROM (SELECT * FROM exported EXCEPT ALL SELECT * FROM arancel_mx)"
        ).fetchone()[0]
        view_types = conn.execute("DESCRIBE SELECT * FROM arancel_mx").fetchall()
        file_types = conn.execute("DESCRIBE SELECT * FROM exported").fetchall()
        rates = conn.execute(
            "SELECT igi_text, ige_text FROM exported WHERE code = '01012101'"
        ).fetchall()
    assert (only_view, only_file) == (0, 0)
    assert [(c[0], c[1]) for c in file_types] == [(c[0], c[1]) for c in view_types]
    assert rates == [("Ex.", None)]
    entry = next(f for f in manifest["files"] if f["view"] == "arancel_mx")
    assert entry["sha256"] == sha256_file(target)


def test_manifest_names_the_source_and_never_claims_verification(
    tmp_path: Path,
) -> None:
    source = create_consumer_duckdb(tmp_path / "arancel_mx.duckdb")
    out, manifest = _export(tmp_path, source)
    assert manifest["release_verified"] is False
    assert manifest["source"] == {
        "file": "arancel_mx.duckdb",
        "sha256": sha256_file(source),
    }
    assert "not a canonical release asset" in str(manifest["note"])
    assert (
        json.loads((out / "export-manifest.json").read_text(encoding="utf-8"))
        == manifest
    )
    exported = {f["view"] for f in manifest["files"]}
    skipped = {s["view"] for s in manifest["skipped"]}
    # Every known view is either written or listed with the reason it was not.
    assert exported | skipped == {view for view, _ in EXPORT_VIEWS}
    assert exported.isdisjoint(skipped)
    for view in skipped:
        assert not (out / f"{view}.parquet").exists()


def test_export_is_deterministic(tmp_path: Path) -> None:
    source = create_consumer_duckdb(tmp_path / "arancel_mx.duckdb")
    _, first = _export(tmp_path / "a", source)
    _, second = _export(tmp_path / "b", source)
    assert first["files"] == second["files"]


def test_export_refuses_a_directory_that_already_has_files(tmp_path: Path) -> None:
    source = create_consumer_duckdb(tmp_path / "arancel_mx.duckdb")
    out = tmp_path / "export"
    out.mkdir()
    (out / "old.parquet").write_bytes(b"older release")
    with (
        duckdb.connect(str(source), read_only=True) as conn,
        pytest.raises(FileExistsError),
    ):
        export_parquet(conn, out, source_path=source, info={})
    assert sorted(p.name for p in out.iterdir()) == ["old.parquet"]


def test_cli_exports_a_local_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    source = create_consumer_duckdb(tmp_path / "arancel_mx.duckdb")
    out = tmp_path / "parquet"
    namespace = build_parser().parse_args(
        ["data", "export", "--dataset", str(source), "--out", str(out)]
    )
    assert namespace.consumer_action == "data_export"
    assert (
        main(
            [
                "data",
                "export",
                "--dataset",
                str(source),
                "--out",
                str(out),
                "--format",
                "json",
            ]
        )
        == 0
    )
    manifest = json.loads(capsys.readouterr().out)
    assert manifest["release_verified"] is False
    assert (out / "arancel_mx.parquet").exists()
    assert main(["data", "export", "--dataset", str(source), "--out", str(out)]) != 0
    assert "is not empty" in capsys.readouterr().err


def _export_sqlite(tmp_path: Path, source: Path) -> tuple[Path, dict[str, object]]:
    out = tmp_path / "sqlite"
    with duckdb.connect(str(source), read_only=True) as conn:
        manifest = export_sqlite(
            conn,
            out,
            source_path=source,
            info={"dataset_version": "2026.08.11", "release_verified": False},
        )
    return out, manifest


def test_sqlite_keeps_text_rates_nulls_exact_decimals_and_iso_dates(
    tmp_path: Path,
) -> None:
    source = create_consumer_duckdb(tmp_path / "arancel_mx.duckdb")
    with duckdb.connect(str(source)) as conn:
        conn.execute(
            "UPDATE canonical_record SET igi_text = 'Ex.', ige_text = NULL WHERE code = '01012101'"
        )
        expected = conn.execute(
            "SELECT igi_text, ige_text, igi_value, effective_from, is_current FROM arancel_mx WHERE code = '01012101'"
        ).fetchone()
        count = conn.execute("SELECT count(*) FROM arancel_mx").fetchone()[0]
    out, manifest = _export_sqlite(tmp_path, source)
    database = sqlite3.connect(out / "arancel_mx.sqlite")
    try:
        row = database.execute(
            "SELECT igi_text, ige_text, igi_value, effective_from, is_current FROM arancel_mx WHERE code = '01012101'"
        ).fetchone()
        rows = database.execute("SELECT count(*) FROM arancel_mx").fetchone()[0]
        mapping = dict(
            database.execute(
                "SELECT column_name, sqlite_type FROM _export_columns WHERE view = 'arancel_mx'"
            ).fetchall()
        )
    finally:
        database.close()
    assert row[0] == "Ex." and row[1] is None
    # A DECIMAL is stored as its exact text, never as a float.
    assert expected[2] is None or row[2] == format(expected[2], "f")
    assert row[3] == (expected[3].isoformat() if expected[3] else None)
    assert row[4] == int(expected[4])
    assert rows == count
    assert (
        mapping["igi_text"] == "TEXT"
        and mapping["igi_value"] == "TEXT"
        and mapping["is_current"] == "INTEGER"
    )
    assert manifest["format"] == "sqlite"
    assert manifest["database"] == {
        "path": "arancel_mx.sqlite",
        "sha256": sha256_file(out / "arancel_mx.sqlite"),
    }
    assert manifest["release_verified"] is False


def test_sqlite_export_is_deterministic_and_lists_skipped_views(tmp_path: Path) -> None:
    source = create_consumer_duckdb(tmp_path / "arancel_mx.duckdb")
    _, first = _export_sqlite(tmp_path / "a", source)
    _, second = _export_sqlite(tmp_path / "b", source)
    assert first["database"] == second["database"]
    exported = {f["view"] for f in first["files"]}
    skipped = {s["view"] for s in first["skipped"]}
    assert exported | skipped == {view for view, _ in EXPORT_VIEWS}


def test_cli_exports_sqlite(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    source = create_consumer_duckdb(tmp_path / "arancel_mx.duckdb")
    out = tmp_path / "db"
    assert (
        main(
            [
                "data",
                "export",
                "--dataset",
                str(source),
                "--out",
                str(out),
                "--to",
                "sqlite",
                "--format",
                "json",
            ]
        )
        == 0
    )
    manifest = json.loads(capsys.readouterr().out)
    assert manifest["format"] == "sqlite"
    assert sorted(p.name for p in out.iterdir()) == [
        "arancel_mx.sqlite",
        "export-manifest.json",
    ]
