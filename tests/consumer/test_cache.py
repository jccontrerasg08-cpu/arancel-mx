from __future__ import annotations

from dataclasses import asdict
import json
import os
from pathlib import Path
import subprocess
import sys
import time

import pytest

from arancel_mx.consumer.errors import (
    DatasetIntegrityError,
    DatasetUnavailableError,
    DatasetVersionNotFoundError,
)
from arancel_mx.consumer.cache import DatasetCache, VerifiedMetadata
import arancel_mx.consumer.cache as cache_module


TAG_OLD = "data-2026.08.10"
TAG_NEW = "data-2026.08.11"


def _metadata(tag: str = TAG_NEW) -> VerifiedMetadata:
    return VerifiedMetadata(
        release_id=368540643,
        dataset_tag=tag,
        dataset_version=tag.removeprefix("data-"),
        schema_version="2",
        duckdb_sha256="a" * 64,
        manifest_sha256="b" * 64,
        sha256sums_sha256="c" * 64,
        github_digest_state="verified",
        verified_at="2026-08-12T03:00:00Z",
    )


def _staging(root: Path, tag: str = TAG_NEW, *, suffix: str = "one") -> Path:
    staging = root / ".staging" / f"{tag}-{suffix}"
    staging.mkdir(parents=True)
    (staging / "manifest.part").write_text('{"schema_version":"2"}', encoding="utf-8")
    (staging / "SHA256SUMS.part").write_text("a" * 64 + "  arancel_mx.duckdb\n", encoding="ascii")
    (staging / "arancel_mx.duckdb.part").write_bytes(b"duckdb-fixture")
    return staging


def _write_verified_direct(root: Path, tag: str) -> None:
    release_dir = root / tag
    release_dir.mkdir(parents=True)
    payload = asdict(_metadata(tag))
    (release_dir / "verified.json").write_text(
        json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )


def test_paths_isolate_each_data_version(tmp_path: Path) -> None:
    cache = DatasetCache(tmp_path)
    old = cache.paths(TAG_OLD)
    new = cache.paths(TAG_NEW)

    assert old.root == new.root == tmp_path
    assert old.release_dir == tmp_path / TAG_OLD
    assert new.release_dir == tmp_path / TAG_NEW
    assert old.duckdb != new.duckdb
    assert old.manifest != new.manifest
    assert old.sha256sums != new.sha256sums
    assert old.verified != new.verified
    assert old.lock == new.lock == tmp_path / ".cache.lock"


def test_paths_reject_invalid_tag(tmp_path: Path) -> None:
    cache = DatasetCache(tmp_path)
    with pytest.raises(DatasetVersionNotFoundError, match="data release tag"):
        cache.paths("latest")


def test_list_verified_ignores_directory_without_verified_json(tmp_path: Path) -> None:
    cache = DatasetCache(tmp_path)
    (tmp_path / TAG_OLD).mkdir()
    _write_verified_direct(tmp_path, TAG_NEW)
    (tmp_path / "not-a-release").mkdir()

    assert cache.list_verified() == (TAG_NEW,)


def test_latest_verified_uses_date_tag_order_not_directory_mtime(tmp_path: Path) -> None:
    cache = DatasetCache(tmp_path)
    _write_verified_direct(tmp_path, TAG_OLD)
    _write_verified_direct(tmp_path, TAG_NEW)
    now = time.time()
    os.utime(tmp_path / TAG_OLD, (now + 1000, now + 1000))
    os.utime(tmp_path / TAG_NEW, (now, now))

    assert cache.latest_verified() == TAG_NEW


def test_latest_verified_without_cache_has_download_guidance(tmp_path: Path) -> None:
    cache = DatasetCache(tmp_path)
    with pytest.raises(DatasetUnavailableError, match=r"arancel-mx data download"):
        cache.latest_verified()


def test_promote_uses_os_replace_and_verified_json_is_written_last(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cache = DatasetCache(tmp_path)
    staging = _staging(tmp_path)
    calls: list[str] = []
    real_replace = os.replace

    def recording_replace(src: str | os.PathLike[str], dst: str | os.PathLike[str]) -> None:
        calls.append(Path(dst).name)
        real_replace(src, dst)

    monkeypatch.setattr(cache_module.os, "replace", recording_replace)
    paths = cache.promote(TAG_NEW, staging, _metadata())

    assert calls == ["manifest.json", "SHA256SUMS", "arancel_mx.duckdb", "verified.json"]
    assert paths.verified.is_file()
    assert paths.duckdb.read_bytes() == b"duckdb-fixture"


def test_verified_json_is_deterministic_sorted_json(tmp_path: Path) -> None:
    cache = DatasetCache(tmp_path)
    staging = _staging(tmp_path)
    paths = cache.promote(TAG_NEW, staging, _metadata())

    text = paths.verified.read_text(encoding="utf-8")
    assert text.endswith("\n")
    payload = json.loads(text)
    assert list(payload) == sorted(payload)
    assert payload["dataset_tag"] == TAG_NEW


def test_failed_promotion_never_creates_verified_json(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    cache = DatasetCache(tmp_path)
    staging = _staging(tmp_path)
    real_replace = os.replace

    def failing_replace(src: str | os.PathLike[str], dst: str | os.PathLike[str]) -> None:
        if Path(dst).name == "SHA256SUMS":
            raise PermissionError("simulated promotion failure")
        real_replace(src, dst)

    monkeypatch.setattr(cache_module.os, "replace", failing_replace)

    with pytest.raises(DatasetUnavailableError, match="promote"):
        cache.promote(TAG_NEW, staging, _metadata())

    assert not cache.paths(TAG_NEW).verified.exists()


def test_existing_verified_version_is_not_silently_overwritten(tmp_path: Path) -> None:
    cache = DatasetCache(tmp_path)
    first = _staging(tmp_path, suffix="first")
    paths = cache.promote(TAG_NEW, first, _metadata())
    original = paths.duckdb.read_bytes()

    second = _staging(tmp_path, suffix="second")
    (second / "arancel_mx.duckdb.part").write_bytes(b"different")
    with pytest.raises(DatasetUnavailableError, match="already verified"):
        cache.promote(TAG_NEW, second, _metadata())

    assert paths.duckdb.read_bytes() == original


def test_load_verified_rejects_metadata_tag_mismatch(tmp_path: Path) -> None:
    cache = DatasetCache(tmp_path)
    release_dir = tmp_path / TAG_NEW
    release_dir.mkdir(parents=True)
    payload = asdict(_metadata(TAG_OLD))
    (release_dir / "verified.json").write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(DatasetIntegrityError, match="metadata tag mismatch"):
        cache.load_verified(TAG_NEW)


def test_stale_part_cleanup_does_not_delete_verified_version(tmp_path: Path) -> None:
    cache = DatasetCache(tmp_path)
    paths = cache.promote(TAG_NEW, _staging(tmp_path), _metadata())
    stale = paths.release_dir / "leftover.part"
    stale.write_bytes(b"partial")
    stale_staging = tmp_path / ".staging" / f"{TAG_NEW}-killed"
    stale_staging.mkdir(parents=True)
    (stale_staging / "asset.part").write_bytes(b"partial")

    cache.cleanup_stale_parts(TAG_NEW)

    assert not stale.exists()
    assert not stale_staging.exists()
    assert paths.verified.exists()
    assert paths.duckdb.exists()


def test_cache_lock_serializes_two_processes(tmp_path: Path) -> None:
    cache_root = tmp_path / "cache"
    first_out = tmp_path / "first.json"
    second_out = tmp_path / "second.json"
    script = r'''
import json
from pathlib import Path
import sys
import time
from arancel_mx.consumer.cache import DatasetCache

root = Path(sys.argv[1])
out = Path(sys.argv[2])
delay = float(sys.argv[3])
with DatasetCache(root).locked():
    start = time.time()
    time.sleep(delay)
    end = time.time()
out.write_text(json.dumps([start, end]), encoding="utf-8")
'''
    first = subprocess.Popen([sys.executable, "-c", script, str(cache_root), str(first_out), "0.35"])
    time.sleep(0.05)
    second = subprocess.Popen([sys.executable, "-c", script, str(cache_root), str(second_out), "0.10"])
    assert first.wait(timeout=5) == 0
    assert second.wait(timeout=5) == 0

    intervals = sorted(
        [
            json.loads(first_out.read_text(encoding="utf-8")),
            json.loads(second_out.read_text(encoding="utf-8")),
        ],
        key=lambda item: item[0],
    )
    assert intervals[0][1] <= intervals[1][0] + 0.01


@pytest.mark.parametrize("directory", ["cache with spaces", "caché-con-ñ"])
def test_cache_supports_portable_paths(tmp_path: Path, directory: str) -> None:
    root = tmp_path / directory
    cache = DatasetCache(root)
    paths = cache.promote(TAG_NEW, _staging(root), _metadata())

    assert paths.duckdb.is_file()
    assert paths.verified.is_file()
    assert paths.root == root


def test_read_only_cache_failure_is_mapped_to_dataset_unavailable_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    root = tmp_path / "read-only"
    cache = DatasetCache(root)
    real_mkdir = Path.mkdir

    def denied_mkdir(self: Path, *args: object, **kwargs: object) -> None:
        if self == root:
            raise PermissionError("simulated read-only cache")
        real_mkdir(self, *args, **kwargs)

    monkeypatch.setattr(Path, "mkdir", denied_mkdir)
    with pytest.raises(DatasetUnavailableError, match="cache directory"):
        with cache.locked():
            pass
