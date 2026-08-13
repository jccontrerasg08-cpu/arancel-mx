"""Cross-platform, transactional cache for verified public data releases."""

from __future__ import annotations

from contextlib import contextmanager
from dataclasses import asdict, dataclass
import json
import os
from pathlib import Path
import re
import shutil
from typing import Iterator, Literal

from filelock import FileLock

from arancel_mx.consumer.errors import (
    DatasetIntegrityError,
    DatasetUnavailableError,
    DatasetVersionNotFoundError,
)


_DATA_TAG_RE = re.compile(r"^data-\d{4}\.\d{2}\.\d{2}$")
_SHA256_RE = re.compile(r"^[0-9a-f]{64}$")
_VERIFIED_KEYS = frozenset(
    {
        "release_id",
        "dataset_tag",
        "dataset_version",
        "schema_version",
        "duckdb_sha256",
        "manifest_sha256",
        "sha256sums_sha256",
        "github_digest_state",
        "verified_at",
    }
)


@dataclass(frozen=True, slots=True)
class CachePaths:
    root: Path
    release_dir: Path
    duckdb: Path
    manifest: Path
    sha256sums: Path
    verified: Path
    lock: Path


@dataclass(frozen=True, slots=True)
class VerifiedMetadata:
    release_id: int
    dataset_tag: str
    dataset_version: str
    schema_version: str
    duckdb_sha256: str
    manifest_sha256: str
    sha256sums_sha256: str
    github_digest_state: Literal["verified", "unavailable"]
    verified_at: str


def _validate_tag(tag: str) -> str:
    if not isinstance(tag, str) or _DATA_TAG_RE.fullmatch(tag) is None:
        raise DatasetVersionNotFoundError(f"invalid data release tag: {tag}")
    return tag


def _validate_metadata(metadata: VerifiedMetadata, *, expected_tag: str) -> None:
    if metadata.dataset_tag != expected_tag:
        raise DatasetIntegrityError(
            "verified metadata tag mismatch: "
            f"expected={expected_tag} actual={metadata.dataset_tag}"
        )
    if metadata.dataset_version != expected_tag.removeprefix("data-"):
        raise DatasetIntegrityError("verified metadata dataset version does not match tag")
    if isinstance(metadata.release_id, bool) or metadata.release_id <= 0:
        raise DatasetIntegrityError("verified metadata release_id must be positive")
    if not metadata.schema_version:
        raise DatasetIntegrityError("verified metadata schema_version must not be empty")
    for label, digest in (
        ("duckdb_sha256", metadata.duckdb_sha256),
        ("manifest_sha256", metadata.manifest_sha256),
        ("sha256sums_sha256", metadata.sha256sums_sha256),
    ):
        if _SHA256_RE.fullmatch(digest) is None:
            raise DatasetIntegrityError(f"verified metadata {label} is invalid")
    if metadata.github_digest_state not in {"verified", "unavailable"}:
        raise DatasetIntegrityError("verified metadata github_digest_state is invalid")
    if not metadata.verified_at:
        raise DatasetIntegrityError("verified metadata verified_at must not be empty")


def _metadata_from_payload(payload: object, *, expected_tag: str) -> VerifiedMetadata:
    if not isinstance(payload, dict) or set(payload) != _VERIFIED_KEYS:
        raise DatasetIntegrityError("verified metadata has an invalid key set")
    try:
        metadata = VerifiedMetadata(
            release_id=payload["release_id"],
            dataset_tag=payload["dataset_tag"],
            dataset_version=payload["dataset_version"],
            schema_version=payload["schema_version"],
            duckdb_sha256=payload["duckdb_sha256"],
            manifest_sha256=payload["manifest_sha256"],
            sha256sums_sha256=payload["sha256sums_sha256"],
            github_digest_state=payload["github_digest_state"],
            verified_at=payload["verified_at"],
        )
    except (KeyError, TypeError) as exc:
        raise DatasetIntegrityError("verified metadata has invalid field types") from exc

    if not isinstance(metadata.release_id, int) or isinstance(metadata.release_id, bool):
        raise DatasetIntegrityError("verified metadata release_id must be an integer")
    for value, label in (
        (metadata.dataset_tag, "dataset_tag"),
        (metadata.dataset_version, "dataset_version"),
        (metadata.schema_version, "schema_version"),
        (metadata.duckdb_sha256, "duckdb_sha256"),
        (metadata.manifest_sha256, "manifest_sha256"),
        (metadata.sha256sums_sha256, "sha256sums_sha256"),
        (metadata.github_digest_state, "github_digest_state"),
        (metadata.verified_at, "verified_at"),
    ):
        if not isinstance(value, str):
            raise DatasetIntegrityError(f"verified metadata {label} must be a string")
    _validate_metadata(metadata, expected_tag=expected_tag)
    return metadata


class DatasetCache:
    """Manage immutable verified dataset directories beneath one cache root."""

    def __init__(self, root: str | Path) -> None:
        self.root = Path(root)

    def paths(self, tag: str) -> CachePaths:
        tag = _validate_tag(tag)
        release_dir = self.root / tag
        return CachePaths(
            root=self.root,
            release_dir=release_dir,
            duckdb=release_dir / "arancel_mx.duckdb",
            manifest=release_dir / "manifest.json",
            sha256sums=release_dir / "SHA256SUMS",
            verified=release_dir / "verified.json",
            lock=self.root / ".cache.lock",
        )

    def _ensure_root(self) -> None:
        try:
            self.root.mkdir(parents=True, exist_ok=True)
        except OSError as exc:
            raise DatasetUnavailableError(
                f"cache directory is not writable: {self.root}"
            ) from exc

    @contextmanager
    def locked(self) -> Iterator[None]:
        self._ensure_root()
        lock = FileLock(str(self.root / ".cache.lock"))
        try:
            with lock:
                yield
        except OSError as exc:
            raise DatasetUnavailableError(
                f"cache directory cannot be locked: {self.root}"
            ) from exc

    def list_verified(self) -> tuple[str, ...]:
        if not self.root.exists():
            return ()
        try:
            tags = [
                path.name
                for path in self.root.iterdir()
                if path.is_dir()
                and _DATA_TAG_RE.fullmatch(path.name) is not None
                and (path / "verified.json").is_file()
            ]
        except OSError as exc:
            raise DatasetUnavailableError(
                f"cannot inspect cache directory: {self.root}"
            ) from exc
        return tuple(sorted(tags))

    def latest_verified(self) -> str:
        tags = self.list_verified()
        if not tags:
            raise DatasetUnavailableError(
                "No verified local dataset is available. "
                "Run `arancel-mx data download` while online."
            )
        return tags[-1]

    def load_verified(self, tag: str) -> VerifiedMetadata:
        paths = self.paths(tag)
        if not paths.verified.is_file():
            raise DatasetUnavailableError(f"dataset is not verified in local cache: {tag}")
        try:
            payload = json.loads(paths.verified.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise DatasetIntegrityError(f"verified metadata is invalid JSON: {tag}") from exc
        except OSError as exc:
            raise DatasetUnavailableError(
                f"cannot read verified metadata for {tag}"
            ) from exc
        return _metadata_from_payload(payload, expected_tag=tag)

    def promote(
        self,
        tag: str,
        staging_dir: Path,
        metadata: VerifiedMetadata,
    ) -> CachePaths:
        paths = self.paths(tag)
        _validate_metadata(metadata, expected_tag=tag)
        self._ensure_root()

        staging_dir = Path(staging_dir)
        root_resolved = self.root.resolve()
        staging_resolved = staging_dir.resolve()
        staging_parent = (self.root / ".staging").resolve()
        if not staging_resolved.is_relative_to(staging_parent):
            raise DatasetIntegrityError("staging directory must live under the cache root")
        if not staging_dir.is_dir():
            raise DatasetUnavailableError(f"staging directory does not exist: {staging_dir}")
        if paths.verified.exists():
            raise DatasetUnavailableError(f"dataset release is already verified: {tag}")

        sources = (
            (staging_dir / "manifest.part", paths.manifest),
            (staging_dir / "SHA256SUMS.part", paths.sha256sums),
            (staging_dir / "arancel_mx.duckdb.part", paths.duckdb),
        )
        missing = [source.name for source, _ in sources if not source.is_file()]
        if missing:
            raise DatasetUnavailableError(
                f"staging directory is incomplete for {tag}: {sorted(missing)}"
            )

        verified_part = staging_dir / "verified.part"
        payload = asdict(metadata)
        try:
            paths.release_dir.mkdir(parents=True, exist_ok=True)
            verified_part.write_text(
                json.dumps(payload, sort_keys=True, separators=(",", ":")) + "\n",
                encoding="utf-8",
            )
            moved: list[Path] = []
            try:
                for source, destination in sources:
                    os.replace(source, destination)
                    moved.append(destination)
                os.replace(verified_part, paths.verified)
            except OSError:
                for destination in reversed(moved):
                    try:
                        destination.unlink(missing_ok=True)
                    except OSError:
                        pass
                paths.verified.unlink(missing_ok=True)
                raise
        except OSError as exc:
            raise DatasetUnavailableError(
                f"failed to promote verified dataset cache for {tag}"
            ) from exc
        finally:
            try:
                verified_part.unlink(missing_ok=True)
            except OSError:
                pass

        shutil.rmtree(staging_dir, ignore_errors=True)
        return paths

    def cleanup_stale_parts(self, tag: str) -> None:
        paths = self.paths(tag)
        try:
            if paths.release_dir.is_dir():
                for partial in paths.release_dir.glob("*.part"):
                    partial.unlink(missing_ok=True)
            staging_root = self.root / ".staging"
            if staging_root.is_dir():
                for staging in staging_root.glob(f"{tag}-*"):
                    if staging.is_dir():
                        shutil.rmtree(staging)
                    else:
                        staging.unlink(missing_ok=True)
        except OSError as exc:
            raise DatasetUnavailableError(
                f"failed to clean stale cache parts for {tag}"
            ) from exc
