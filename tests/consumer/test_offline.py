from __future__ import annotations

from pathlib import Path
import socket

import pytest
import requests

from arancel_mx import Dataset
from arancel_mx.consumer.config import ConsumerConfig
from arancel_mx.consumer.errors import DatasetUnavailableError
from arancel_mx.consumer.manager import DatasetManager
import arancel_mx.consumer.manager as manager_module
from tests.consumer.test_manager import DownloadHarness, FakeReleaseClient, _two_releases


def _populate_verified_cache(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    *,
    tag: str | None = None,
) -> Path:
    releases, bundles = _two_releases(tmp_path)
    client = FakeReleaseClient(releases)
    downloader = DownloadHarness(bundles)
    monkeypatch.setattr(manager_module, "GitHubReleaseClient", lambda session, timeout: client)
    monkeypatch.setattr(manager_module, "stream_download", downloader)
    config = ConsumerConfig(
        cache_dir=tmp_path / "cache",
        dataset=None,
        offline=False,
        timeout=2.0,
    )
    return DatasetManager(config, session=object()).ensure(tag)  # type: ignore[arg-type]


def _block_network(monkeypatch: pytest.MonkeyPatch) -> None:
    def forbidden_request(*args: object, **kwargs: object) -> object:
        raise AssertionError("network request attempted in offline mode")

    def forbidden_socket(*args: object, **kwargs: object) -> object:
        raise AssertionError("socket connection attempted in offline mode")

    monkeypatch.setattr(requests.Session, "request", forbidden_request)
    monkeypatch.setattr(socket, "create_connection", forbidden_socket)


def test_latest_offline_never_constructs_or_calls_network_client(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _populate_verified_cache(tmp_path, monkeypatch)

    def forbidden_client(*args: object, **kwargs: object) -> object:
        raise AssertionError("GitHubReleaseClient constructed in offline mode")

    monkeypatch.setattr(manager_module, "GitHubReleaseClient", forbidden_client)
    _block_network(monkeypatch)

    dataset = Dataset.latest(offline=True, cache_dir=tmp_path / "cache")

    assert dataset.info.release_verified is True
    assert dataset.info.dataset_version == "2026.08.11"


def test_latest_offline_selects_newest_verified_local_tag(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _populate_verified_cache(tmp_path, monkeypatch, tag="data-2026.08.10")
    _populate_verified_cache(tmp_path, monkeypatch, tag="data-2026.08.11")
    _block_network(monkeypatch)

    dataset = Dataset.latest(offline=True, cache_dir=tmp_path / "cache")

    assert dataset.info.dataset_version == "2026.08.11"


def test_latest_offline_without_cache_raises_dataset_unavailable_with_download_guidance(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _block_network(monkeypatch)
    with pytest.raises(DatasetUnavailableError, match=r"arancel-mx data download"):
        Dataset.latest(offline=True, cache_dir=tmp_path / "empty-cache")


def test_version_offline_requires_requested_verified_tag(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _populate_verified_cache(tmp_path, monkeypatch, tag="data-2026.08.11")
    _block_network(monkeypatch)

    with pytest.raises(DatasetUnavailableError, match="not verified"):
        Dataset.version(
            "data-2026.08.10",
            offline=True,
            cache_dir=tmp_path / "cache",
        )


def test_lookup_search_parent_children_provenance_work_with_network_blocked(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _populate_verified_cache(tmp_path, monkeypatch)
    _block_network(monkeypatch)
    dataset = Dataset.latest(offline=True, cache_dir=tmp_path / "cache")

    assert dataset.lookup("01012101").code == "01012101"
    assert dataset.search("raza pura")[0].record.code == "010121"
    parent = dataset.parent("01012101")
    assert parent is not None and parent.code == "010121"
    assert tuple(item.code for item in dataset.children("010121")) == ("01012101",)
    assert dataset.provenance("01012101")[0].source_document_id == "fixture-source"


def test_local_verify_works_with_network_blocked(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    _populate_verified_cache(tmp_path, monkeypatch)
    _block_network(monkeypatch)
    config = ConsumerConfig(
        cache_dir=tmp_path / "cache",
        dataset=None,
        offline=True,
        timeout=2.0,
    )
    manager = DatasetManager(config)

    info = manager.verify("data-2026.08.11")

    assert info.release_verified is True
    assert info.github_digest_state == "verified"
