"""Transactional manager for immutable public dataset releases."""

from __future__ import annotations

from datetime import datetime, timezone
from pathlib import Path
import shutil
from typing import Literal
import uuid

import requests

from arancel_mx.consumer.cache import DatasetCache, VerifiedMetadata
from arancel_mx.consumer.config import ConsumerConfig
from arancel_mx.consumer.errors import (
    DatasetIntegrityError,
    DatasetUnavailableError,
)
from arancel_mx.consumer.http import build_session, stream_download
from arancel_mx.consumer.integrity import (
    load_manifest,
    parse_sha256sums,
    sha256_file,
    validate_duckdb,
    verify_api_digest,
)
from arancel_mx.consumer.models import DatasetInfo
from arancel_mx.consumer.release_api import DataRelease, GitHubReleaseClient
from arancel_mx.release.package import PUBLIC_RELEASE_ASSETS


_MANAGED_ASSETS = (
    ("manifest.json", "manifest.part"),
    ("SHA256SUMS", "SHA256SUMS.part"),
    ("arancel_mx.duckdb", "arancel_mx.duckdb.part"),
)


class DatasetManager:
    """Resolve, verify, cache, update, and certify public data releases."""

    def __init__(
        self,
        config: ConsumerConfig,
        *,
        session: requests.Session | None = None,
    ) -> None:
        self.config = config
        self.cache = DatasetCache(config.cache_dir)
        self._session = session if session is not None else build_session()
        # Offline mode must not even construct the network-facing release client.
        self._release_client = (
            None
            if config.offline
            else GitHubReleaseClient(self._session, timeout=config.timeout)
        )

    def _client(self) -> GitHubReleaseClient:
        if self.config.offline or self._release_client is None:
            raise DatasetUnavailableError(
                "network access is disabled by offline mode"
            )
        return self._release_client

    def _selected_local_tag(self, tag: str | None) -> str:
        if tag is not None:
            return tag
        if self.config.dataset is not None:
            return self.config.dataset
        return self.cache.latest_verified()

    def _resolve_release(self, tag: str | None) -> DataRelease:
        selected = tag if tag is not None else self.config.dataset
        client = self._client()
        if selected is not None:
            return client.version(selected)
        return client.latest()

    @staticmethod
    def _validate_release_contract(release: DataRelease) -> None:
        expected = frozenset(PUBLIC_RELEASE_ASSETS)
        actual = frozenset(release.assets_by_name)
        if actual != expected:
            missing = sorted(expected - actual)
            extra = sorted(actual - expected)
            raise DatasetIntegrityError(
                f"data release {release.tag} asset set mismatch: "
                f"missing={missing} extra={extra}"
            )

    @staticmethod
    def _read_text(path: Path, *, label: str, encoding: str) -> str:
        try:
            return path.read_text(encoding=encoding)
        except OSError as exc:
            raise DatasetIntegrityError(f"cannot read {label}: {path}") from exc

    @staticmethod
    def _require_declared_checksum(
        checksums: dict[str, str],
        name: str,
        path: Path,
    ) -> None:
        expected = checksums.get(name)
        if expected is None:
            raise DatasetIntegrityError(
                f"SHA256SUMS does not declare required asset: {name}"
            )
        actual = sha256_file(path)
        if actual != expected:
            raise DatasetIntegrityError(
                f"SHA256SUMS checksum mismatch for {name}: "
                f"expected={expected} actual={actual}"
            )

    @staticmethod
    def _combined_digest_state(states: list[str]) -> Literal["verified", "unavailable"]:
        return "verified" if states and all(state == "verified" for state in states) else "unavailable"

    def _validate_cached(self, tag: str) -> DatasetInfo:
        paths = self.cache.paths(tag)
        metadata = self.cache.load_verified(tag)
        required = (paths.manifest, paths.sha256sums, paths.duckdb)
        missing = [path.name for path in required if not path.is_file()]
        if missing:
            raise DatasetIntegrityError(
                f"verified cache is missing required assets for {tag}: {sorted(missing)}"
            )

        actual_manifest = sha256_file(paths.manifest)
        actual_sums = sha256_file(paths.sha256sums)
        actual_duckdb = sha256_file(paths.duckdb)
        expected_pairs = (
            ("manifest.json", actual_manifest, metadata.manifest_sha256),
            ("SHA256SUMS", actual_sums, metadata.sha256sums_sha256),
            ("arancel_mx.duckdb", actual_duckdb, metadata.duckdb_sha256),
        )
        for name, actual, expected in expected_pairs:
            if actual != expected:
                raise DatasetIntegrityError(
                    f"verified cache checksum mismatch for {name}: "
                    f"expected={expected} actual={actual}"
                )

        manifest = load_manifest(paths.manifest)
        checksums = parse_sha256sums(
            self._read_text(paths.sha256sums, label="SHA256SUMS", encoding="ascii")
        )
        self._require_declared_checksum(checksums, "manifest.json", paths.manifest)
        self._require_declared_checksum(checksums, "arancel_mx.duckdb", paths.duckdb)
        info = validate_duckdb(
            paths.duckdb,
            manifest=manifest,
            expected_tag=tag,
            release_verified=True,
            github_digest_state=metadata.github_digest_state,
        )
        if info.dataset_version != metadata.dataset_version:
            raise DatasetIntegrityError(
                "verified metadata dataset version does not match DuckDB"
            )
        if info.schema_version != metadata.schema_version:
            raise DatasetIntegrityError(
                "verified metadata schema version does not match DuckDB"
            )
        return info

    def _download_asset(
        self,
        release: DataRelease,
        name: str,
        destination: Path,
    ) -> str:
        asset = release.assets_by_name.get(name)
        if asset is None:
            raise DatasetIntegrityError(
                f"data release {release.tag} asset set is missing required asset: {name}"
            )
        written = stream_download(
            self._session,
            asset.url,
            destination,
            timeout=self.config.timeout,
        )
        if written != asset.size:
            raise DatasetIntegrityError(
                f"downloaded size mismatch for {name}: expected={asset.size} actual={written}"
            )
        return verify_api_digest(destination, asset.api_sha256)

    def _new_staging(self, tag: str) -> Path:
        staging = self.cache.root / ".staging" / f"{tag}-{uuid.uuid4().hex}"
        try:
            staging.mkdir(parents=True, exist_ok=False)
        except OSError as exc:
            raise DatasetUnavailableError(
                f"cannot create dataset staging directory for {tag}"
            ) from exc
        return staging

    def _ensure_release_locked(self, release: DataRelease) -> Path:
        self._validate_release_contract(release)
        paths = self.cache.paths(release.tag)
        if paths.verified.is_file():
            self._validate_cached(release.tag)
            return paths.duckdb

        self.cache.cleanup_stale_parts(release.tag)
        staging = self._new_staging(release.tag)
        try:
            states: list[str] = []
            for name, temporary_name in _MANAGED_ASSETS:
                states.append(
                    self._download_asset(
                        release,
                        name,
                        staging / temporary_name,
                    )
                )

            manifest_path = staging / "manifest.part"
            sums_path = staging / "SHA256SUMS.part"
            duckdb_path = staging / "arancel_mx.duckdb.part"
            manifest = load_manifest(manifest_path)
            checksums = parse_sha256sums(
                self._read_text(sums_path, label="SHA256SUMS", encoding="ascii")
            )
            self._require_declared_checksum(checksums, "manifest.json", manifest_path)
            self._require_declared_checksum(checksums, "arancel_mx.duckdb", duckdb_path)

            digest_state = self._combined_digest_state(states)
            info = validate_duckdb(
                duckdb_path,
                manifest=manifest,
                expected_tag=release.tag,
                release_verified=True,
                github_digest_state=digest_state,
            )
            metadata = VerifiedMetadata(
                release_id=release.release_id,
                dataset_tag=release.tag,
                dataset_version=str(info.dataset_version),
                schema_version=str(info.schema_version),
                duckdb_sha256=sha256_file(duckdb_path),
                manifest_sha256=sha256_file(manifest_path),
                sha256sums_sha256=sha256_file(sums_path),
                github_digest_state=digest_state,
                verified_at=datetime.now(timezone.utc)
                .isoformat()
                .replace("+00:00", "Z"),
            )
            promoted = self.cache.promote(release.tag, staging, metadata)
            return promoted.duckdb
        finally:
            if staging.exists():
                shutil.rmtree(staging, ignore_errors=True)

    def ensure(self, tag: str | None = None) -> Path:
        """Ensure one selected dataset is locally verified and return its DuckDB path."""

        if self.config.offline:
            with self.cache.locked():
                selected = self._selected_local_tag(tag)
                self._validate_cached(selected)
                return self.cache.paths(selected).duckdb

        # Resolve exactly once. Every following URL is read from this immutable object.
        release = self._resolve_release(tag)
        with self.cache.locked():
            return self._ensure_release_locked(release)

    def update(self) -> tuple[Literal["downloaded", "no_change"], Path]:
        """Download a newer public latest release without deleting older versions."""

        release = self._client().latest()
        with self.cache.locked():
            if self.cache.paths(release.tag).verified.is_file():
                self._validate_release_contract(release)
                self._validate_cached(release.tag)
                return "no_change", self.cache.paths(release.tag).duckdb
            return "downloaded", self._ensure_release_locked(release)

    def list_local(self) -> tuple[str, ...]:
        return self.cache.list_verified()

    def list_remote(self) -> tuple[str, ...]:
        releases = self._client().list()
        for release in releases:
            self._validate_release_contract(release)
        return tuple(release.tag for release in releases)

    def selected_path(self, tag: str | None = None) -> Path:
        with self.cache.locked():
            selected = self._selected_local_tag(tag)
            self._validate_cached(selected)
            return self.cache.paths(selected).duckdb

    def _verify_remote_identity(self, release: DataRelease) -> VerifiedMetadata:
        self._validate_release_contract(release)
        metadata = self.cache.load_verified(release.tag)
        if metadata.release_id != release.release_id:
            raise DatasetIntegrityError(
                f"remote release identity changed for {release.tag}: "
                f"cached={metadata.release_id} remote={release.release_id}"
            )
        paths = self.cache.paths(release.tag)
        local_paths = {
            "manifest.json": paths.manifest,
            "SHA256SUMS": paths.sha256sums,
            "arancel_mx.duckdb": paths.duckdb,
        }
        for name, path in local_paths.items():
            expected = release.assets_by_name[name].api_sha256
            if expected is not None:
                verify_api_digest(path, expected)
        return metadata

    def _verify_bundle(self, release: DataRelease) -> None:
        self._validate_release_contract(release)
        certification_root = self.cache.root / ".certification"
        work = certification_root / f"{release.tag}-{uuid.uuid4().hex}"
        try:
            work.mkdir(parents=True, exist_ok=False)
            states: list[str] = []
            for name in PUBLIC_RELEASE_ASSETS:
                states.append(self._download_asset(release, name, work / name))

            sums_path = work / "SHA256SUMS"
            checksums = parse_sha256sums(
                self._read_text(sums_path, label="SHA256SUMS", encoding="ascii")
            )
            expected_names = set(PUBLIC_RELEASE_ASSETS) - {"SHA256SUMS"}
            if set(checksums) != expected_names:
                raise DatasetIntegrityError(
                    "publication bundle SHA256SUMS coverage is not exact: "
                    f"expected={sorted(expected_names)} actual={sorted(checksums)}"
                )
            for name in sorted(expected_names):
                self._require_declared_checksum(checksums, name, work / name)

            manifest = load_manifest(work / "manifest.json")
            validate_duckdb(
                work / "arancel_mx.duckdb",
                manifest=manifest,
                expected_tag=release.tag,
                release_verified=True,
                github_digest_state=self._combined_digest_state(states),
            )
        finally:
            if work.exists():
                shutil.rmtree(work, ignore_errors=True)

    def verify(
        self,
        tag: str | None = None,
        *,
        online: bool = False,
        bundle: bool = False,
    ) -> DatasetInfo:
        """Verify cached data locally, optionally comparing the exact remote release."""

        selected = self._selected_local_tag(tag)
        with self.cache.locked():
            info = self._validate_cached(selected)
        if not online:
            if bundle:
                raise DatasetUnavailableError(
                    "bundle verification requires online=True"
                )
            return info

        release = self._client().version(selected)
        self._verify_remote_identity(release)
        if bundle:
            self._verify_bundle(release)
        return info
