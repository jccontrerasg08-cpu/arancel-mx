import hashlib
import json
import tarfile

import pytest

from arancel_mx.release.package import (
    RELEASE_ARTIFACTS,
    build_release,
    prepare_release_archive,
    verify_release,
)


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _fixture(tmp_path):
    release = tmp_path / "release"
    sources = tmp_path / "sources"
    release.mkdir()
    sources.mkdir()
    hashes = {}
    for name in RELEASE_ARTIFACTS:
        path = release / name
        path.write_bytes(f"artifact:{name}".encode())
        hashes[name] = _sha256(path)
    manifest = {
        "dataset_version": "2026.08.09",
        "validation_status": "passed",
        "artifact_sha256": hashes,
    }
    (release / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    (release / "SHA256SUMS").write_text(
        "".join(f"{digest}  {name}\n" for name, digest in sorted(hashes.items())),
        encoding="ascii",
    )
    source = sources / "ligie.xlsx"
    source.write_bytes(b"official source")
    capture = [{"filename": source.name, "sha256": _sha256(source)}]
    (sources / "source_capture.json").write_text(json.dumps(capture), encoding="utf-8")
    return release, sources


def test_build_release_delegates_to_deterministic_database_export(tmp_path, monkeypatch):
    database = tmp_path / "arancel.duckdb"
    database.write_bytes(b"database")
    expected = {"dataset_version": "2026.08.09"}
    monkeypatch.setattr(
        "arancel_mx.release.package.export_arancel_release",
        lambda source, output: expected if source == database and output == tmp_path / "out" else None,
    )

    assert build_release(database, tmp_path / "out") == expected


def test_prepares_allowlisted_source_archive_and_latest_pointer(tmp_path):
    release, sources = _fixture(tmp_path)
    latest = tmp_path / "latest"

    summary = prepare_release_archive(release, sources, latest)

    assert summary["source_count"] == 1
    assert verify_release(release)["validation_status"] == "passed"
    with tarfile.open(release / "official-sources.tar.gz") as archive:
        assert sorted(archive.getnames()) == [
            "official-sources/ligie.xlsx",
            "official-sources/source_capture.json",
        ]
    assert sorted(path.name for path in latest.iterdir()) == [
        "README.md",
        "SHA256SUMS",
        "manifest.json",
    ]


def test_corrupt_source_creates_no_archive_or_latest_pointer(tmp_path):
    release, sources = _fixture(tmp_path)
    (sources / "ligie.xlsx").write_bytes(b"corrupt")
    latest = tmp_path / "latest"

    with pytest.raises(ValueError, match="source checksum mismatch"):
        prepare_release_archive(release, sources, latest)

    assert not (release / "official-sources.tar.gz").exists()
    assert not latest.exists()

