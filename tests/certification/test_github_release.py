from __future__ import annotations

import hashlib
import json

import pytest

from scripts.certify_github_release import (
    CertificationReleaseError,
    certification_tag,
    certify_release_boundary,
    cleanup_certification_resources,
)
from scripts.github_api import GitHubNotFound


REPOSITORY = "owner/arancel-mx"
RUN_ID = "31439123456"
COMMIT_SHA = "a" * 40
TAG = f"certification-{RUN_ID}"
ASSET_NAME = "certification-proof.json"
JSON_ACCEPT = "application/vnd.github+json"


class FakeGitHub:
    def __init__(self, *, preexisting_release=False, preexisting_ref=False, omit_digest=False):
        self.preexisting_release = preexisting_release
        self.ref_exists = preexisting_ref
        self.omit_digest = omit_digest
        self.release = None
        self.asset_bytes = {}
        self.events = []
        self.mutations = []

    def request_json(self, method, path, **kwargs):
        if method == "GET" and path.startswith("/releases?per_page=100&page="):
            page = int(path.rsplit("=", 1)[1])
            if page != 1:
                return []
            releases = []
            if self.preexisting_release:
                releases.append(
                    {
                        "id": 5,
                        "tag_name": TAG,
                        "draft": True,
                        "assets": [],
                    }
                )
            if self.release is not None:
                releases.append({**self.release, "assets": list(self.release["assets"])})
            return releases
        if method == "GET" and path == f"/git/ref/tags/{TAG}":
            if not self.ref_exists:
                raise GitHubNotFound(404, "Not Found")
            return {"ref": f"refs/tags/{TAG}", "object": {"sha": COMMIT_SHA}}
        if method == "POST" and path == "/releases":
            payload = kwargs["json"]
            self.events.append("create_draft")
            self.mutations.append((method, path, payload))
            assert payload["tag_name"] == TAG
            assert payload["target_commitish"] == COMMIT_SHA
            assert payload["draft"] is True
            assert payload["prerelease"] is True
            self.ref_exists = True
            self.release = {
                "id": 10,
                "tag_name": TAG,
                "draft": True,
                "prerelease": True,
                "target_commitish": COMMIT_SHA,
                "upload_url": (
                    "https://uploads.github.com/repos/owner/arancel-mx/releases/10/"
                    "assets{?name,label}"
                ),
                "assets": [],
            }
            return dict(self.release)
        if method == "GET" and path == "/releases/10":
            if self.release is None:
                raise GitHubNotFound(404, "Not Found")
            return {**self.release, "assets": list(self.release["assets"])}
        raise AssertionError(f"unexpected JSON request: {method} {path} {kwargs}")

    def request_upload_json(self, upload_url, data):
        assert self.release is not None
        self.events.append("upload_asset")
        self.mutations.append(("UPLOAD", upload_url, bytes(data)))
        payload = bytes(data)
        digest = hashlib.sha256(payload).hexdigest()
        asset = {
            "id": 100,
            "name": ASSET_NAME,
            "size": len(payload),
            "url": "https://api.github.com/repos/owner/arancel-mx/releases/assets/100",
        }
        if not self.omit_digest:
            asset["digest"] = f"sha256:{digest}"
        self.asset_bytes[100] = payload
        self.release["assets"] = [asset]
        return dict(asset)

    def request_bytes(self, method, path, **kwargs):
        if method == "GET" and path == "/releases/assets/100":
            self.events.append("download_asset")
            return self.asset_bytes[100]
        if method == "DELETE" and path == "/releases/10":
            assert kwargs == {"accept": JSON_ACCEPT}
            self.events.append("delete_release")
            self.mutations.append((method, path, None))
            self.release = None
            return b""
        if method == "DELETE" and path == f"/git/refs/tags/{TAG}":
            assert kwargs == {"accept": JSON_ACCEPT}
            self.events.append("delete_tag")
            self.mutations.append((method, path, None))
            self.ref_exists = False
            return b""
        raise AssertionError(f"unexpected bytes request: {method} {path} {kwargs}")


class HiddenDraftFromListGitHub(FakeGitHub):
    """Model the live API lag where a just-created draft is not listed yet."""

    def request_json(self, method, path, **kwargs):
        if method == "GET" and path.startswith("/releases?per_page=100&page="):
            return []
        return super().request_json(method, path, **kwargs)


def test_certification_tag_rejects_production_or_unscoped_names():
    assert certification_tag(RUN_ID) == TAG
    with pytest.raises(ValueError, match="run id"):
        certification_tag("not-a-run")
    with pytest.raises(ValueError, match="production data tag"):
        certification_tag("data-2026.08.10")


def test_release_boundary_creates_draft_verifies_asset_and_removes_everything():
    client = FakeGitHub()

    result = certify_release_boundary(client, REPOSITORY, RUN_ID, COMMIT_SHA)

    assert result["status"] == "passed"
    assert result["tag"] == TAG
    assert result["release_absent"] is True
    assert result["tag_absent"] is True
    assert len(result["asset_sha256"]) == 64
    assert client.release is None
    assert client.ref_exists is False
    assert client.events == [
        "create_draft",
        "upload_asset",
        "delete_release",
        "delete_tag",
    ]
    assert all(method != "PATCH" for method, _path, _payload in client.mutations)
    create_payload = client.mutations[0][2]
    assert "CERTIFICATION ONLY" in create_payload["body"]
    proof = json.loads(client.asset_bytes[100])
    assert proof == {
        "commit_sha": COMMIT_SHA,
        "marker": "certification only; not a production release",
        "repository": REPOSITORY,
        "run_id": RUN_ID,
        "tag": TAG,
    }


def test_release_boundary_downloads_asset_when_github_digest_is_missing():
    client = FakeGitHub(omit_digest=True)

    result = certify_release_boundary(client, REPOSITORY, RUN_ID, COMMIT_SHA)

    assert result["status"] == "passed"
    assert "download_asset" in client.events
    assert client.release is None
    assert client.ref_exists is False


def test_release_boundary_deletes_created_draft_by_id_when_listing_is_stale():
    client = HiddenDraftFromListGitHub()

    result = certify_release_boundary(client, REPOSITORY, RUN_ID, COMMIT_SHA)

    assert result["status"] == "passed"
    assert result["release_absent"] is True
    assert result["tag_absent"] is True
    assert client.release is None
    assert client.ref_exists is False
    assert "delete_release" in client.events


def test_release_boundary_persists_exact_release_id_until_cleanup_succeeds(tmp_path):
    state_path = tmp_path / "release-boundary-state.json"
    client = UploadAndCleanupFailureGitHub()

    with pytest.raises(CertificationReleaseError):
        certify_release_boundary(
            client,
            REPOSITORY,
            RUN_ID,
            COMMIT_SHA,
            state_path=state_path,
        )

    assert json.loads(state_path.read_text(encoding="utf-8")) == {
        "release_id": 10,
        "tag": TAG,
    }


def test_cleanup_uses_persisted_release_id_when_listing_is_stale(tmp_path):
    state_path = tmp_path / "release-boundary-state.json"
    state_path.write_text(
        json.dumps({"release_id": 10, "tag": TAG}),
        encoding="utf-8",
    )
    client = HiddenDraftFromListGitHub()
    client.release = {
        "id": 10,
        "tag_name": TAG,
        "draft": True,
        "prerelease": True,
        "target_commitish": COMMIT_SHA,
        "upload_url": "unused",
        "assets": [],
    }
    client.ref_exists = True

    result = cleanup_certification_resources(client, TAG, state_path=state_path)

    assert result == {"release_absent": True, "tag_absent": True}
    assert client.release is None
    assert client.ref_exists is False
    assert not state_path.exists()


def test_preexisting_certification_resource_blocks_before_mutation():
    for client in (
        FakeGitHub(preexisting_release=True),
        FakeGitHub(preexisting_ref=True),
    ):
        with pytest.raises(CertificationReleaseError, match="pre-existing"):
            certify_release_boundary(client, REPOSITORY, RUN_ID, COMMIT_SHA)
        assert client.mutations == []


def test_cleanup_only_removes_orphan_release_and_ref_and_is_idempotent():
    client = FakeGitHub()
    client.release = {
        "id": 10,
        "tag_name": TAG,
        "draft": True,
        "prerelease": True,
        "target_commitish": COMMIT_SHA,
        "upload_url": "unused",
        "assets": [],
    }
    client.ref_exists = True

    first = cleanup_certification_resources(client, TAG)
    second = cleanup_certification_resources(client, TAG)

    assert first == {"release_absent": True, "tag_absent": True}
    assert second == first
    assert client.release is None
    assert client.ref_exists is False


def test_cleanup_can_target_known_release_id_when_listing_is_stale():
    client = HiddenDraftFromListGitHub()
    client.release = {
        "id": 10,
        "tag_name": TAG,
        "draft": True,
        "prerelease": True,
        "target_commitish": COMMIT_SHA,
        "upload_url": "unused",
        "assets": [],
    }
    client.ref_exists = True

    result = cleanup_certification_resources(client, TAG, release_id=10)

    assert result == {"release_absent": True, "tag_absent": True}
    assert client.release is None
    assert client.ref_exists is False


class UploadAndCleanupFailureGitHub(FakeGitHub):
    def request_upload_json(self, upload_url, data):
        raise RuntimeError("simulated upload failure")

    def request_bytes(self, method, path, **kwargs):
        if method == "DELETE" and path == "/releases/10":
            raise RuntimeError("simulated cleanup failure")
        return super().request_bytes(method, path, **kwargs)


def test_primary_failure_preserves_cleanup_failure_context():
    client = UploadAndCleanupFailureGitHub()

    with pytest.raises(CertificationReleaseError) as raised:
        certify_release_boundary(client, REPOSITORY, RUN_ID, COMMIT_SHA)

    message = str(raised.value)
    assert "simulated upload failure" in message
    assert "cleanup also failed" in message
    assert "simulated cleanup failure" in message
