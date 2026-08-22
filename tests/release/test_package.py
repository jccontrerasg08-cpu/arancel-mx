import hashlib
import json
import tarfile
from pathlib import Path

import pytest

from arancel_mx.release.package import (
    PUBLIC_RELEASE_ASSETS,
    RELEASE_ARTIFACTS,
    build_release,
    prepare_release_archive,
    verify_publication_bundle,
    verify_release,
    verify_sources,
)


def _sha256(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _manifest(hashes):
    return {
        "dataset_version": "2026.08.09",
        "schema_version": "2",
        "validation_status": "passed",
        "row_count": 1,
        "registry_version": "2026-08-10",
        "registry_sha256": "b" * 64,
        "git_commit_sha": "local",
        "github_run_id": "local",
        "github_run_attempt": "local",
        "github_workflow_ref": "local",
        "github_artifact_name": "local",
        "level_counts": {
            "hs2": 1,
            "hs4": 0,
            "hs6": 0,
            "fraccion8": 0,
            "nico10": 0,
        },
        "reconciliation": {
            "publishable": True,
            "error_codes": [],
            "discrepancies": [],
            "legal_document_ids": ["doc-1"],
            "proposal_document_ids": [],
            "indicator_document_ids": [],
        },
        "source_identity": [
            {
                "dataset_key": "ligie",
                "document_role": "ligie_snapshot",
                "source_url": "https://www.snice.gob.mx/ligie.xlsx",
                "sha256": "a" * 64,
                "registry_version": "2026-08-10",
            }
        ],
        "artifact_sha256": hashes,
    }


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
    manifest = _manifest(hashes)
    manifest_path = release / "manifest.json"
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    checksum_hashes = {**hashes, "manifest.json": _sha256(manifest_path)}
    (release / "SHA256SUMS").write_text(
        "".join(
            f"{digest}  {name}\n" for name, digest in sorted(checksum_hashes.items())
        ),
        encoding="ascii",
    )
    source = sources / "ligie.xlsx"
    source.write_bytes(b"official source")
    capture = [{"filename": source.name, "sha256": _sha256(source)}]
    (sources / "source_capture.json").write_text(json.dumps(capture), encoding="utf-8")
    return release, sources


def _publication_bundle(tmp_path):
    release, sources = _fixture(tmp_path)
    prepare_release_archive(release, sources, tmp_path / "latest")
    return release


def test_build_release_delegates_to_deterministic_database_export(tmp_path, monkeypatch):
    database = tmp_path / "arancel.duckdb"
    database.write_bytes(b"database")
    expected = {"dataset_version": "2026.08.09"}
    monkeypatch.setattr(
        "arancel_mx.pipeline.build.export_arancel_release",
        lambda source, output: expected if source == database and output == tmp_path / "out" else None,
    )

    assert build_release(database, tmp_path / "out") == expected


def test_verify_release_requires_complete_schema_v2_provenance(tmp_path):
    release, _sources = _fixture(tmp_path)
    manifest_path = release / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    del manifest["registry_sha256"]
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ValueError, match="registry_sha256"):
        verify_release(release)


def test_verify_release_rejects_malformed_source_history(tmp_path):
    release, _sources = _fixture(tmp_path)
    manifest_path = release / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["source_history"] = {
        "previous_dataset_version": "2026.08.08",
        "changes": "not-a-list",
    }
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
    checksums_path = release / "SHA256SUMS"
    checksums = [
        line
        for line in checksums_path.read_text(encoding="ascii").splitlines()
        if not line.endswith("  manifest.json")
    ]
    checksums.append(f"{_sha256(manifest_path)}  manifest.json")
    checksums_path.write_text(chr(10).join(checksums) + chr(10), encoding="ascii")

    with pytest.raises(ValueError, match="source_history"):
        verify_release(release)


def test_verify_release_rejects_non_publishable_reconciliation(tmp_path):
    release, _sources = _fixture(tmp_path)
    manifest_path = release / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["reconciliation"]["publishable"] = False
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ValueError, match="reconciliation"):
        verify_release(release)


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


def test_source_archive_is_byte_deterministic(tmp_path, monkeypatch):
    first_root = tmp_path / "first"
    second_root = tmp_path / "second"
    first_root.mkdir()
    second_root.mkdir()
    first_release, first_sources = _fixture(first_root)
    second_release, second_sources = _fixture(second_root)

    monkeypatch.setattr("gzip.time.time", lambda: 1)
    first = prepare_release_archive(
        first_release, first_sources, tmp_path / "first-latest"
    )
    monkeypatch.setattr("gzip.time.time", lambda: 2)
    second = prepare_release_archive(
        second_release, second_sources, tmp_path / "second-latest"
    )

    assert first["source_archive_sha256"] == second["source_archive_sha256"]
    assert (first_release / "official-sources.tar.gz").read_bytes() == (
        second_release / "official-sources.tar.gz"
    ).read_bytes()


def test_corrupt_source_creates_no_archive_or_latest_pointer(tmp_path):
    release, sources = _fixture(tmp_path)
    (sources / "ligie.xlsx").write_bytes(b"corrupt")
    latest = tmp_path / "latest"

    with pytest.raises(ValueError, match="source checksum mismatch"):
        prepare_release_archive(release, sources, latest)

    assert not (release / "official-sources.tar.gz").exists()
    assert not latest.exists()


def test_verify_publication_bundle_accepts_exact_six_verified_assets(tmp_path):
    release = _publication_bundle(tmp_path)

    manifest = verify_publication_bundle(release)

    assert manifest["validation_status"] == "passed"
    assert tuple(path.name for path in sorted(release.iterdir())) == tuple(
        sorted(PUBLIC_RELEASE_ASSETS)
    )


def test_verify_publication_bundle_rejects_missing_asset(tmp_path):
    release = _publication_bundle(tmp_path)
    (release / "arancel_mx.csv").unlink()

    with pytest.raises(ValueError, match="exactly the six public assets"):
        verify_publication_bundle(release)


def test_verify_publication_bundle_rejects_extra_asset(tmp_path):
    release = _publication_bundle(tmp_path)
    (release / "debug.txt").write_text("not public", encoding="utf-8")

    with pytest.raises(ValueError, match="exactly the six public assets"):
        verify_publication_bundle(release)


def test_verify_publication_bundle_rejects_corrupted_source_archive(tmp_path):
    release = _publication_bundle(tmp_path)
    with (release / "official-sources.tar.gz").open("ab") as stream:
        stream.write(b"corrupt")

    with pytest.raises(ValueError, match="checksum mismatch"):
        verify_publication_bundle(release)


def test_verify_publication_bundle_rejects_invalid_reconciliation_metadata(tmp_path):
    release = _publication_bundle(tmp_path)
    manifest_path = release / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["reconciliation"]["publishable"] = False
    manifest_path.write_text(json.dumps(manifest), encoding="utf-8")

    with pytest.raises(ValueError, match="reconciliation"):
        verify_publication_bundle(release)


@pytest.mark.parametrize("missing_name", ["manifest.json", "official-sources.tar.gz"])
def test_publication_bundle_requires_checksum_coverage_for_manifest_and_sources(
    tmp_path, missing_name
):
    release = _publication_bundle(tmp_path)
    checksums_path = release / "SHA256SUMS"
    lines = [
        line
        for line in checksums_path.read_text(encoding="ascii").splitlines()
        if not line.endswith(f"  {missing_name}")
    ]
    checksums_path.write_text("\n".join(lines) + "\n", encoding="ascii")

    with pytest.raises(ValueError, match="checksum coverage"):
        verify_publication_bundle(release)


def test_verify_release_accepts_uppercase_sha256sums_digests(tmp_path):
    release, _sources = _fixture(tmp_path)
    checksums_path = release / "SHA256SUMS"
    checksums_path.write_text(
        "".join(
            f"{digest.upper()}  {name}\n"
            for digest, name in (
                line.split("  ", 1)
                for line in checksums_path.read_text(encoding="ascii").splitlines()
            )
        ),
        encoding="ascii",
    )

    assert verify_release(release)["validation_status"] == "passed"


def test_verify_sources_rejects_non_object_capture_row(tmp_path):
    _release, sources = _fixture(tmp_path)
    (sources / "source_capture.json").write_text(json.dumps(["oops"]), encoding="utf-8")

    with pytest.raises(ValueError, match="must be an object"):
        verify_sources(sources)


def test_failed_latest_staging_leaves_checksums_and_archive_untouched(tmp_path, monkeypatch):
    release, sources = _fixture(tmp_path)
    checksums_before = (release / "SHA256SUMS").read_text(encoding="ascii")
    latest = tmp_path / "latest"

    def boom(*_args, **_kwargs):
        raise OSError("no tmp")

    monkeypatch.setattr("arancel_mx.release.package.tempfile.mkdtemp", boom)

    with pytest.raises(OSError, match="no tmp"):
        prepare_release_archive(release, sources, latest)

    assert not (release / "official-sources.tar.gz").exists()
    assert (release / "SHA256SUMS").read_text(encoding="ascii") == checksums_before
    assert "official-sources.tar.gz" not in checksums_before
    assert not latest.exists()
    assert list(tmp_path.glob(".latest-*")) == []


def test_failed_latest_copy_leaves_checksums_and_archive_untouched(tmp_path, monkeypatch):
    release, sources = _fixture(tmp_path)
    checksums_before = (release / "SHA256SUMS").read_text(encoding="ascii")
    latest = tmp_path / "latest"

    def boom(*_args, **_kwargs):
        raise OSError("disk full")

    monkeypatch.setattr("arancel_mx.release.package.shutil.copy2", boom)

    with pytest.raises(OSError, match="disk full"):
        prepare_release_archive(release, sources, latest)

    assert not (release / "official-sources.tar.gz").exists()
    assert (release / "SHA256SUMS").read_text(encoding="ascii") == checksums_before
    assert not latest.exists()
    assert list(tmp_path.glob(".latest-*")) == []


def test_failed_latest_replace_restores_dirty_checksums(tmp_path, monkeypatch):
    release, sources = _fixture(tmp_path)
    checksums_before = (release / "SHA256SUMS").read_bytes()
    latest = tmp_path / "latest"
    real_replace = Path.replace

    def replace(self, target):
        if Path(target).resolve() == latest.resolve():
            raise OSError("rename failed")
        return real_replace(self, target)

    monkeypatch.setattr(Path, "replace", replace)

    with pytest.raises(OSError, match="rename failed"):
        prepare_release_archive(release, sources, latest)

    assert not (release / "official-sources.tar.gz").exists()
    assert (release / "SHA256SUMS").read_bytes() == checksums_before
    assert not latest.exists()
    assert list(tmp_path.glob(".latest-*")) == []


def test_staging_removed_if_checksum_restore_fails(tmp_path, monkeypatch):
    release, sources = _fixture(tmp_path)
    checksums_path = (release / "SHA256SUMS").resolve()
    latest = tmp_path / "latest"
    real_replace = Path.replace
    real_write_bytes = Path.write_bytes

    def replace(self, target):
        if Path(target).resolve() == latest.resolve():
            raise OSError("rename failed")
        return real_replace(self, target)

    def write_bytes(self, data):
        if self.resolve() == checksums_path and b"official-sources.tar.gz" not in data:
            raise OSError("restore failed")
        return real_write_bytes(self, data)

    monkeypatch.setattr(Path, "replace", replace)
    monkeypatch.setattr(Path, "write_bytes", write_bytes)

    with pytest.raises(OSError, match="restore failed"):
        prepare_release_archive(release, sources, latest)

    assert list(tmp_path.glob(".latest-*")) == []
    assert not latest.exists()
    assert not (release / "official-sources.tar.gz").exists()
