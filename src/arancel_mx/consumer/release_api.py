"""Exact, immutable discovery of public ``data-*`` GitHub Releases."""

from __future__ import annotations

from dataclasses import dataclass
import re
from types import MappingProxyType
from typing import Any, Mapping

import requests

from arancel_mx.consumer.errors import (
    DatasetDownloadError,
    DatasetIntegrityError,
    DatasetVersionNotFoundError,
)
from arancel_mx.release.package import PUBLIC_RELEASE_ASSETS


_REPOSITORY = "jccontrerasg08-cpu/arancel-mx"
_API_ROOT = f"https://api.github.com/repos/{_REPOSITORY}"
_DATA_TAG_RE = re.compile(r"^data-\d{4}\.\d{2}\.\d{2}$")
_API_DIGEST_RE = re.compile(r"^sha256:([0-9a-fA-F]{64})$")
_MAX_LIST_PAGES = 10
_PAGE_SIZE = 100

EXPECTED_ASSETS = frozenset(PUBLIC_RELEASE_ASSETS)


@dataclass(frozen=True, slots=True)
class ReleaseAsset:
    """One immutable asset resolved from a specific data release."""

    asset_id: int
    name: str
    url: str
    size: int
    api_sha256: str | None


@dataclass(frozen=True, slots=True)
class DataRelease:
    """One validated immutable GitHub data release."""

    tag: str
    release_id: int
    assets_by_name: Mapping[str, ReleaseAsset]


def _require_mapping(value: object, *, context: str) -> Mapping[str, Any]:
    if not isinstance(value, Mapping):
        raise DatasetIntegrityError(f"{context} must be a JSON object")
    return value


def _require_int(value: object, *, context: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise DatasetIntegrityError(f"{context} must be an integer")
    return value


def _parse_api_digest(value: object, *, asset_name: str) -> str | None:
    if value is None:
        return None
    if not isinstance(value, str):
        raise DatasetIntegrityError(f"malformed GitHub digest for asset {asset_name}")
    match = _API_DIGEST_RE.fullmatch(value)
    if match is None:
        raise DatasetIntegrityError(f"malformed GitHub digest for asset {asset_name}")
    return match.group(1).lower()


def _parse_asset(value: object, *, tag: str) -> ReleaseAsset:
    payload = _require_mapping(value, context="release asset")
    name = payload.get("name")
    if not isinstance(name, str) or not name:
        raise DatasetIntegrityError("release asset name must be a non-empty string")

    url = payload.get("browser_download_url")
    if not isinstance(url, str) or not url:
        raise DatasetIntegrityError(f"release asset {name} is missing browser_download_url")
    expected_path = f"/releases/download/{tag}/{name}"
    if "/releases/latest/" in url or expected_path not in url:
        raise DatasetIntegrityError(
            f"release asset {name} does not use an exact release download URL"
        )

    asset_id = _require_int(payload.get("id"), context=f"asset {name} id")
    size = _require_int(payload.get("size"), context=f"asset {name} size")
    if size < 0:
        raise DatasetIntegrityError(f"asset {name} size must not be negative")

    return ReleaseAsset(
        asset_id=asset_id,
        name=name,
        url=url,
        size=size,
        api_sha256=_parse_api_digest(payload.get("digest"), asset_name=name),
    )


def _parse_release(value: object) -> DataRelease:
    payload = _require_mapping(value, context="GitHub release")

    tag = payload.get("tag_name")
    if not isinstance(tag, str) or _DATA_TAG_RE.fullmatch(tag) is None:
        raise DatasetIntegrityError("GitHub latest release is not a valid data release tag")
    if payload.get("draft") is not False:
        raise DatasetIntegrityError(f"data release {tag} is draft or has invalid draft state")
    if payload.get("prerelease") is not False:
        raise DatasetIntegrityError(
            f"data release {tag} is prerelease or has invalid prerelease state"
        )

    release_id = _require_int(payload.get("id"), context="release id")
    raw_assets = payload.get("assets")
    if not isinstance(raw_assets, list):
        raise DatasetIntegrityError(f"data release {tag} assets must be a list")

    assets: dict[str, ReleaseAsset] = {}
    for raw_asset in raw_assets:
        asset = _parse_asset(raw_asset, tag=tag)
        if asset.name in assets:
            raise DatasetIntegrityError(
                f"data release {tag} contains duplicate asset name {asset.name}"
            )
        assets[asset.name] = asset

    actual_names = frozenset(assets)
    if actual_names != EXPECTED_ASSETS:
        missing = sorted(EXPECTED_ASSETS - actual_names)
        extra = sorted(actual_names - EXPECTED_ASSETS)
        raise DatasetIntegrityError(
            f"data release {tag} asset set mismatch: missing={missing} extra={extra}"
        )

    return DataRelease(
        tag=tag,
        release_id=release_id,
        assets_by_name=MappingProxyType(dict(assets)),
    )


class GitHubReleaseClient:
    """Resolve public data releases without relying on mutable download aliases."""

    def __init__(self, session: requests.Session, *, timeout: float) -> None:
        if timeout <= 0:
            raise ValueError("timeout must be greater than zero")
        self._session = session
        self._timeout = float(timeout)

    def _get_json(
        self,
        url: str,
        *,
        params: Mapping[str, object] | None = None,
    ) -> object:
        try:
            response = self._session.get(url, params=params, timeout=self._timeout)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:
            raise DatasetDownloadError(
                f"failed to query GitHub releases: {url}"
            ) from exc

    def latest(self) -> DataRelease:
        """Return GitHub's latest release only if it satisfies the data contract."""

        payload = self._get_json(f"{_API_ROOT}/releases/latest")
        return _parse_release(payload)

    def version(self, tag: str) -> DataRelease:
        """Resolve one exact data tag, mapping a GitHub 404 to the public error."""

        if _DATA_TAG_RE.fullmatch(tag) is None:
            raise DatasetVersionNotFoundError(f"invalid data release tag: {tag}")

        url = f"{_API_ROOT}/releases/tags/{tag}"
        try:
            response = self._session.get(url, timeout=self._timeout)
            if response.status_code == 404:
                raise DatasetVersionNotFoundError(
                    f"dataset version not found: {tag}"
                )
            response.raise_for_status()
            payload = response.json()
        except DatasetVersionNotFoundError:
            raise
        except requests.RequestException as exc:
            raise DatasetDownloadError(
                f"failed to query GitHub releases for {tag}"
            ) from exc

        release = _parse_release(payload)
        if release.tag != tag:
            raise DatasetIntegrityError(
                f"GitHub release tag mismatch: requested={tag} resolved={release.tag}"
            )
        return release

    def list(self) -> tuple[DataRelease, ...]:
        """Return valid data releases newest first with bounded pagination."""

        releases: list[DataRelease] = []
        for page in range(1, _MAX_LIST_PAGES + 1):
            payload = self._get_json(
                f"{_API_ROOT}/releases",
                params={"per_page": _PAGE_SIZE, "page": page},
            )
            if not isinstance(payload, list):
                raise DatasetIntegrityError("GitHub releases listing must be a JSON array")
            if not payload:
                break
            for item in payload:
                try:
                    releases.append(_parse_release(item))
                except DatasetIntegrityError:
                    continue

        releases.sort(key=lambda release: release.tag, reverse=True)
        return tuple(releases)
