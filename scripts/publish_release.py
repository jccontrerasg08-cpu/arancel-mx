"""Publish one immutable, independently verified six-asset GitHub data release."""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile
from urllib.parse import quote, urlencode

from arancel_mx.certification.bundle import certify_bundle
from arancel_mx.release.package import (
    PUBLIC_RELEASE_ASSETS,
    sha256,
)
from scripts.github_api import GitHubApi, GitHubApiError, GitHubNotFound


MAX_DIAGNOSTIC_LENGTH = 1200
_SECRET_KEY_MARKERS = ("TOKEN", "SECRET", "PASSWORD", "PRIVATE_KEY", "API_KEY")


class PublicationError(RuntimeError):
    def __init__(self, category: str, message: str, *, release_id: int | None = None):
        super().__init__(message)
        self.category = category
        self.release_id = release_id


def _nonblank(value: str, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise PublicationError("publisher_configuration", f"{label} must be a non-blank string")
    return value.strip()


def _load_certified_manifest(release_dir: Path) -> dict[str, object]:
    payload = json.loads((release_dir / "manifest.json").read_text(encoding="utf-8"))
    if not isinstance(payload, dict):
        raise PublicationError("release_publication", "certified manifest must be a JSON object")
    return payload


def _sanitize_message(message: object, *extra_secrets: object) -> str:
    text = " ".join(str(message).split())
    secret_values = {
        value
        for key, value in os.environ.items()
        if value and any(marker in key.upper() for marker in _SECRET_KEY_MARKERS)
    }
    secret_values.update(
        str(value) for value in extra_secrets if isinstance(value, str) and value
    )
    for value in sorted(secret_values, key=len, reverse=True):
        text = text.replace(value, "[REDACTED]")
    if len(text) > MAX_DIAGNOSTIC_LENGTH:
        text = text[: MAX_DIAGNOSTIC_LENGTH - 3] + "..."
    return text or "publisher failed without an error message"


def _atomic_write_json(path: Path, value: Mapping[str, object]) -> None:
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ) + "\n"
    handle = tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        newline="",
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    )
    temporary = Path(handle.name)
    try:
        with handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def _release_id(value: Mapping[str, object]) -> int:
    release_id = value.get("id")
    if not isinstance(release_id, int) or isinstance(release_id, bool) or release_id <= 0:
        raise PublicationError("github_release_response", "GitHub release response is missing a valid id")
    return release_id


def _assert_tag_is_available(client: GitHubApi, tag: str) -> None:
    encoded = quote(tag, safe="")
    try:
        client.request_json("GET", f"/releases/tags/{encoded}")
    except GitHubNotFound:
        pass
    else:
        raise PublicationError(
            "release_tag_collision",
            f"GitHub Release already exists for immutable tag {tag}",
        )

    try:
        client.request_json("GET", f"/git/ref/tags/{encoded}")
    except GitHubNotFound:
        return
    raise PublicationError(
        "release_tag_collision",
        f"Git tag already exists for immutable dataset tag {tag}",
    )


def _upload_url(template: object, filename: str) -> str:
    if not isinstance(template, str) or not template.strip():
        raise PublicationError("github_release_response", "draft release is missing upload_url")
    if Path(filename).name != filename or filename not in PUBLIC_RELEASE_ASSETS:
        raise PublicationError("publisher_configuration", f"invalid release asset name: {filename}")
    base = template.split("{", 1)[0]
    separator = "&" if "?" in base else "?"
    return f"{base}{separator}{urlencode({'name': filename})}"


def _remote_asset_map(release: Mapping[str, object]) -> dict[str, Mapping[str, object]]:
    assets = release.get("assets")
    if not isinstance(assets, list):
        raise PublicationError("remote_asset_verification", "remote release assets must be a list")
    mapped: dict[str, Mapping[str, object]] = {}
    for asset in assets:
        if not isinstance(asset, Mapping):
            raise PublicationError("remote_asset_verification", "remote release contains an invalid asset object")
        name = asset.get("name")
        if not isinstance(name, str) or Path(name).name != name:
            raise PublicationError("remote_asset_verification", "remote release contains an invalid asset name")
        if name in mapped:
            raise PublicationError("remote_asset_verification", f"remote release contains duplicate asset {name}")
        mapped[name] = asset
    if set(mapped) != set(PUBLIC_RELEASE_ASSETS):
        raise PublicationError(
            "remote_asset_verification",
            "remote release asset set does not match the six-file publication contract",
        )
    return mapped


def _download_asset_bytes(client: GitHubApi, asset: Mapping[str, object]) -> bytes:
    asset_id = asset.get("id")
    if not isinstance(asset_id, int) or isinstance(asset_id, bool) or asset_id <= 0:
        raise PublicationError("remote_asset_verification", "remote asset is missing a valid id")
    return client.request_bytes(
        "GET",
        f"/releases/assets/{asset_id}",
        accept="application/octet-stream",
    )


def _verify_remote_assets(
    client: GitHubApi,
    release: Mapping[str, object],
    release_dir: Path,
) -> None:
    assets = _remote_asset_map(release)
    for name in PUBLIC_RELEASE_ASSETS:
        local_path = release_dir / name
        expected_size = local_path.stat().st_size
        expected_digest = sha256(local_path)
        remote = assets[name]
        remote_size = remote.get("size")
        if not isinstance(remote_size, int) or isinstance(remote_size, bool) or remote_size != expected_size:
            raise PublicationError(
                "remote_asset_verification",
                f"remote asset size mismatch: {name}",
            )
        remote_digest = remote.get("digest")
        if isinstance(remote_digest, str) and remote_digest:
            if remote_digest.lower() != f"sha256:{expected_digest}":
                raise PublicationError(
                    "remote_asset_verification",
                    f"remote asset digest mismatch: {name}",
                )
            continue
        downloaded = _download_asset_bytes(client, remote)
        if len(downloaded) != expected_size or hashlib.sha256(downloaded).hexdigest() != expected_digest:
            raise PublicationError(
                "remote_asset_verification",
                f"downloaded remote asset checksum mismatch: {name}",
            )


def _delete_failed_draft(client: GitHubApi, release_id: int, original: BaseException) -> None:
    try:
        client.request_bytes("DELETE", f"/releases/{release_id}")
    except Exception as cleanup_error:  # noqa: BLE001 - retain both failure contexts
        category = original.category if isinstance(original, PublicationError) else "release_publication"
        raise PublicationError(
            category,
            (
                f"{original}; draft cleanup also failed for release_id={release_id}: "
                f"{cleanup_error}"
            ),
            release_id=release_id,
        ) from original


def publish_release(
    client: GitHubApi,
    release_dir: Path,
    commit_sha: str,
) -> dict[str, object]:
    release_dir = Path(release_dir).resolve()
    commit_sha = _nonblank(commit_sha, "commit_sha")
    report = certify_bundle(release_dir)
    if not report.passed:
        raise PublicationError("release_publication", "publication bundle certification failed")
    manifest = _load_certified_manifest(release_dir)
    dataset_version = _nonblank(str(manifest.get("dataset_version") or ""), "dataset_version")
    manifest_commit = _nonblank(str(manifest.get("git_commit_sha") or ""), "manifest git_commit_sha")
    if manifest_commit != commit_sha:
        raise PublicationError(
            "manifest_provenance",
            "manifest git_commit_sha does not match the commit selected for publication",
        )
    tag = f"data-{dataset_version}"
    _assert_tag_is_available(client, tag)

    created = client.request_json(
        "POST",
        "/releases",
        json={
            "tag_name": tag,
            "target_commitish": commit_sha,
            "name": f"Arancel MX data {dataset_version}",
            "body": (
                "Automated immutable tariff dataset release. All six assets were "
                "verified locally before upload and are verified again before publication."
            ),
            "draft": True,
            "prerelease": False,
        },
    )
    if not isinstance(created, Mapping):
        raise PublicationError("github_release_response", "draft release response must be an object")
    release_id = _release_id(created)
    published = False
    try:
        for name in PUBLIC_RELEASE_ASSETS:
            client.request_upload_json(
                _upload_url(created.get("upload_url"), name),
                (release_dir / name).read_bytes(),
            )

        remote_draft = client.request_json("GET", f"/releases/{release_id}")
        if not isinstance(remote_draft, Mapping) or remote_draft.get("draft") is not True:
            raise PublicationError(
                "remote_asset_verification",
                "release stopped being a draft before verification completed",
            )
        _verify_remote_assets(client, remote_draft, release_dir)

        published_value = client.request_json(
            "PATCH",
            f"/releases/{release_id}",
            json={"draft": False},
        )
        published = True
        if not isinstance(published_value, Mapping) or published_value.get("draft") is not False:
            raise PublicationError(
                "release_publication",
                "GitHub did not confirm draft publication",
                release_id=release_id,
            )

        final_release = client.request_json("GET", f"/releases/tags/{quote(tag, safe='')}")
        if not isinstance(final_release, Mapping):
            raise PublicationError("release_publication", "published release response must be an object")
        if final_release.get("draft") is not False or final_release.get("tag_name") != tag:
            raise PublicationError("release_publication", "published release identity is invalid")
        if _release_id(final_release) != release_id:
            raise PublicationError("release_publication", "published release id changed after publication")
        _verify_remote_assets(client, final_release, release_dir)
    except Exception as error:  # noqa: BLE001 - publication boundary must clean drafts
        if not published:
            _delete_failed_draft(client, release_id, error)
        if isinstance(error, PublicationError):
            raise
        raise PublicationError(
            "release_publication",
            str(error),
            release_id=release_id,
        ) from error

    return {
        "status": "published",
        "dataset_version": dataset_version,
        "tag": tag,
        "release_id": release_id,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--release-dir", type=Path, default=Path("out/release"))
    parser.add_argument("--commit-sha", default=os.getenv("GITHUB_SHA"))
    parser.add_argument("--repository", default=os.getenv("GITHUB_REPOSITORY"))
    parser.add_argument("--token", default=os.getenv("GITHUB_TOKEN"))
    parser.add_argument("--api-url", default=os.getenv("GITHUB_API_URL", "https://api.github.com"))
    parser.add_argument(
        "--result-path",
        type=Path,
        default=Path("out/publisher-result.json"),
    )
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    try:
        client = GitHubApi(args.repository, args.token, api_url=args.api_url)
        result: dict[str, object] = publish_release(
            client, args.release_dir, args.commit_sha
        )
        exit_code = 0
    except (PublicationError, GitHubApiError, ValueError, OSError) as error:
        category = error.category if isinstance(error, PublicationError) else "release_publication"
        result = {
            "status": "failed",
            "stage": "publish",
            "failure_category": category,
            "message": _sanitize_message(error, args.token),
        }
        exit_code = 2

    try:
        _atomic_write_json(args.result_path, result)
    except Exception as write_error:  # noqa: BLE001 - preserve a bounded stderr diagnostic
        print(
            f"error: unable to write publisher diagnostics: "
            f"{_sanitize_message(write_error, args.token)}",
            file=sys.stderr,
        )
        return 2

    print(
        json.dumps(result, ensure_ascii=False, sort_keys=True),
        file=sys.stderr if exit_code else sys.stdout,
    )
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
