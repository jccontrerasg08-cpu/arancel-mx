import hashlib
from urllib.parse import parse_qs, urlparse

import pytest

from arancel_mx.release.package import PUBLIC_RELEASE_ASSETS
from scripts.github_api import GitHubNotFound
from scripts import publish_release as publisher
from scripts.publish_release import PublicationError, publish_release


COMMIT = "abc123def456"
VERSION = "2026.08.10"
TAG = f"data-{VERSION}"


def bundle(tmp_path):
    release = tmp_path / "release"
    release.mkdir()
    for name in PUBLIC_RELEASE_ASSETS:
        (release / name).write_bytes(f"public:{name}".encode())
    return release


def manifest(**overrides):
    value = {
        "dataset_version": VERSION,
        "git_commit_sha": COMMIT,
        "validation_status": "passed",
    }
    value.update(overrides)
    return value


class FakeGitHub:
    def __init__(
        self,
        *,
        existing_release=False,
        existing_tag=False,
        include_digests=True,
        duplicate_remote_asset=False,
    ):
        self.existing_release = existing_release
        self.existing_tag = existing_tag
        self.include_digests = include_digests
        self.duplicate_remote_asset = duplicate_remote_asset
        self.release = None
        self.uploaded = {}
        self.asset_bytes = {}
        self.events = []
        self.mutations = []
        self.upload_calls = []
        self.download_calls = []

    def _asset(self, name, content):
        asset_id = len(self.uploaded) + 100
        digest = hashlib.sha256(content).hexdigest()
        value = {
            "id": asset_id,
            "name": name,
            "size": len(content),
            "url": f"https://api.github.com/repos/owner/repo/releases/assets/{asset_id}",
        }
        if self.include_digests:
            value["digest"] = f"sha256:{digest}"
        self.asset_bytes[asset_id] = content
        return value

    def _release_value(self):
        assert self.release is not None
        assets = list(self.uploaded.values())
        if self.duplicate_remote_asset and assets:
            assets = assets + [dict(assets[0])]
        return {**self.release, "assets": assets}

    def request_json(self, method, path, **kwargs):
        if method == "GET" and path == f"/releases/tags/{TAG}":
            self.events.append("check_release" if self.release is None else "refetch_published")
            if self.existing_release:
                return {"id": 1, "tag_name": TAG, "draft": False, "assets": []}
            if self.release is None or self.release.get("draft") is True:
                raise GitHubNotFound(404, "Not Found")
            return self._release_value()
        if method == "GET" and path == f"/git/ref/tags/{TAG}":
            self.events.append("check_tag")
            if self.existing_tag:
                return {"ref": f"refs/tags/{TAG}"}
            raise GitHubNotFound(404, "Not Found")
        if method == "POST" and path == "/releases":
            self.events.append("create_draft")
            self.mutations.append((method, path, kwargs))
            payload = kwargs["json"]
            self.release = {
                "id": 10,
                "tag_name": payload["tag_name"],
                "target_commitish": payload["target_commitish"],
                "draft": payload["draft"],
                "prerelease": payload["prerelease"],
                "upload_url": (
                    "https://uploads.github.com/repos/owner/repo/releases/10/"
                    "assets{?name,label}"
                ),
                "assets": [],
            }
            return dict(self.release)
        if method == "GET" and path == "/releases/10":
            self.events.append("refetch_draft")
            return self._release_value()
        if method == "PATCH" and path == "/releases/10":
            self.events.append("publish_draft")
            self.mutations.append((method, path, kwargs))
            assert kwargs["json"] == {"draft": False}
            self.release["draft"] = False
            return self._release_value()
        raise AssertionError(f"unexpected JSON request: {method} {path} {kwargs}")

    def request_upload_json(self, upload_url, data, **kwargs):
        query = parse_qs(urlparse(upload_url).query)
        name = query["name"][0]
        content = bytes(data)
        self.events.append(f"upload:{name}")
        self.mutations.append(("UPLOAD", upload_url, {"data": content, **kwargs}))
        self.upload_calls.append((name, upload_url, content))
        asset = self._asset(name, content)
        self.uploaded[name] = asset
        return asset

    def request_bytes(self, method, path, **kwargs):
        if method == "GET" and path.startswith("/releases/assets/"):
            asset_id = int(path.rsplit("/", 1)[1])
            self.download_calls.append((asset_id, kwargs))
            return self.asset_bytes[asset_id]
        if method == "DELETE" and path == "/releases/10":
            self.events.append("delete_draft")
            self.mutations.append((method, path, kwargs))
            self.release = None
            self.uploaded = {}
            return b""
        raise AssertionError(f"unexpected byte request: {method} {path} {kwargs}")


class WrongDigestGitHub(FakeGitHub):
    def _asset(self, name, content):
        value = super()._asset(name, content)
        value["digest"] = "sha256:" + ("0" * 64)
        return value


class CleanupFailureGitHub(FakeGitHub):
    def request_bytes(self, method, path, **kwargs):
        if method == "DELETE" and path == "/releases/10":
            self.events.append("delete_draft_failed")
            raise RuntimeError("simulated draft cleanup failure")
        return super().request_bytes(method, path, **kwargs)


def patch_local_verifier(monkeypatch, events, value=None):
    def verify(path):
        events.append("local_verify")
        assert path.name == "release"
        return value or manifest()

    def certify(path, verified_manifest):
        events.append("duckdb_certify")
        assert path.name == "arancel_mx.duckdb"
        assert verified_manifest == (value or manifest())
        return (
            "core_objects",
            "public_columns",
            "release_metadata",
            "row_count",
            "record_ids",
            "hierarchy",
            "value_origin",
        )

    monkeypatch.setattr(publisher, "verify_publication_bundle", verify)
    monkeypatch.setattr(publisher, "certify_duckdb", certify)


@pytest.mark.parametrize(
    ("existing_release", "existing_tag"),
    [(True, False), (False, True)],
)
def test_existing_release_or_tag_fails_closed_before_any_mutation(
    tmp_path, monkeypatch, existing_release, existing_tag
):
    client = FakeGitHub(
        existing_release=existing_release,
        existing_tag=existing_tag,
    )
    events = client.events
    patch_local_verifier(monkeypatch, events)

    with pytest.raises(PublicationError) as raised:
        publish_release(client, bundle(tmp_path), COMMIT)

    assert raised.value.category == "release_tag_collision"
    assert client.mutations == []
    assert events[0] == "local_verify"


def test_same_date_second_change_never_overwrites_existing_release(tmp_path, monkeypatch):
    client = FakeGitHub(existing_release=True)
    events = client.events
    patch_local_verifier(
        monkeypatch,
        events,
        manifest(source_identity=[{"sha256": "different-source"}]),
    )

    with pytest.raises(PublicationError) as raised:
        publish_release(client, bundle(tmp_path), COMMIT)

    assert raised.value.category == "release_tag_collision"
    assert all(method not in {"POST", "PATCH", "DELETE", "UPLOAD"} for method, _path, _kwargs in client.mutations)


def test_success_is_verify_then_draft_upload_remote_verify_and_publish(tmp_path, monkeypatch):
    client = FakeGitHub(include_digests=True)
    events = client.events
    patch_local_verifier(monkeypatch, events)
    release_dir = bundle(tmp_path)

    result = publish_release(client, release_dir, COMMIT)

    assert result == {
        "status": "published",
        "dataset_version": VERSION,
        "tag": TAG,
        "release_id": 10,
    }
    assert events == [
        "local_verify",
        "duckdb_certify",
        "check_release",
        "check_tag",
        "create_draft",
        *[f"upload:{name}" for name in PUBLIC_RELEASE_ASSETS],
        "refetch_draft",
        "publish_draft",
        "refetch_published",
    ]
    create_payload = client.mutations[0][2]["json"]
    assert create_payload["tag_name"] == TAG
    assert create_payload["target_commitish"] == COMMIT
    assert create_payload["draft"] is True
    assert create_payload["prerelease"] is False
    assert [name for name, _url, _content in client.upload_calls] == list(PUBLIC_RELEASE_ASSETS)
    assert all(content == (release_dir / name).read_bytes() for name, _url, content in client.upload_calls)
    assert client.download_calls == []
    assert client.release["draft"] is False


def test_remote_verification_downloads_assets_when_github_digest_is_unavailable(
    tmp_path, monkeypatch
):
    client = FakeGitHub(include_digests=False)
    patch_local_verifier(monkeypatch, client.events)

    publish_release(client, bundle(tmp_path), COMMIT)

    downloaded_ids = [asset_id for asset_id, _kwargs in client.download_calls]
    assert len(downloaded_ids) == len(PUBLIC_RELEASE_ASSETS) * 2
    assert all(
        kwargs["accept"] == "application/octet-stream"
        for _asset_id, kwargs in client.download_calls
    )


def test_duplicate_remote_asset_blocks_publication_and_deletes_draft(tmp_path, monkeypatch):
    client = FakeGitHub(duplicate_remote_asset=True)
    patch_local_verifier(monkeypatch, client.events)

    with pytest.raises(PublicationError) as raised:
        publish_release(client, bundle(tmp_path), COMMIT)

    assert raised.value.category == "remote_asset_verification"
    assert "publish_draft" not in client.events
    assert client.events[-1] == "delete_draft"


def test_remote_digest_mismatch_blocks_publication_and_deletes_draft(tmp_path, monkeypatch):
    client = WrongDigestGitHub()
    patch_local_verifier(monkeypatch, client.events)

    with pytest.raises(PublicationError) as raised:
        publish_release(client, bundle(tmp_path), COMMIT)

    assert raised.value.category == "remote_asset_verification"
    assert "remote asset digest mismatch" in str(raised.value)
    assert "publish_draft" not in client.events
    assert client.events[-1] == "delete_draft"
    assert client.release is None


def test_cleanup_failure_preserves_original_publication_category_and_context(
    tmp_path, monkeypatch
):
    client = CleanupFailureGitHub(duplicate_remote_asset=True)
    patch_local_verifier(monkeypatch, client.events)

    with pytest.raises(PublicationError) as raised:
        publish_release(client, bundle(tmp_path), COMMIT)

    assert raised.value.category == "remote_asset_verification"
    assert raised.value.release_id == 10
    message = str(raised.value)
    assert "duplicate asset" in message
    assert "draft cleanup also failed" in message
    assert "simulated draft cleanup failure" in message
    assert "publish_draft" not in client.events
    assert client.events[-1] == "delete_draft_failed"
