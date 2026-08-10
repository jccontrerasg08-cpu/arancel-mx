"""Certify GitHub release write permissions with a disposable draft release.

The helper is intentionally isolated from production release namespaces. It creates at
most one ``certification-<run-id>`` draft, uploads one tiny JSON proof asset, verifies
that asset, and removes both the release and any tag ref before reporting success.
"""

from __future__ import annotations

import argparse
import hashlib
import json
import os
from pathlib import Path
import re
import sys
from typing import Any
from urllib.parse import urlencode

from scripts.github_api import GitHubApi, GitHubNotFound


ASSET_NAME = "certification-proof.json"
_TAG_PATTERN = re.compile(r"^certification-[0-9]+$")
_COMMIT_PATTERN = re.compile(r"^[0-9a-fA-F]{40}$")


class CertificationReleaseError(RuntimeError):
    """Fail-closed error for the temporary release certification boundary."""


def _validate_certification_tag(tag: str) -> str:
    value = str(tag).strip()
    if value.startswith("data-"):
        raise ValueError("production data tag is forbidden for certification")
    if not _TAG_PATTERN.fullmatch(value):
        raise ValueError("certification tag must use certification-<numeric-run-id>")
    return value


def certification_tag(run_id: str) -> str:
    """Return the only tag namespace allowed for release-boundary certification."""
    value = str(run_id).strip()
    if value.startswith("data-"):
        raise ValueError("production data tag is forbidden for certification")
    if not value.isdigit():
        raise ValueError("GitHub run id must contain digits only")
    return _validate_certification_tag(f"certification-{value}")


def _validate_repository(repository: str) -> str:
    value = str(repository).strip()
    parts = value.split("/")
    if len(parts) != 2 or not all(parts):
        raise ValueError("repository must use owner/name")
    return value


def _validate_commit_sha(commit_sha: str) -> str:
    value = str(commit_sha).strip()
    if not _COMMIT_PATTERN.fullmatch(value):
        raise ValueError("commit SHA must contain exactly 40 hexadecimal characters")
    return value.lower()


def _proof_bytes(repository: str, run_id: str, commit_sha: str, tag: str) -> bytes:
    payload = {
        "commit_sha": commit_sha,
        "marker": "certification only; not a production release",
        "repository": repository,
        "run_id": run_id,
        "tag": tag,
    }
    return (
        json.dumps(payload, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")


def _matching_releases(client: GitHubApi, tag: str) -> list[dict[str, Any]]:
    matches: list[dict[str, Any]] = []
    page = 1
    while True:
        value = client.request_json(
            "GET",
            f"/releases?per_page=100&page={page}",
        )
        if not isinstance(value, list):
            raise CertificationReleaseError("GitHub releases response must be a list")
        for release in value:
            if not isinstance(release, dict):
                raise CertificationReleaseError("GitHub release entry must be an object")
            if release.get("tag_name") == tag:
                matches.append(release)
        if len(value) < 100:
            break
        page += 1
    return matches


def _tag_ref_exists(client: GitHubApi, tag: str) -> bool:
    try:
        value = client.request_json("GET", f"/git/ref/tags/{tag}")
    except GitHubNotFound:
        return False
    if not isinstance(value, dict) or value.get("ref") != f"refs/tags/{tag}":
        raise CertificationReleaseError("GitHub returned an unexpected certification tag ref")
    return True


def _asset_upload_url(upload_template: str) -> str:
    base = str(upload_template).split("{", 1)[0]
    if not base.startswith("https://uploads.github.com/"):
        raise CertificationReleaseError("unexpected GitHub release upload URL")
    return f"{base}?{urlencode({'name': ASSET_NAME})}"


def _verify_draft(
    client: GitHubApi,
    release_id: int,
    tag: str,
    proof: bytes,
) -> str:
    release = client.request_json("GET", f"/releases/{release_id}")
    if not isinstance(release, dict):
        raise CertificationReleaseError("GitHub draft release response must be an object")
    if release.get("tag_name") != tag:
        raise CertificationReleaseError("certification draft tag mismatch")
    if release.get("draft") is not True:
        raise CertificationReleaseError("certification release must remain draft")
    if release.get("prerelease") is not True:
        raise CertificationReleaseError("certification release must remain prerelease")

    assets = release.get("assets")
    if not isinstance(assets, list) or len(assets) != 1:
        raise CertificationReleaseError("certification draft must contain exactly one asset")
    asset = assets[0]
    if not isinstance(asset, dict):
        raise CertificationReleaseError("certification release asset must be an object")
    if asset.get("name") != ASSET_NAME or asset.get("size") != len(proof):
        raise CertificationReleaseError("certification release asset metadata mismatch")

    expected = hashlib.sha256(proof).hexdigest()
    digest = asset.get("digest")
    if digest is not None:
        if digest != f"sha256:{expected}":
            raise CertificationReleaseError("certification release asset digest mismatch")
    else:
        asset_id = asset.get("id")
        if not isinstance(asset_id, int):
            raise CertificationReleaseError("certification release asset is missing id")
        downloaded = client.request_bytes(
            "GET",
            f"/releases/assets/{asset_id}",
            accept="application/octet-stream",
        )
        if hashlib.sha256(downloaded).hexdigest() != expected:
            raise CertificationReleaseError("certification release downloaded asset mismatch")
    return expected


def cleanup_certification_resources(client: GitHubApi, tag: str) -> dict[str, bool]:
    """Idempotently remove the exact temporary certification release and tag ref."""
    tag = _validate_certification_tag(tag)

    for release in _matching_releases(client, tag):
        release_id = release.get("id")
        if not isinstance(release_id, int):
            raise CertificationReleaseError("matching certification release has invalid id")
        client.request_bytes("DELETE", f"/releases/{release_id}")

    if _tag_ref_exists(client, tag):
        client.request_bytes("DELETE", f"/git/refs/tags/{tag}")

    release_absent = not _matching_releases(client, tag)
    tag_absent = not _tag_ref_exists(client, tag)
    if not release_absent or not tag_absent:
        raise CertificationReleaseError(
            "certification cleanup verification failed: "
            f"release_absent={release_absent} tag_absent={tag_absent}"
        )
    return {"release_absent": True, "tag_absent": True}


def certify_release_boundary(
    client: GitHubApi,
    repository: str,
    run_id: str,
    commit_sha: str,
) -> dict[str, object]:
    """Create, verify, and completely remove one temporary draft release."""
    repository = _validate_repository(repository)
    tag = certification_tag(run_id)
    commit_sha = _validate_commit_sha(commit_sha)

    if _matching_releases(client, tag):
        raise CertificationReleaseError(f"pre-existing certification release blocks {tag}")
    if _tag_ref_exists(client, tag):
        raise CertificationReleaseError(f"pre-existing certification tag blocks {tag}")

    proof = _proof_bytes(repository, str(run_id), commit_sha, tag)
    mutation_started = False
    primary_error: Exception | None = None
    asset_sha256: str | None = None

    try:
        mutation_started = True
        created = client.request_json(
            "POST",
            "/releases",
            json={
                "tag_name": tag,
                "target_commitish": commit_sha,
                "name": f"Production certification {run_id}",
                "body": (
                    "CERTIFICATION ONLY. Disposable draft used to verify the repository "
                    "release write boundary. This is not a production data release."
                ),
                "draft": True,
                "prerelease": True,
                "generate_release_notes": False,
            },
        )
        if not isinstance(created, dict):
            raise CertificationReleaseError("GitHub create-release response must be an object")
        release_id = created.get("id")
        upload_template = created.get("upload_url")
        if not isinstance(release_id, int) or not isinstance(upload_template, str):
            raise CertificationReleaseError("GitHub draft release is missing id or upload URL")
        if created.get("draft") is not True or created.get("tag_name") != tag:
            raise CertificationReleaseError("GitHub did not create the expected draft release")

        client.request_upload_json(
            _asset_upload_url(upload_template),
            proof,
            content_type="application/json",
        )
        asset_sha256 = _verify_draft(client, release_id, tag, proof)
    except Exception as error:  # noqa: BLE001 - preserve failure through cleanup
        primary_error = error

    cleanup_result: dict[str, bool] | None = None
    cleanup_error: Exception | None = None
    if mutation_started:
        try:
            cleanup_result = cleanup_certification_resources(client, tag)
        except Exception as error:  # noqa: BLE001 - report rollback failure too
            cleanup_error = error

    if primary_error is not None:
        message = f"release-boundary certification failed: {primary_error}"
        if cleanup_error is not None:
            message += f"; cleanup also failed: {cleanup_error}"
        raise CertificationReleaseError(message) from primary_error
    if cleanup_error is not None:
        raise CertificationReleaseError(
            f"release-boundary certification cleanup failed: {cleanup_error}"
        ) from cleanup_error
    if cleanup_result is None or asset_sha256 is None:
        raise CertificationReleaseError("release-boundary certification ended without evidence")

    return {
        "status": "passed",
        "tag": tag,
        "release_absent": cleanup_result["release_absent"],
        "tag_absent": cleanup_result["tag_absent"],
        "asset_sha256": asset_sha256,
    }


def _write_json(path: Path, result: dict[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(
        json.dumps(result, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        + "\n",
        encoding="utf-8",
    )


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cleanup-only", action="store_true")
    parser.add_argument("--result-path", type=Path)
    return parser.parse_args(argv)


def _environment() -> tuple[str, str, str, str]:
    repository = os.getenv("GITHUB_REPOSITORY", "")
    token = os.getenv("GITHUB_TOKEN", "")
    run_id = os.getenv("GITHUB_RUN_ID", "")
    commit_sha = os.getenv("GITHUB_SHA", "")
    if not token:
        raise ValueError("GITHUB_TOKEN is required")
    _validate_repository(repository)
    certification_tag(run_id)
    if commit_sha:
        _validate_commit_sha(commit_sha)
    return repository, token, run_id, commit_sha


def main(argv: list[str] | None = None) -> int:
    args = _parse_args(argv)
    repository, token, run_id, commit_sha = _environment()
    client = GitHubApi(repository, token)
    tag = certification_tag(run_id)

    if args.cleanup_only:
        cleanup = cleanup_certification_resources(client, tag)
        result: dict[str, object] = {"status": "passed", "tag": tag, **cleanup}
    else:
        if not commit_sha:
            raise ValueError("GITHUB_SHA is required for release-boundary certification")
        result = certify_release_boundary(client, repository, run_id, commit_sha)

    if args.result_path is not None:
        _write_json(args.result_path, result)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
