from __future__ import annotations

from collections.abc import Callable
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import re
import tempfile
from typing import Any

import duckdb
import requests

from arancel_mx.certification.consumer import certify_duckdb
from arancel_mx.operational import (
    OperationalConnection,
    OperationalRelease,
    _evidence_rows,
    ensure_schema,
    load_certified_release,
    promote_release,
)
from arancel_mx.release.package import PUBLIC_RELEASE_ASSETS


DEFAULT_RELEASE_URL = "https://api.github.com/repos/jccontrerasg08-cpu/arancel-mx/releases/latest"
_RELEASE_HEADERS = {"Accept": "application/vnd.github+json"}
_EVIDENCE_ASSETS = ("arancel_mx.duckdb", "manifest.json", "SHA256SUMS")
_SHA256 = re.compile(r"^[0-9a-f]{64}$")


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
        name, url = asset.get("name"), asset.get("browser_download_url")
        if not isinstance(name, str) or not isinstance(url, str) or name in downloads:
            raise OperationalSyncError("latest public release asset metadata is invalid")
        downloads[name] = url
    if set(downloads) != set(PUBLIC_RELEASE_ASSETS):
        raise OperationalSyncError("latest public release assets are not the exact publication bundle")
    return tag, downloads


def _latest_release(*, release_url: str, fetch: Callable[..., Any]) -> tuple[str, dict[str, str], datetime]:
    response = fetch(release_url, timeout=60, headers=_RELEASE_HEADERS)
    response.raise_for_status()
    tag, downloads = _release_assets(response.json())
    return tag, downloads, _parse_published_at(response.json().get("published_at"))


def _download_assets(destination: Path, downloads: dict[str, str], names: tuple[str, ...], *, fetch: Callable[..., Any]) -> Path:
    destination.mkdir(parents=True, exist_ok=False)
    for name in names:
        response = fetch(downloads[name], timeout=120, headers=_RELEASE_HEADERS)
        response.raise_for_status()
        content = getattr(response, "content", None)
        if not isinstance(content, bytes):
            raise OperationalSyncError(f"downloaded release asset is not bytes: {name}")
        (destination / name).write_bytes(content)
    return destination


def download_latest_publication_bundle(destination: Path, *, release_url: str = DEFAULT_RELEASE_URL, fetch: Callable[..., Any] = requests.get) -> tuple[Path, datetime]:
    tag, downloads, published_at = _latest_release(release_url=release_url, fetch=fetch)
    return _download_assets(Path(destination) / tag, downloads, PUBLIC_RELEASE_ASSETS, fetch=fetch), published_at


def _active_release_state(connection: OperationalConnection) -> tuple[str, object] | None:
    ensure_schema(connection)
    row = connection.execute(
        "SELECT release.tag, release.evidence_json FROM operational_active_release AS active "
        "JOIN operational_release AS release ON release.tag = active.tag"
    ).fetchone()
    return None if row is None else (str(row[0]), row[1])


def _has_evidence(value: object) -> bool:
    if isinstance(value, str):
        try:
            value = json.loads(value)
        except json.JSONDecodeError:
            return False
    return isinstance(value, dict) and any(value.get(key) for key in ("source_documents", "record_provenance", "national_notes"))


def _certified_evidence_release(bundle: Path, *, tag: str, published_at: datetime, source_checked_at: datetime) -> OperationalRelease:
    try:
        manifest = json.loads((bundle / "manifest.json").read_text(encoding="utf-8"))
        checksums = {
            name: digest
            for digest, name in (
                line.split("  ", 1) for line in (bundle / "SHA256SUMS").read_text(encoding="ascii").splitlines()
            )
        }
    except (OSError, ValueError, json.JSONDecodeError) as exc:
        raise OperationalSyncError("evidence snapshot metadata is invalid") from exc
    if not isinstance(manifest, dict) or manifest.get("validation_status") != "passed":
        raise OperationalSyncError("evidence snapshot is not validated")
    version = manifest.get("dataset_version")
    if not isinstance(version, str) or tag != f"data-{version}":
        raise OperationalSyncError("evidence snapshot tag does not match manifest")
    expected = manifest.get("artifact_sha256", {}).get("arancel_mx.duckdb")
    observed = hashlib.sha256((bundle / "arancel_mx.duckdb").read_bytes()).hexdigest()
    if not isinstance(expected, str) or not _SHA256.fullmatch(expected) or expected != observed or checksums.get("arancel_mx.duckdb") != observed:
        raise OperationalSyncError("evidence snapshot DuckDB checksum mismatch")
    try:
        certify_duckdb(bundle / "arancel_mx.duckdb", manifest)
        with duckdb.connect(str(bundle / "arancel_mx.duckdb"), read_only=True) as database:
            evidence = _evidence_rows(database)
        generated_at = datetime.fromisoformat(str(manifest["generated_at"]).replace("Z", "+00:00"))
    except (KeyError, ValueError, duckdb.Error) as exc:
        raise OperationalSyncError("evidence snapshot DuckDB is not certifiable") from exc
    return OperationalRelease(
        tag=tag,
        dataset_version=version,
        schema_version=str(manifest.get("schema_version") or ""),
        manifest_sha256=hashlib.sha256((bundle / "manifest.json").read_bytes()).hexdigest(),
        generated_at=generated_at,
        published_at=published_at,
        source_checked_at=source_checked_at,
        evidence=evidence,
    )


def synchronize_latest_release(connection: OperationalConnection, *, release_url: str = DEFAULT_RELEASE_URL, fetch: Callable[..., Any] = requests.get, checked_at: datetime | None = None) -> dict[str, object]:
    """Promote a new certified bundle, or rehydrate evidence for the active identical release."""
    source_checked_at = checked_at or datetime.now(timezone.utc)
    if source_checked_at.tzinfo is None or source_checked_at.utcoffset() is None:
        raise OperationalSyncError("checked_at must be timezone-aware")
    tag, downloads, published_at = _latest_release(release_url=release_url, fetch=fetch)
    active = _active_release_state(connection)
    if active is not None and active[0] == tag and _has_evidence(active[1]):
        return {"release_tag": tag, "record_count": 0, "changed": False}
    with tempfile.TemporaryDirectory(prefix="arancel-mx-operational-") as temporary:
        if active is not None and active[0] == tag:
            bundle = _download_assets(Path(temporary) / tag, downloads, _EVIDENCE_ASSETS, fetch=fetch)
            release = _certified_evidence_release(bundle, tag=tag, published_at=published_at, source_checked_at=source_checked_at)
            promote_release(connection, release, [])
            return {"release_tag": release.tag, "record_count": 0, "changed": True}
        bundle = _download_assets(Path(temporary) / tag, downloads, PUBLIC_RELEASE_ASSETS, fetch=fetch)
        release, records = load_certified_release(bundle, published_at=published_at, source_checked_at=source_checked_at)
        promote_release(connection, release, records)
    return {"release_tag": release.tag, "record_count": len(records), "changed": True}
