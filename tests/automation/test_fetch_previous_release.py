import json

import pytest

from scripts.fetch_previous_release import (
    fetch_previous_manifest,
    latest_data_release,
)


IDENTITY = {
    "dataset_key": "ligie",
    "document_role": "ligie_snapshot",
    "source_url": "https://www.snice.gob.mx/ligie.xlsx",
    "sha256": "a" * 64,
    "registry_version": "2026-08-10",
}


def release(tag, *, draft=False, prerelease=False, assets=None):
    return {
        "id": int(tag[-2:]) if tag[-2:].isdigit() else 1,
        "tag_name": tag,
        "draft": draft,
        "prerelease": prerelease,
        "assets": list(assets or []),
    }


def manifest_asset(asset_id=42):
    return {
        "id": asset_id,
        "name": "manifest.json",
        "url": f"https://api.github.com/repos/owner/repo/releases/assets/{asset_id}",
    }


class FakeClient:
    def __init__(self, releases, downloads=None):
        self.releases = releases
        self.downloads = downloads or {}
        self.json_calls = []
        self.byte_calls = []

    def request_json(self, method, path, **kwargs):
        self.json_calls.append((method, path, kwargs))
        assert method == "GET"
        assert path == "/releases?per_page=100"
        return self.releases

    def request_bytes(self, method, path, **kwargs):
        self.byte_calls.append((method, path, kwargs))
        assert method == "GET"
        assert kwargs["accept"] == "application/octet-stream"
        return self.downloads[path]


def valid_manifest(dataset_version="2026.08.10"):
    return {
        "dataset_version": dataset_version,
        "schema_version": "2",
        "validation_status": "passed",
        "row_count": 1,
        "source_identity": [IDENTITY],
    }


def test_latest_data_release_uses_semantic_tag_date_not_api_order():
    values = [
        release("data-2026.07.31"),
        release("data-2026.08.02"),
        release("data-2026.08.10"),
        release("data-2026.08.09"),
    ]

    assert latest_data_release(values)["tag_name"] == "data-2026.08.10"


def test_latest_data_release_excludes_drafts_prereleases_and_malformed_tags():
    values = [
        release("data-2026.08.12", draft=True),
        release("data-2026.08.11", prerelease=True),
        release("data-2026.8.10"),
        release("v2026.08.10"),
        release("data-2026.08.09"),
    ]

    assert latest_data_release(values)["tag_name"] == "data-2026.08.09"


def test_fetch_previous_manifest_returns_none_when_no_dataset_release(tmp_path):
    client = FakeClient([release("v0.1.0")])

    result = fetch_previous_manifest(client, tmp_path / "manifest.json")

    assert result is None
    assert client.byte_calls == []
    assert not (tmp_path / "manifest.json").exists()


def test_fetch_previous_manifest_downloads_valid_latest_manifest_atomically(tmp_path):
    older = manifest_asset(41)
    latest = manifest_asset(42)
    client = FakeClient(
        [
            release("data-2026.08.09", assets=[older]),
            release("data-2026.08.10", assets=[latest]),
        ],
        downloads={
            older["url"]: json.dumps(valid_manifest("2026.08.09")).encode(),
            latest["url"]: json.dumps(valid_manifest()).encode(),
        },
    )
    output = tmp_path / "previous" / "manifest.json"

    result = fetch_previous_manifest(client, output)

    assert result["dataset_version"] == "2026.08.10"
    assert json.loads(output.read_text(encoding="utf-8")) == valid_manifest()
    assert client.byte_calls == [
        ("GET", latest["url"], {"accept": "application/octet-stream"})
    ]


def test_duplicate_manifest_assets_are_rejected(tmp_path):
    assets = [manifest_asset(41), manifest_asset(42)]
    client = FakeClient([release("data-2026.08.10", assets=assets)])

    with pytest.raises(ValueError, match="exactly one manifest.json"):
        fetch_previous_manifest(client, tmp_path / "manifest.json")

    assert client.byte_calls == []


def test_malformed_manifest_json_is_rejected_without_output(tmp_path):
    asset = manifest_asset()
    client = FakeClient(
        [release("data-2026.08.10", assets=[asset])],
        downloads={asset["url"]: b"{not-json"},
    )
    output = tmp_path / "manifest.json"

    with pytest.raises(ValueError, match="valid JSON"):
        fetch_previous_manifest(client, output)

    assert not output.exists()


def test_manifest_without_source_identity_is_rejected_without_output(tmp_path):
    asset = manifest_asset()
    client = FakeClient(
        [release("data-2026.08.10", assets=[asset])],
        downloads={asset["url"]: json.dumps({"dataset_version": "2026.08.10"}).encode()},
    )
    output = tmp_path / "manifest.json"

    with pytest.raises(ValueError, match="source_identity"):
        fetch_previous_manifest(client, output)

    assert not output.exists()
