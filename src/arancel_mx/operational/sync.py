"""Vercel-side synchronization from a public immutable GitHub release to Neon."""

from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
from pathlib import Path
import tempfile
from typing import Any

import requests

from arancel_mx.operational import OperationalConnection, load_certified_release, promote_release
from arancel_mx.release.package import PUBLIC_RELEASE_ASSETS


DEFAULT_RELEASE_URL = "https://api.github.com/repos/jccontrerasg08-cpu/arancel-mx/releases/latest"
_RELEASE_HEADERS = {"Accept": "application/vnd.github+json"}


class OperationalSyncError(ValueError):
    """Raised when a public release cannot safely enter operational storage."""


def _parse_published_at(value: object) -> datetime:
    if not isinstance(value, str):
        raise OperationalSyncError("latest public release is missing published_at")
    try:
        published_at = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise OperationalSyncError("latest public release has invalid published_at") from exc
    if published_at.tzinfo is None or published_at.utcoffset() is None:
        raise OperationalSyncError("latest public release published_at must be timezone-aware")
    return published_at


def _release_assets(payload: object) -> tuple[str, dict[str, str]]:
    if not isinstance(payload, dict):
        raise OperationalSyncError("latest public release response must be an object")
    tag = payload.get("tag_name")
    if not isinstance(tag, str) or not tag.startswith("data-"):
        raise OperationalSyncError("latest public release tag is not a dataset release")
    assets = payload.get("assets")
    if not isinstance(assets, list):
        raise OperationalSyncError("latest public release is missing assets")
    downloads: dict[str, str] = {}
    for asset in assets:
        if not isinstance(asset, dict):
            raise OperationalSyncError("latest public release asset is invalid")
        name = asset.get("name")
        url = asset.get("browser_download_url")
        if not isinstance(name, str) or not isinstance(url, str):
            raise OperationalSyncError("latest public release asset metadata is invalid")
        if name in downloads:
            raise OperationalSyncError(f"latest public release has duplicate asset: {name}")
        downloads[name] = url
    if set(downloads) != set(PUBLIC_RELEASE_ASSETS):
        raise OperationalSyncError("latest public release assets are not the exact publication bundle")
    return tag, downloads


def download_latest_publication_bundle(
    destination: Path,
    *,
    release_url: str = DEFAULT_RELEASE_URL,
    fetch: Callable[..., Any] = requests.get,
) -> tuple[Path, datetime]:
    """Download the exact public bundle for the newest immutable dataset release.

    The archive is not trusted merely because it comes from GitHub. The caller
    invokes ``load_certified_release`` next, which verifies the complete bundle,
    manifest, and artifact checksums before any database transaction opens.
    """

    release_response = fetch(release_url, timeout=60, headers=_RELEASE_HEADERS)
    release_response.raise_for_status()
    payload = release_response.json()
    tag, downloads = _release_assets(payload)
    published_at = _parse_published_at(payload.get("published_at"))

    bundle = Path(destination) / tag
    bundle.mkdir(parents=True, exist_ok=False)
    for name in PUBLIC_RELEASE_ASSETS:
        response = fetch(downloads[name], timeout=120, headers=_RELEASE_HEADERS)
        response.raise_for_status()
        content = getattr(response, "content", None)
        if not isinstance(content, bytes):
            raise OperationalSyncError(f"downloaded release asset is not bytes: {name}")
        (bundle / name).write_bytes(content)
    return bundle, published_at


def synchronize_latest_release(
    connection: OperationalConnection,
    *,
    release_url: str = DEFAULT_RELEASE_URL,
    fetch: Callable[..., Any] = requests.get,
    checked_at: datetime | None = None,
) -> dict[str, object]:
    """Certify and atomically activate the newest public release in Neon.

    Duplicate or missed cron requests are safe: records are version-keyed and the
    active pointer is upserted only after the checked bundle is loaded.
    """

    source_checked_at = checked_at or datetime.now(timezone.utc)
    if source_checked_at.tzinfo is None or source_checked_at.utcoffset() is None:
        raise OperationalSyncError("checked_at must be timezone-aware")
    with tempfile.TemporaryDirectory(prefix="arancel-mx-operational-") as temporary:
        bundle, published_at = download_latest_publication_bundle(
            Path(temporary), release_url=release_url, fetch=fetch
        )
        release, records = load_certified_release(
            bundle,
            published_at=published_at,
            source_checked_at=source_checked_at,
        )
        promote_release(connection, release, records)
    return {"release_tag": release.tag, "record_count": len(records)}
