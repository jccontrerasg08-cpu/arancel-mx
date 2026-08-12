from __future__ import annotations

from pathlib import Path

import pytest

from arancel_mx import Dataset
from arancel_mx.consumer.config import ConsumerConfig
from arancel_mx.consumer.manager import DatasetManager
import arancel_mx.consumer.manager as manager_module
from tests.consumer.test_manager import DownloadHarness, FakeReleaseClient, _two_releases


def test_verified_cache_survives_new_consumer_process_boundary(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    releases, bundles = _two_releases(tmp_path)
    client = FakeReleaseClient(releases)
    downloader = DownloadHarness(bundles)
    monkeypatch.setattr(manager_module, "GitHubReleaseClient", lambda session, timeout: client)
    monkeypatch.setattr(manager_module, "stream_download", downloader)
    cache_dir = tmp_path / "durable cache ñ"

    first_manager = DatasetManager(
        ConsumerConfig(cache_dir, None, False, 2.0),
        session=object(),  # type: ignore[arg-type]
    )
    first_manager.ensure("data-2026.08.11")
    assert first_manager.verify("data-2026.08.11").release_verified is True

    # Drop all live consumer objects. A new package process/version must be able to
    # reconstruct state using only the durable on-disk cache contract.
    del first_manager
    del client
    del downloader

    dataset = Dataset.latest(offline=True, cache_dir=cache_dir)

    assert dataset.info.dataset_version == "2026.08.11"
    assert dataset.info.release_verified is True
    assert dataset.lookup("01012101").code == "01012101"
    assert dataset.search("reproductores")[0].record.code == "010121"
