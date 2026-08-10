"""Verify and package immutable Arancel MX GitHub Release assets."""

from __future__ import annotations

import hashlib
import gzip
import json
from pathlib import Path
import shutil
import tarfile
import tempfile
from typing import Any

from arancel_mx.pipeline.build import export_arancel_release


RELEASE_ARTIFACTS = ("arancel_mx.csv", "arancel_mx.json", "arancel_mx.duckdb")
SOURCE_ARCHIVE = "official-sources.tar.gz"


def sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for chunk in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _checksum_lines(path: Path) -> dict[str, str]:
    declared: dict[str, str] = {}
    for line in path.read_text(encoding="ascii").splitlines():
        parts = line.split()
        if len(parts) != 2 or Path(parts[1]).name != parts[1]:
            raise ValueError(f"Invalid checksum line: {line}")
        declared[parts[1]] = parts[0]
    return declared


def verify_release(release_dir: Path) -> dict[str, Any]:
    release_dir = Path(release_dir).resolve()
    manifest_path = release_dir / "manifest.json"
    checksums_path = release_dir / "SHA256SUMS"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("validation_status") != "passed":
        raise ValueError("Release validation status is not passed")
    artifact_hashes = manifest.get("artifact_sha256")
    if not isinstance(artifact_hashes, dict) or set(artifact_hashes) != set(RELEASE_ARTIFACTS):
        raise ValueError("Release manifest artifact set is not canonical")
    for name, expected in artifact_hashes.items():
        path = release_dir / name
        if not path.is_file() or sha256(path) != expected:
            raise ValueError(f"Release artifact checksum mismatch: {name}")
    for name, expected in _checksum_lines(checksums_path).items():
        path = release_dir / name
        if not path.is_file() or sha256(path) != expected:
            raise ValueError(f"SHA256SUMS checksum mismatch: {name}")
    return manifest


def verify_sources(source_dir: Path) -> list[dict[str, Any]]:
    source_dir = Path(source_dir).resolve()
    capture_path = source_dir / "source_capture.json"
    captured = json.loads(capture_path.read_text(encoding="utf-8"))
    if not isinstance(captured, list) or not captured:
        raise ValueError("Source capture metadata is empty")
    filenames: set[str] = set()
    for row in captured:
        filename = row.get("filename")
        if not isinstance(filename, str) or Path(filename).name != filename or filename in filenames:
            raise ValueError(f"Invalid captured source filename: {filename}")
        filenames.add(filename)
        path = source_dir / filename
        if not path.is_file() or sha256(path) != row.get("sha256"):
            raise ValueError(f"Captured source checksum mismatch: {filename}")
    return captured


def _add_deterministic_file(
    archive: tarfile.TarFile, path: Path, arcname: str
) -> None:
    info = tarfile.TarInfo(arcname)
    info.size = path.stat().st_size
    info.mode = 0o644
    info.mtime = 0
    info.uid = 0
    info.gid = 0
    info.uname = ""
    info.gname = ""
    with path.open("rb") as stream:
        archive.addfile(info, stream)


def build_release(database_path: Path, output_dir: Path) -> dict[str, object]:
    """Create deterministic public artifacts from a validated tariff database."""
    return export_arancel_release(Path(database_path), Path(output_dir))


def prepare_release_archive(
    release_dir: Path, source_dir: Path, latest_dir: Path
) -> dict[str, Any]:
    release_dir = Path(release_dir).resolve()
    source_dir = Path(source_dir).resolve()
    latest_dir = Path(latest_dir).resolve()
    archive_path = release_dir / SOURCE_ARCHIVE
    if archive_path.exists():
        raise FileExistsError(f"Source archive already exists: {archive_path}")
    if latest_dir.exists():
        raise FileExistsError(f"Latest pointer already exists: {latest_dir}")

    manifest = verify_release(release_dir)
    captured = verify_sources(source_dir)
    archive_tmp = archive_path.with_suffix(".tmp")
    try:
        with archive_tmp.open("wb") as raw_archive:
            with gzip.GzipFile(
                filename="", mode="wb", fileobj=raw_archive, mtime=0
            ) as compressed:
                with tarfile.open(
                    fileobj=compressed, mode="w", format=tarfile.PAX_FORMAT
                ) as archive:
                    for filename in sorted(row["filename"] for row in captured):
                        _add_deterministic_file(
                            archive,
                            source_dir / filename,
                            f"official-sources/{filename}",
                        )
                    _add_deterministic_file(
                        archive,
                        source_dir / "source_capture.json",
                        "official-sources/source_capture.json",
                    )
        archive_tmp.replace(archive_path)

        checksums_path = release_dir / "SHA256SUMS"
        lines = checksums_path.read_text(encoding="ascii").rstrip("\r\n")
        lines += f"\r\n{sha256(archive_path)}  {SOURCE_ARCHIVE}\r\n"
        checksums_path.write_text(lines, encoding="ascii", newline="")

        staging = Path(tempfile.mkdtemp(prefix=f".{latest_dir.name}-", dir=latest_dir.parent))
        shutil.copy2(release_dir / "manifest.json", staging / "manifest.json")
        shutil.copy2(checksums_path, staging / "SHA256SUMS")
        version = str(manifest["dataset_version"])
        (staging / "README.md").write_text(
            "# Arancel MX latest release\n\n"
            f"Dataset version: `{version}`  \n"
            f"GitHub tag: `data-{version}`\n\n"
            "Download the required asset from GitHub Releases and verify it "
            "against `SHA256SUMS` before use.\n",
            encoding="utf-8",
        )
        staging.replace(latest_dir)
    except Exception:
        if archive_tmp.exists():
            archive_tmp.unlink()
        if archive_path.exists():
            archive_path.unlink()
        raise
    return {
        "dataset_version": manifest["dataset_version"],
        "validation_status": manifest["validation_status"],
        "source_count": len(captured),
        "source_archive_sha256": sha256(archive_path),
    }

