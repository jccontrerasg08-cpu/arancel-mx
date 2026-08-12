from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import MappingProxyType
from concurrent.futures import ThreadPoolExecutor

import pytest

from arancel_mx import Dataset
from arancel_mx.consumer.cache import DatasetCache
from arancel_mx.consumer.config import ConsumerConfig
from arancel_mx.consumer.errors import DatasetIntegrityError, DatasetSchemaError
from arancel_mx.consumer.manager import DatasetManager
import arancel_mx.consumer.manager as manager_module
from arancel_mx.consumer.release_api import DataRelease, ReleaseAsset
from tests.consumer.conftest import create_consumer_duckdb
from tests.consumer.test_manager import DownloadHarness, FakeReleaseClient, _bundle, _two_releases


TAG = "data-2026.08.11"


def _sha(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def _replace_asset(
    release: DataRelease,
    bundles: dict[str, dict[str, bytes]],
    name: str,
    body: bytes,
) -> DataRelease:
    bundles[release.tag][name] = body
    assets = dict(release.assets_by_name)
    old = assets[name]
    assets[name] = ReleaseAsset(
        asset_id=old.asset_id,
        name=old.name,
        url=old.url,
        size=len(body),
        api_sha256=_sha(body),
    )
    return DataRelease(release.tag, release.release_id, MappingProxyType(assets))


def _rebuild_sha256sums(
    release: DataRelease,
    bundles: dict[str, dict[str, bytes]],
) -> DataRelease:
    files = bundles[release.tag]
    body = "".join(
        f"{_sha(files[name])}  {name}\n"
        for name in [
            "arancel_mx.duckdb",
            "arancel_mx.csv",
            "arancel_mx.json",
            "manifest.json",
            "official-sources.tar.gz",
        ]
    ).encode("ascii")
    return _replace_asset(release, bundles, "SHA256SUMS", body)


def _manager(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    release: DataRelease,
    bundles: dict[str, dict[str, bytes]],
) -> DatasetManager:
    client = FakeReleaseClient([release])
    downloader = DownloadHarness(bundles)
    monkeypatch.setattr(manager_module, "GitHubReleaseClient", lambda session, timeout: client)
    monkeypatch.setattr(manager_module, "stream_download", downloader)
    return DatasetManager(
        ConsumerConfig(
            cache_dir=tmp_path / "cache",
            dataset=None,
            offline=False,
            timeout=2.0,
        ),
        session=object(),  # type: ignore[arg-type]
    )


def _new_release(tmp_path: Path) -> tuple[DataRelease, dict[str, dict[str, bytes]]]:
    db = create_consumer_duckdb(tmp_path / "dataset.duckdb")
    release, files = _bundle(db, TAG, 101)
    return release, {TAG: files}


def _assert_not_promoted(tmp_path: Path) -> None:
    assert not (tmp_path / "cache" / TAG / "verified.json").exists()


def test_wrong_sha256_leaves_no_verified_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    release, bundles = _new_release(tmp_path)
    # Make the GitHub digest unavailable so the SHA256SUMS layer detects corruption.
    assets = dict(release.assets_by_name)
    duck = assets["arancel_mx.duckdb"]
    assets["arancel_mx.duckdb"] = ReleaseAsset(
        duck.asset_id, duck.name, duck.url, duck.size, None
    )
    release = DataRelease(release.tag, release.release_id, MappingProxyType(assets))
    bundles[TAG]["arancel_mx.duckdb"] = b"x" * duck.size
    manager = _manager(tmp_path, monkeypatch, release, bundles)

    with pytest.raises(DatasetIntegrityError, match="SHA256SUMS"):
        manager.ensure(TAG)
    _assert_not_promoted(tmp_path)


def test_truncated_download_leaves_no_verified_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    release, bundles = _new_release(tmp_path)
    bundles[TAG]["manifest.json"] = bundles[TAG]["manifest.json"][:-1]
    manager = _manager(tmp_path, monkeypatch, release, bundles)

    with pytest.raises(DatasetIntegrityError, match="size mismatch"):
        manager.ensure(TAG)
    _assert_not_promoted(tmp_path)


def test_invalid_sha256sums_leaves_no_verified_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    release, bundles = _new_release(tmp_path)
    release = _replace_asset(release, bundles, "SHA256SUMS", b"garbage\n")
    manager = _manager(tmp_path, monkeypatch, release, bundles)

    with pytest.raises(DatasetIntegrityError, match="SHA256SUMS"):
        manager.ensure(TAG)
    _assert_not_promoted(tmp_path)


def test_invalid_json_manifest_leaves_no_verified_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    release, bundles = _new_release(tmp_path)
    release = _replace_asset(release, bundles, "manifest.json", b"{")
    manager = _manager(tmp_path, monkeypatch, release, bundles)

    with pytest.raises(DatasetIntegrityError, match="invalid JSON"):
        manager.ensure(TAG)
    _assert_not_promoted(tmp_path)


def test_manifest_missing_required_field_leaves_no_verified_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    release, bundles = _new_release(tmp_path)
    manifest = json.loads(bundles[TAG]["manifest.json"])
    del manifest["schema_version"]
    release = _replace_asset(
        release,
        bundles,
        "manifest.json",
        json.dumps(manifest).encode("utf-8"),
    )
    manager = _manager(tmp_path, monkeypatch, release, bundles)

    with pytest.raises(DatasetIntegrityError, match="schema_version"):
        manager.ensure(TAG)
    _assert_not_promoted(tmp_path)


def test_unsupported_schema_leaves_no_verified_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    db = create_consumer_duckdb(
        tmp_path / "schema999.duckdb",
        schema_version="999",
    )
    release, files = _bundle(db, TAG, 101)
    bundles = {TAG: files}
    manifest = json.loads(files["manifest.json"])
    manifest["schema_version"] = "999"
    release = _replace_asset(
        release,
        bundles,
        "manifest.json",
        json.dumps(manifest).encode("utf-8"),
    )
    release = _rebuild_sha256sums(release, bundles)
    manager = _manager(tmp_path, monkeypatch, release, bundles)

    with pytest.raises(DatasetSchemaError, match="999"):
        manager.ensure(TAG)
    _assert_not_promoted(tmp_path)


def test_manifest_version_mismatch_leaves_no_verified_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    release, bundles = _new_release(tmp_path)
    manifest = json.loads(bundles[TAG]["manifest.json"])
    manifest["dataset_version"] = "2026.08.10"
    release = _replace_asset(
        release,
        bundles,
        "manifest.json",
        json.dumps(manifest).encode("utf-8"),
    )
    release = _rebuild_sha256sums(release, bundles)
    manager = _manager(tmp_path, monkeypatch, release, bundles)

    with pytest.raises(DatasetIntegrityError, match="resolved tag"):
        manager.ensure(TAG)
    _assert_not_promoted(tmp_path)


def test_corrupt_duckdb_leaves_no_verified_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    release, bundles = _new_release(tmp_path)
    release = _replace_asset(release, bundles, "arancel_mx.duckdb", b"not-duckdb")
    release = _rebuild_sha256sums(release, bundles)
    manager = _manager(tmp_path, monkeypatch, release, bundles)

    with pytest.raises(DatasetIntegrityError, match="DuckDB"):
        manager.ensure(TAG)
    _assert_not_promoted(tmp_path)


def test_remote_missing_asset_leaves_no_verified_json(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    release, bundles = _new_release(tmp_path)
    assets = dict(release.assets_by_name)
    del assets["manifest.json"]
    release = DataRelease(release.tag, release.release_id, MappingProxyType(assets))
    manager = _manager(tmp_path, monkeypatch, release, bundles)

    with pytest.raises(DatasetIntegrityError, match="asset set"):
        manager.ensure(TAG)
    _assert_not_promoted(tmp_path)


def test_partial_part_from_killed_process_is_cleanable(tmp_path: Path) -> None:
    cache = DatasetCache(tmp_path / "cache")
    stale = cache.root / ".staging" / f"{TAG}-killed"
    stale.mkdir(parents=True)
    (stale / "arancel_mx.duckdb.part").write_bytes(b"partial")

    cache.cleanup_stale_parts(TAG)

    assert not stale.exists()
    assert not cache.paths(TAG).verified.exists()


def test_concurrent_downloads_end_with_one_valid_verified_cache(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    releases, bundles = _two_releases(tmp_path)
    client = FakeReleaseClient(releases)
    downloader = DownloadHarness(bundles)
    monkeypatch.setattr(manager_module, "GitHubReleaseClient", lambda session, timeout: client)
    monkeypatch.setattr(manager_module, "stream_download", downloader)

    def run() -> Path:
        manager = DatasetManager(
            ConsumerConfig(
                cache_dir=tmp_path / "cache",
                dataset=None,
                offline=False,
                timeout=2.0,
            ),
            session=object(),  # type: ignore[arg-type]
        )
        return manager.ensure(TAG)

    with ThreadPoolExecutor(max_workers=2) as executor:
        paths = list(executor.map(lambda _: run(), range(2)))

    assert paths[0] == paths[1]
    assert paths[0].is_file()
    cache = DatasetCache(tmp_path / "cache")
    assert cache.list_verified() == (TAG,)
    assert cache.load_verified(TAG).dataset_tag == TAG


def test_verified_cache_survives_network_failure(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    release, bundles = _new_release(tmp_path)
    manager = _manager(tmp_path, monkeypatch, release, bundles)
    manager.ensure(TAG)

    offline = Dataset.version(TAG, offline=True, cache_dir=tmp_path / "cache")

    assert offline.lookup("01012101").code == "01012101"
    assert offline.info.release_verified is True


def test_old_supported_data_release_can_be_opened_by_new_package(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    releases, bundles = _two_releases(tmp_path)
    client = FakeReleaseClient(releases)
    downloader = DownloadHarness(bundles)
    monkeypatch.setattr(manager_module, "GitHubReleaseClient", lambda session, timeout: client)
    monkeypatch.setattr(manager_module, "stream_download", downloader)
    online = DatasetManager(
        ConsumerConfig(tmp_path / "cache", None, False, 2.0),
        session=object(),  # type: ignore[arg-type]
    )
    online.ensure("data-2026.08.10")

    old = Dataset.version(
        "data-2026.08.10",
        offline=True,
        cache_dir=tmp_path / "cache",
    )

    assert old.info.dataset_version == "2026.08.10"
    assert old.lookup("01012101").code == "01012101"
