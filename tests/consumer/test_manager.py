from __future__ import annotations

import hashlib
import json
from pathlib import Path
from types import MappingProxyType
from urllib.parse import unquote

import pytest

import arancel_mx.consumer.manager as manager_module
from arancel_mx.consumer.config import ConsumerConfig
from arancel_mx.consumer.errors import DatasetIntegrityError
from arancel_mx.consumer.manager import DatasetManager
from arancel_mx.consumer.release_api import DataRelease, ReleaseAsset
from tests.consumer.conftest import create_consumer_duckdb


TAG_OLD = "data-2026.08.10"
TAG_NEW = "data-2026.08.11"


def _sha(body: bytes) -> str:
    return hashlib.sha256(body).hexdigest()


def _bundle(db_path: Path, tag: str, release_id: int) -> tuple[DataRelease, dict[str, bytes]]:
    version = tag.removeprefix("data-")
    files: dict[str, bytes] = {
        "arancel_mx.duckdb": db_path.read_bytes(),
        "arancel_mx.csv": b"code,description\n01012101,fixture\n",
        "arancel_mx.json": b'[{"code":"01012101"}]\n',
        "manifest.json": json.dumps(
            {
                "dataset_version": version,
                "schema_version": "2",
                "validation_status": "passed",
            },
            sort_keys=True,
        ).encode("utf-8"),
        "official-sources.tar.gz": b"fixture-source-archive",
    }
    checksum_order = [
        "arancel_mx.duckdb",
        "arancel_mx.csv",
        "arancel_mx.json",
        "manifest.json",
        "official-sources.tar.gz",
    ]
    files["SHA256SUMS"] = "".join(
        f"{_sha(files[name])}  {name}\n" for name in checksum_order
    ).encode("ascii")

    assets = {
        name: ReleaseAsset(
            asset_id=release_id * 10 + index,
            name=name,
            url=(
                "https://github.com/jccontrerasg08-cpu/arancel-mx/"
                f"releases/download/{tag}/{name}"
            ),
            size=len(body),
            api_sha256=_sha(body),
        )
        for index, (name, body) in enumerate(sorted(files.items()), start=1)
    }
    return (
        DataRelease(
            tag=tag,
            release_id=release_id,
            assets_by_name=MappingProxyType(assets),
        ),
        files,
    )


class FakeReleaseClient:
    def __init__(self, releases: list[DataRelease]) -> None:
        self.releases = {release.tag: release for release in releases}
        self.latest_release = sorted(releases, key=lambda release: release.tag)[-1]
        self.latest_calls = 0
        self.version_calls: list[str] = []
        self.list_calls = 0

    def latest(self) -> DataRelease:
        self.latest_calls += 1
        return self.latest_release

    def version(self, tag: str) -> DataRelease:
        self.version_calls.append(tag)
        return self.releases[tag]

    def list(self) -> tuple[DataRelease, ...]:
        self.list_calls += 1
        return tuple(sorted(self.releases.values(), key=lambda item: item.tag, reverse=True))


class DownloadHarness:
    def __init__(self, bundles: dict[str, dict[str, bytes]]) -> None:
        self.bundles = bundles
        self.calls: list[tuple[str, str]] = []
        self.overrides: dict[tuple[str, str], bytes] = {}

    def __call__(
        self,
        session: object,
        url: str,
        destination: Path,
        *,
        timeout: float,
    ) -> int:
        parts = unquote(url).rstrip("/").split("/")
        tag, name = parts[-2], parts[-1]
        self.calls.append((tag, name))
        body = self.overrides.get((tag, name), self.bundles[tag][name])
        destination.parent.mkdir(parents=True, exist_ok=True)
        destination.write_bytes(body)
        return len(body)


def _manager(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    client: FakeReleaseClient,
    downloader: DownloadHarness,
    *,
    offline: bool = False,
) -> DatasetManager:
    monkeypatch.setattr(manager_module, "GitHubReleaseClient", lambda session, timeout: client)
    monkeypatch.setattr(manager_module, "stream_download", downloader)
    config = ConsumerConfig(
        cache_dir=tmp_path / "cache",
        dataset=None,
        offline=offline,
        timeout=2.5,
    )
    return DatasetManager(config, session=object())  # type: ignore[arg-type]


def _two_releases(tmp_path: Path) -> tuple[list[DataRelease], dict[str, dict[str, bytes]]]:
    old_db = create_consumer_duckdb(
        tmp_path / "old.duckdb", dataset_version="2026.08.10"
    )
    new_db = create_consumer_duckdb(
        tmp_path / "new.duckdb", dataset_version="2026.08.11"
    )
    old_release, old_files = _bundle(old_db, TAG_OLD, 100)
    new_release, new_files = _bundle(new_db, TAG_NEW, 101)
    return [old_release, new_release], {TAG_OLD: old_files, TAG_NEW: new_files}


def test_ensure_latest_resolves_once_and_pins_exact_release(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    releases, bundles = _two_releases(tmp_path)
    client = FakeReleaseClient(releases)
    downloader = DownloadHarness(bundles)
    manager = _manager(tmp_path, monkeypatch, client, downloader)

    path = manager.ensure()

    assert client.latest_calls == 1
    assert path == tmp_path / "cache" / TAG_NEW / "arancel_mx.duckdb"
    assert {tag for tag, _ in downloader.calls} == {TAG_NEW}


def test_ensure_downloads_manifest_then_sha256sums_then_duckdb(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    releases, bundles = _two_releases(tmp_path)
    client = FakeReleaseClient(releases)
    downloader = DownloadHarness(bundles)
    manager = _manager(tmp_path, monkeypatch, client, downloader)

    manager.ensure(TAG_NEW)

    assert [name for _, name in downloader.calls] == [
        "manifest.json",
        "SHA256SUMS",
        "arancel_mx.duckdb",
    ]
    assert client.version_calls == [TAG_NEW]


def test_ensure_reuses_existing_verified_cache_without_redownload(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    releases, bundles = _two_releases(tmp_path)
    client = FakeReleaseClient(releases)
    downloader = DownloadHarness(bundles)
    manager = _manager(tmp_path, monkeypatch, client, downloader)
    first = manager.ensure(TAG_NEW)
    calls_after_first = list(downloader.calls)

    second = manager.ensure(TAG_NEW)

    assert second == first
    assert downloader.calls == calls_after_first


def test_ensure_failed_checksum_never_promotes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    releases, bundles = _two_releases(tmp_path)
    client = FakeReleaseClient(releases)
    downloader = DownloadHarness(bundles)
    downloader.overrides[(TAG_NEW, "arancel_mx.duckdb")] = b"tampered"
    manager = _manager(tmp_path, monkeypatch, client, downloader)

    with pytest.raises(DatasetIntegrityError):
        manager.ensure(TAG_NEW)

    assert not (tmp_path / "cache" / TAG_NEW / "verified.json").exists()


def test_ensure_invalid_manifest_never_promotes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    releases, bundles = _two_releases(tmp_path)
    client = FakeReleaseClient(releases)
    downloader = DownloadHarness(bundles)
    downloader.overrides[(TAG_NEW, "manifest.json")] = b"{"
    manager = _manager(tmp_path, monkeypatch, client, downloader)

    with pytest.raises(DatasetIntegrityError):
        manager.ensure(TAG_NEW)

    assert not (tmp_path / "cache" / TAG_NEW / "verified.json").exists()


def test_ensure_corrupt_duckdb_never_promotes_even_with_matching_release_hashes(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    releases, bundles = _two_releases(tmp_path)
    release = releases[-1]
    corrupt = b"not-a-duckdb"
    bundles[TAG_NEW]["arancel_mx.duckdb"] = corrupt
    assets = dict(release.assets_by_name)
    old_asset = assets["arancel_mx.duckdb"]
    assets["arancel_mx.duckdb"] = ReleaseAsset(
        old_asset.asset_id,
        old_asset.name,
        old_asset.url,
        len(corrupt),
        _sha(corrupt),
    )
    # Keep SHA256SUMS internally consistent so structural validation is the failing layer.
    checksum_lines = bundles[TAG_NEW]["SHA256SUMS"].decode("ascii").splitlines()
    checksum_lines[0] = next(
        (
            f"{_sha(corrupt)}  arancel_mx.duckdb"
            if line.endswith("  arancel_mx.duckdb")
            else line
        )
        for line in checksum_lines
        if line.endswith("  arancel_mx.duckdb")
    )
    # Rebuild in canonical order because the compact replacement above only selected one line.
    files = bundles[TAG_NEW]
    files["SHA256SUMS"] = "".join(
        f"{_sha(files[name])}  {name}\n"
        for name in [
            "arancel_mx.duckdb",
            "arancel_mx.csv",
            "arancel_mx.json",
            "manifest.json",
            "official-sources.tar.gz",
        ]
    ).encode("ascii")
    sha_asset = assets["SHA256SUMS"]
    assets["SHA256SUMS"] = ReleaseAsset(
        sha_asset.asset_id,
        sha_asset.name,
        sha_asset.url,
        len(files["SHA256SUMS"]),
        _sha(files["SHA256SUMS"]),
    )
    releases[-1] = DataRelease(release.tag, release.release_id, MappingProxyType(assets))
    client = FakeReleaseClient(releases)
    downloader = DownloadHarness(bundles)
    manager = _manager(tmp_path, monkeypatch, client, downloader)

    with pytest.raises(DatasetIntegrityError, match="DuckDB"):
        manager.ensure(TAG_NEW)
    assert not (tmp_path / "cache" / TAG_NEW / "verified.json").exists()


def test_ensure_latest_change_during_operation_cannot_mix_release_assets(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    releases, bundles = _two_releases(tmp_path)
    client = FakeReleaseClient(releases)
    downloader = DownloadHarness(bundles)
    manager = _manager(tmp_path, monkeypatch, client, downloader)

    manager.ensure()

    assert client.latest_calls == 1
    assert downloader.calls == [
        (TAG_NEW, "manifest.json"),
        (TAG_NEW, "SHA256SUMS"),
        (TAG_NEW, "arancel_mx.duckdb"),
    ]


def test_update_downloads_newer_release_without_deleting_old(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    releases, bundles = _two_releases(tmp_path)
    client = FakeReleaseClient(releases)
    client.latest_release = releases[0]
    downloader = DownloadHarness(bundles)
    manager = _manager(tmp_path, monkeypatch, client, downloader)
    old_path = manager.ensure()
    client.latest_release = releases[1]

    state, new_path = manager.update()

    assert state == "downloaded"
    assert old_path.exists()
    assert new_path.exists()
    assert manager.list_local() == (TAG_OLD, TAG_NEW)


def test_update_returns_no_change_when_local_latest_matches_remote(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    releases, bundles = _two_releases(tmp_path)
    client = FakeReleaseClient(releases)
    downloader = DownloadHarness(bundles)
    manager = _manager(tmp_path, monkeypatch, client, downloader)
    expected = manager.ensure()
    calls = list(downloader.calls)

    state, path = manager.update()

    assert state == "no_change"
    assert path == expected
    assert downloader.calls == calls


def test_verify_default_is_local_only(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    releases, bundles = _two_releases(tmp_path)
    client = FakeReleaseClient(releases)
    downloader = DownloadHarness(bundles)
    manager = _manager(tmp_path, monkeypatch, client, downloader)
    manager.ensure(TAG_NEW)
    latest_calls = client.latest_calls
    version_calls = list(client.version_calls)

    info = manager.verify(TAG_NEW)

    assert info.release_verified is True
    assert client.latest_calls == latest_calls
    assert client.version_calls == version_calls


def test_verify_online_compares_exact_remote_release_metadata(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    releases, bundles = _two_releases(tmp_path)
    client = FakeReleaseClient(releases)
    downloader = DownloadHarness(bundles)
    manager = _manager(tmp_path, monkeypatch, client, downloader)
    manager.ensure(TAG_NEW)

    info = manager.verify(TAG_NEW, online=True)

    assert info.release_verified is True
    assert client.version_calls == [TAG_NEW, TAG_NEW]


def test_verify_bundle_fetches_and_validates_all_six_assets(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    releases, bundles = _two_releases(tmp_path)
    client = FakeReleaseClient(releases)
    downloader = DownloadHarness(bundles)
    manager = _manager(tmp_path, monkeypatch, client, downloader)
    manager.ensure(TAG_NEW)
    downloader.calls.clear()

    info = manager.verify(TAG_NEW, online=True, bundle=True)

    assert info.release_verified is True
    assert {name for _, name in downloader.calls} == {
        "arancel_mx.duckdb",
        "arancel_mx.csv",
        "arancel_mx.json",
        "manifest.json",
        "SHA256SUMS",
        "official-sources.tar.gz",
    }
    assert {tag for tag, _ in downloader.calls} == {TAG_NEW}
