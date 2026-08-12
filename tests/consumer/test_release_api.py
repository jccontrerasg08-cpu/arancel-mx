from __future__ import annotations

from dataclasses import FrozenInstanceError
from typing import Any

import pytest
import requests

from arancel_mx.consumer.errors import (
    DatasetDownloadError,
    DatasetIntegrityError,
    DatasetVersionNotFoundError,
)
from arancel_mx.consumer.release_api import EXPECTED_ASSETS, GitHubReleaseClient


TAG = "data-2026.08.11"
EXPECTED_NAMES = {
    "arancel_mx.duckdb",
    "arancel_mx.csv",
    "arancel_mx.json",
    "manifest.json",
    "SHA256SUMS",
    "official-sources.tar.gz",
}


class FakeResponse:
    def __init__(self, payload: Any, *, status_code: int = 200) -> None:
        self._payload = payload
        self.status_code = status_code

    def json(self) -> Any:
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            response = requests.Response()
            response.status_code = self.status_code
            raise requests.HTTPError(f"HTTP {self.status_code}", response=response)


class FakeSession:
    def __init__(self, *results: object) -> None:
        self.results = list(results)
        self.calls: list[tuple[str, dict[str, object]]] = []

    def get(self, url: str, **kwargs: object) -> FakeResponse:
        self.calls.append((url, kwargs))
        if not self.results:
            raise AssertionError(f"unexpected GET: {url}")
        result = self.results.pop(0)
        if isinstance(result, BaseException):
            raise result
        assert isinstance(result, FakeResponse)
        return result


def _asset(name: str, *, digest: object = "sha256:" + "a" * 64, tag: str = TAG) -> dict[str, object]:
    item: dict[str, object] = {
        "id": abs(hash((name, tag))) % 100000,
        "name": name,
        "size": 123,
        "browser_download_url": (
            "https://github.com/jccontrerasg08-cpu/arancel-mx/"
            f"releases/download/{tag}/{name}"
        ),
    }
    if digest is not _MISSING:
        item["digest"] = digest
    return item


_MISSING = object()


def _release(
    *,
    tag: str = TAG,
    release_id: int = 368540643,
    draft: bool = False,
    prerelease: bool = False,
    assets: list[dict[str, object]] | None = None,
) -> dict[str, object]:
    return {
        "id": release_id,
        "tag_name": tag,
        "draft": draft,
        "prerelease": prerelease,
        "assets": assets if assets is not None else [_asset(name, tag=tag) for name in EXPECTED_NAMES],
    }


def _client(*results: object) -> tuple[GitHubReleaseClient, FakeSession]:
    session = FakeSession(*results)
    return GitHubReleaseClient(session, timeout=7.5), session  # type: ignore[arg-type]


def test_expected_assets_constant_is_exact() -> None:
    assert EXPECTED_ASSETS == frozenset(EXPECTED_NAMES)


def test_latest_accepts_non_draft_non_prerelease_data_tag() -> None:
    client, session = _client(FakeResponse(_release()))

    release = client.latest()

    assert release.tag == TAG
    assert release.release_id == 368540643
    assert set(release.assets_by_name) == EXPECTED_NAMES
    assert session.calls[0][0].endswith("/releases/latest")


def test_resolved_release_models_are_immutable() -> None:
    client, _ = _client(FakeResponse(_release()))
    release = client.latest()

    with pytest.raises(FrozenInstanceError):
        release.tag = "data-2000.01.01"  # type: ignore[misc]
    with pytest.raises(TypeError):
        release.assets_by_name["extra"] = next(iter(release.assets_by_name.values()))  # type: ignore[index]


def test_latest_rejects_non_data_tag() -> None:
    client, _ = _client(FakeResponse(_release(tag="pkg-v0.2.0")))

    with pytest.raises(DatasetIntegrityError, match="data release tag"):
        client.latest()


def test_latest_rejects_draft() -> None:
    client, _ = _client(FakeResponse(_release(draft=True)))

    with pytest.raises(DatasetIntegrityError, match="draft"):
        client.latest()


def test_latest_rejects_prerelease() -> None:
    client, _ = _client(FakeResponse(_release(prerelease=True)))

    with pytest.raises(DatasetIntegrityError, match="prerelease"):
        client.latest()


def test_release_requires_exact_six_asset_names() -> None:
    assets = [_asset(name) for name in EXPECTED_NAMES if name != "SHA256SUMS"]
    client, _ = _client(FakeResponse(_release(assets=assets)))

    with pytest.raises(DatasetIntegrityError, match="asset set"):
        client.latest()


def test_release_rejects_duplicate_asset_name() -> None:
    assets = [_asset(name) for name in EXPECTED_NAMES]
    assets.append(_asset("manifest.json"))
    client, _ = _client(FakeResponse(_release(assets=assets)))

    with pytest.raises(DatasetIntegrityError, match="duplicate"):
        client.latest()


def test_release_rejects_extra_asset_name() -> None:
    assets = [_asset(name) for name in EXPECTED_NAMES]
    assets.append(_asset("unexpected.zip"))
    client, _ = _client(FakeResponse(_release(assets=assets)))

    with pytest.raises(DatasetIntegrityError, match="asset set"):
        client.latest()


def test_release_records_valid_sha256_api_digest() -> None:
    expected = "b" * 64
    assets = [
        _asset(name, digest="sha256:" + expected if name == "arancel_mx.duckdb" else "sha256:" + "a" * 64)
        for name in EXPECTED_NAMES
    ]
    client, _ = _client(FakeResponse(_release(assets=assets)))

    release = client.latest()

    assert release.assets_by_name["arancel_mx.duckdb"].api_sha256 == expected


def test_release_allows_missing_api_digest_as_none() -> None:
    assets = [
        _asset(name, digest=_MISSING if name == "manifest.json" else "sha256:" + "a" * 64)
        for name in EXPECTED_NAMES
    ]
    client, _ = _client(FakeResponse(_release(assets=assets)))

    release = client.latest()

    assert release.assets_by_name["manifest.json"].api_sha256 is None


def test_release_rejects_malformed_present_api_digest() -> None:
    assets = [
        _asset(name, digest="md5:abcd" if name == "manifest.json" else "sha256:" + "a" * 64)
        for name in EXPECTED_NAMES
    ]
    client, _ = _client(FakeResponse(_release(assets=assets)))

    with pytest.raises(DatasetIntegrityError, match="digest"):
        client.latest()


def test_version_rejects_invalid_requested_tag_before_network() -> None:
    client, session = _client()

    with pytest.raises(DatasetVersionNotFoundError, match="invalid data release tag"):
        client.version("v0.2.0")

    assert session.calls == []


def test_version_maps_github_404_to_dataset_version_not_found() -> None:
    client, _ = _client(FakeResponse({}, status_code=404))

    with pytest.raises(DatasetVersionNotFoundError, match=TAG):
        client.version(TAG)


def test_transport_failure_maps_to_dataset_download_error() -> None:
    client, _ = _client(requests.ConnectionError("offline"))

    with pytest.raises(DatasetDownloadError, match="GitHub releases"):
        client.latest()


def test_list_filters_invalid_releases_and_sorts_newest_first() -> None:
    older = _release(tag="data-2026.08.10", release_id=10)
    newest = _release(tag="data-2026.08.12", release_id=12)
    invalid = _release(tag="pkg-v0.2.0", release_id=99)
    client, session = _client(
        FakeResponse([older, invalid]),
        FakeResponse([newest]),
        FakeResponse([]),
    )

    releases = client.list()

    assert [release.tag for release in releases] == ["data-2026.08.12", "data-2026.08.10"]
    assert len(session.calls) == 3
    assert session.calls[0][1]["params"] == {"per_page": 100, "page": 1}


def test_list_stops_at_ten_pages() -> None:
    pages = [FakeResponse([] if page == 10 else [_release(release_id=page)]) for page in range(1, 11)]
    client, session = _client(*pages)

    client.list()

    assert len(session.calls) <= 10


def test_resolved_asset_urls_are_exact_release_urls_not_releases_latest_urls() -> None:
    client, _ = _client(FakeResponse(_release()))

    release = client.latest()

    for name, asset in release.assets_by_name.items():
        assert "/releases/latest/" not in asset.url
        assert f"/releases/download/{TAG}/{name}" in asset.url
