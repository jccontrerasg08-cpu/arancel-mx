from __future__ import annotations

import json
from pathlib import Path
from types import SimpleNamespace

import duckdb
import pytest

import scripts.build_static_pages as pages
from arancel_mx.consumer.dataset import Dataset
from arancel_mx.diff_pages import DIFF_INDEX, diff_file_name, previous_tag, release_diff_files
from arancel_mx.static_api import build_static_api, verify_static_api
from tests.consumer.conftest import create_consumer_duckdb


def _pair(tmp_path: Path) -> tuple[Dataset, Dataset]:
    before = create_consumer_duckdb(tmp_path / "before.duckdb", dataset_version="2026.08.11")
    after = create_consumer_duckdb(tmp_path / "after.duckdb", dataset_version="2026.08.12")
    with duckdb.connect(str(after)) as conn:
        conn.execute("UPDATE canonical_record SET igi_text = '15' WHERE code = '01012101'")
    return Dataset.open(before), Dataset.open(after)


def test_previous_tag_is_the_newest_older_well_formed_release() -> None:
    tags = ["data-2026.11.20", "data-2026.08.15", "data-2026.11.19", "latest", "data-2026.12.01"]
    assert previous_tag("data-2026.11.20", tags) == "data-2026.11.19"
    assert previous_tag("data-2026.08.15", tags) is None


def test_diff_files_hold_the_same_report_as_the_cli(tmp_path: Path) -> None:
    before, after = _pair(tmp_path)
    files = release_diff_files(before, after)
    name = diff_file_name("2026.08.11", "2026.08.12")
    assert set(files) == {DIFF_INDEX, name}
    report = json.loads(files[name])
    assert [(c["code"], c["event"], c["old_value"], c["new_value"]) for c in report["changes"]] == [
        ("01012101", "igi_changed", "10", "15")
    ]
    index = json.loads(files[DIFF_INDEX])
    assert index["latest"] == name
    assert index["diffs"][0]["changes"] == 1
    assert index["diffs"][0]["by_event"]["igi_changed"] == 1
    assert "not legal events" in index["note"]


def test_without_a_previous_release_the_index_says_why_and_publishes_no_diff(tmp_path: Path) -> None:
    _, after = _pair(tmp_path)
    files = release_diff_files(None, after, reason="no earlier published release")
    assert set(files) == {DIFF_INDEX}
    index = json.loads(files[DIFF_INDEX])
    assert index["latest"] is None and index["diffs"] == []
    assert index["reason"] == "no earlier published release"


def test_diff_files_are_part_of_the_verified_static_tree(tmp_path: Path) -> None:
    before, after = _pair(tmp_path)
    root = tmp_path / "v1"
    manifest = build_static_api(
        Path(after.info.path), root, dataset_tag="data-2026.08.12", release_verified=True,
        extra_files=release_diff_files(before, after),
    )
    assert {DIFF_INDEX, diff_file_name("2026.08.11", "2026.08.12")} <= set(manifest["files"])
    assert verify_static_api(root) == []
    (root / DIFF_INDEX).write_text("{}", encoding="utf-8")
    assert verify_static_api(root) == [f"sha256 mismatch: {DIFF_INDEX}"]


def test_extra_files_cannot_replace_a_core_file(tmp_path: Path) -> None:
    _, after = _pair(tmp_path)
    with pytest.raises(ValueError, match="meta.json"):
        build_static_api(
            Path(after.info.path), tmp_path / "v1", dataset_tag="data-2026.08.12",
            release_verified=True, extra_files={"meta.json": b"{}"},
        )


def test_pages_build_never_fails_because_the_previous_release_is_unavailable(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    _, after = _pair(tmp_path)

    class Broken:
        def __init__(self, *args: object, **kwargs: object) -> None:
            raise ConnectionError("offline")

    monkeypatch.setattr(pages, "DatasetManager", Broken)
    files = pages.diff_files(after, "data-2026.08.12", diff_from="auto", cache_dir=tmp_path)
    index = json.loads(files[DIFF_INDEX])
    assert index["diffs"] == [] and index["reason"] == "previous release unavailable: ConnectionError"
    assert pages.diff_files(after, "data-2026.08.12", diff_from="none", cache_dir=tmp_path) == {}


def test_pages_build_refuses_an_unverified_previous_release(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    before, after = _pair(tmp_path)
    monkeypatch.setattr(pages, "DatasetManager", lambda config: SimpleNamespace(list_remote=lambda: ("data-2026.08.11",)))
    monkeypatch.setattr(pages.Dataset, "version", classmethod(lambda cls, tag, **kwargs: before))
    files = pages.diff_files(after, "data-2026.08.12", diff_from="auto", cache_dir=tmp_path)
    index = json.loads(files[DIFF_INDEX])
    # Dataset.open on a local file is never release_verified, so no comparison is published.
    assert index["diffs"] == [] and index["reason"] == "data-2026.08.11 did not pass verification"


def test_pages_build_publishes_the_diff_against_a_verified_previous_release(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from dataclasses import replace

    before, after = _pair(tmp_path)
    verified = Dataset(Path(before.info.path), replace(before.info, release_verified=True))
    seen: list[str] = []
    monkeypatch.setattr(
        pages, "DatasetManager",
        lambda config: SimpleNamespace(list_remote=lambda: ("data-2026.08.12", "data-2026.08.11", "data-2026.08.10")),
    )

    def version(cls: type, tag: str, **kwargs: object) -> Dataset:
        seen.append(tag)
        return verified

    monkeypatch.setattr(pages.Dataset, "version", classmethod(version))
    files = pages.diff_files(after, "data-2026.08.12", diff_from="auto", cache_dir=tmp_path)
    assert seen == ["data-2026.08.11"]
    index = json.loads(files[DIFF_INDEX])
    assert index["latest"] == diff_file_name("2026.08.11", "2026.08.12")
    assert index["diffs"][0]["changes"] == 1
