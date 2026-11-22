from __future__ import annotations

import json
from pathlib import Path

import duckdb
import pytest

from arancel_mx.cli import build_parser, main
from arancel_mx.consumer.export import EXPORT_VIEWS, export_parquet, sha256_file
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
