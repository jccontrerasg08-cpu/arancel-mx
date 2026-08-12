"""Fetch the latest published dataset manifest from GitHub Releases."""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
from datetime import date
import json
import os
from pathlib import Path
import re
import sys
import tempfile

from arancel_mx.release.metadata import source_identity_from_manifest
from scripts.github_api import GitHubApi


_DATA_TAG = re.compile(r"^data-(\d{4})\.(\d{2})\.(\d{2})$")
_SHA256 = re.compile(r"^[0-9a-fA-F]{64}$")
_LEGACY_BASELINE_VERSION = "2026.08.10"
_RELEASE_ARTIFACTS = {"arancel_mx.csv", "arancel_mx.json", "arancel_mx.duckdb"}


def _tag_date(tag: object) -> date | None:
    if not isinstance(tag, str):
        return None
    match = _DATA_TAG.fullmatch(tag)
    if not match:
        return None
    try:
        return date(*(int(value) for value in match.groups()))
    except ValueError:
        return None


def latest_data_release(
    releases: Sequence[Mapping[str, object]],
) -> Mapping[str, object] | None:
    candidates: list[tuple[date, Mapping[str, object]]] = []
    for release in releases:
        if release.get("draft") is True or release.get("prerelease") is True:
            continue
        published_date = _tag_date(release.get("tag_name"))
        if published_date is not None:
            candidates.append((published_date, release))
    if not candidates:
        return None
    return max(candidates, key=lambda item: item[0])[1]


def _manifest_asset(release: Mapping[str, object]) -> Mapping[str, object]:
    assets = release.get("assets")
    if not isinstance(assets, list):
        raise ValueError("selected release assets must be a list")
    matching = [
        asset
        for asset in assets
        if isinstance(asset, Mapping) and asset.get("name") == "manifest.json"
    ]
    if len(matching) != 1:
        raise ValueError("selected release must contain exactly one manifest.json asset")
    return matching[0]


def _asset_api_path(asset: Mapping[str, object]) -> str:
    url = asset.get("url")
    if isinstance(url, str) and url.strip():
        return url
    asset_id = asset.get("id")
    if isinstance(asset_id, int) and not isinstance(asset_id, bool) and asset_id > 0:
        return f"/releases/assets/{asset_id}"
    raise ValueError("manifest.json asset is missing a GitHub asset URL or id")


def _mark_known_legacy_baseline(
    value: Mapping[str, object], expected_version: str
) -> dict[str, object] | None:
    """Validate and mark only the known pre-schema-v2 release baseline."""
    if expected_version != _LEGACY_BASELINE_VERSION or value.get("schema_version") != "1":
        return None
    if value.get("validation_status") != "passed":
        raise ValueError("legacy baseline manifest validation_status must be passed")
    row_count = value.get("row_count")
    if not isinstance(row_count, int) or isinstance(row_count, bool) or row_count <= 0:
        raise ValueError("legacy baseline manifest row_count must be a positive integer")
    artifact_hashes = value.get("artifact_sha256")
    if not isinstance(artifact_hashes, Mapping) or set(artifact_hashes) != _RELEASE_ARTIFACTS:
        raise ValueError("legacy baseline manifest artifact set is not canonical")
    if any(
        not isinstance(digest, str) or _SHA256.fullmatch(digest) is None
        for digest in artifact_hashes.values()
    ):
        raise ValueError("legacy baseline manifest contains an invalid artifact checksum")
    marked = dict(value)
    marked["baseline_status"] = "legacy_baseline"
    return marked


def _parse_manifest(raw: bytes, expected_version: str) -> dict[str, object]:
    try:
        value = json.loads(raw.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("downloaded manifest.json is not valid JSON") from exc
    if not isinstance(value, dict):
        raise ValueError("downloaded manifest.json must contain a JSON object")
    if value.get("dataset_version") != expected_version:
        raise ValueError("downloaded manifest dataset_version does not match release tag")

    legacy = _mark_known_legacy_baseline(value, expected_version)
    if legacy is not None:
        return legacy

    # Schema-v2 and any future baseline remain strict: complete source identity is
    # required before a previous release can participate in no-change decisions.
    source_identity_from_manifest(value)
    return value


def _atomic_write_json(path: Path, value: Mapping[str, object]) -> None:
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
    temp_path = Path(handle.name)
    try:
        with handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        temp_path.replace(path)
    except Exception:
        temp_path.unlink(missing_ok=True)
        raise


def fetch_previous_manifest(
    client: GitHubApi,
    output_path: Path,
) -> dict[str, object] | None:
    releases = client.request_json("GET", "/releases?per_page=100")
    if not isinstance(releases, list):
        raise ValueError("GitHub releases response must be a list")
    selected = latest_data_release(
        [release for release in releases if isinstance(release, Mapping)]
    )
    if selected is None:
        return None
    tag = str(selected["tag_name"])
    expected_version = tag.removeprefix("data-")
    asset = _manifest_asset(selected)
    raw = client.request_bytes(
        "GET",
        _asset_api_path(asset),
        accept="application/octet-stream",
    )
    manifest = _parse_manifest(raw, expected_version)
    _atomic_write_json(Path(output_path), manifest)
    return manifest


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, default=Path("out/previous-manifest.json"))
    parser.add_argument("--repository", default=os.getenv("GITHUB_REPOSITORY"))
    parser.add_argument("--token", default=os.getenv("GITHUB_TOKEN"))
    parser.add_argument("--api-url", default=os.getenv("GITHUB_API_URL", "https://api.github.com"))
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    try:
        client = GitHubApi(args.repository, args.token, api_url=args.api_url)
        manifest = fetch_previous_manifest(client, args.output)
    except (ValueError, OSError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    if manifest is None:
        print(json.dumps({"status": "none"}, sort_keys=True))
        return 0
    print(
        json.dumps(
            {
                "status": "found",
                "tag": f"data-{manifest['dataset_version']}",
                "path": str(args.output),
                "baseline_status": manifest.get("baseline_status", "schema_v2"),
            },
            sort_keys=True,
        )
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
