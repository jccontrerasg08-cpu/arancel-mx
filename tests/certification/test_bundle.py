from datetime import date, datetime
from decimal import Decimal
import hashlib
import io
import json
from pathlib import Path
import tarfile

import pytest

from arancel_mx.certification.bundle import certify_bundle
from arancel_mx.pipeline.build import export_arancel_release, materialize_arancel
from arancel_mx.release.package import (
    PUBLIC_RELEASE_ASSETS,
    RELEASE_ARTIFACTS,
    prepare_release_archive,
)
from arancel_mx.storage.duckdb import connect, init_tariff_db


SOURCE_BYTES = b"official source bytes"
SOURCE_FILENAME = "ligie.xlsx"
SOURCE_DOCUMENT_ID = "source-1"
SOURCE_URL = "https://www.snice.gob.mx/ligie.xlsx"


def _sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def _source_sha256() -> str:
    return hashlib.sha256(SOURCE_BYTES).hexdigest()


def _release_metadata() -> dict[str, object]:
    return {
        "registry_version": "2026-08-10",
        "registry_sha256": "b" * 64,
        "git_commit_sha": "local",
        "github_run_id": "local",
        "github_run_attempt": "local",
        "github_workflow_ref": "local",
        "github_artifact_name": "local",
        "reconciliation": {
            "publishable": True,
            "error_codes": [],
            "discrepancies": [],
            "legal_document_ids": [SOURCE_DOCUMENT_ID],
            "proposal_document_ids": [],
            "indicator_document_ids": [],
        },
        "source_identity": [
            {
                "dataset_key": "ligie",
                "document_role": "ligie_snapshot",
                "source_url": SOURCE_URL,
                "sha256": _source_sha256(),
                "registry_version": "2026-08-10",
            }
        ],
    }


def _classification(level: str, code: str, description: str) -> dict[str, object]:
    return {
        "level": level,
        "code": code,
        "description": description,
        "ligie_version": "LIGIE-2022",
        "validity_basis": "observed_snapshot",
        "updated_at": date(2026, 8, 10),
        "source_document_id": SOURCE_DOCUMENT_ID,
    }


def _write_checksum_set(release: Path, names: list[str]) -> None:
    (release / "SHA256SUMS").write_text(
        "".join(f"{_sha256(release / name)}  {name}\n" for name in sorted(names)),
        encoding="ascii",
    )


def _write_publication_checksums(release: Path) -> None:
    _write_checksum_set(
        release,
        list(set(PUBLIC_RELEASE_ASSETS) - {"SHA256SUMS"}),
    )


def _refresh_manifest_artifact_hashes(release: Path) -> None:
    manifest_path = release / "manifest.json"
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    manifest["artifact_sha256"] = {
        name: _sha256(release / name) for name in RELEASE_ARTIFACTS
    }
    manifest_path.write_text(
        json.dumps(manifest, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    _write_publication_checksums(release)


def _capture() -> list[dict[str, object]]:
    return [
        {
            "dataset_key": "ligie",
            "document_role": "ligie_snapshot",
            "filename": SOURCE_FILENAME,
            "media_type": (
                "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            ),
            "sha256": _source_sha256(),
            "source_document_id": SOURCE_DOCUMENT_ID,
            "source_url": SOURCE_URL,
            "published_at": None,
        }
    ]


def _bundle(tmp_path: Path) -> Path:
    warehouse = init_tariff_db(tmp_path / "warehouse.duckdb")
    source = {
        "source_document_id": SOURCE_DOCUMENT_ID,
        "authority": "Secretaría de Economía / SNICE",
        "publication_venue": "SNICE",
        "title": "LIGIE",
        "source_url": SOURCE_URL,
        "media_type": (
            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
        ),
        "sha256": _source_sha256(),
        "observed_at": date(2026, 8, 10),
        "retrieved_at": datetime(2026, 8, 10, 20, 35, 49),
    }
    classifications = [
        _classification("hs2", "01", "Animales vivos"),
        _classification("hs4", "0101", "Caballos, asnos, mulos y burdéganos"),
        _classification("hs6", "010121", "Reproductores de raza pura"),
        _classification("fraccion8", "01012101", "Reproductores de raza pura"),
        _classification("nico10", "0101210100", "Reproductores de raza pura"),
    ]
    rates = [
        {
            "code": "01012101",
            "unit_code": "01",
            "unit_name": "Cabeza",
            "igi_text": "15",
            "igi_kind": "ad_valorem",
            "igi_value": Decimal("15"),
            "ige_text": "Ex.",
            "ige_kind": "exento",
            "ige_value": Decimal("0"),
            "ligie_version": "LIGIE-2022",
            "updated_at": date(2026, 8, 10),
            "source_document_id": SOURCE_DOCUMENT_ID,
        }
    ]
    release_meta = {
        "dataset_version": "2026.08.10",
        "schema_version": "2",
        "ligie_version": "LIGIE-2022",
        "effective_as_of": date(2026, 8, 10),
        "generated_at": datetime(2026, 8, 10, 20, 35, 47),
        "release_metadata": _release_metadata(),
    }
    with connect(warehouse) as connection:
        materialize_arancel(
            connection,
            [source],
            classifications,
            rates,
            release_meta,
        )

    release = tmp_path / "release"
    export_arancel_release(warehouse, release)

    sources = tmp_path / "sources"
    sources.mkdir()
    (sources / SOURCE_FILENAME).write_bytes(SOURCE_BYTES)
    (sources / "source_capture.json").write_text(
        json.dumps(_capture(), ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    prepare_release_archive(release, sources, tmp_path / "latest")
    return release


def _replace_archive(
    release: Path,
    members: list[tarfile.TarInfo],
    payloads: list[bytes],
) -> None:
    archive_path = release / "official-sources.tar.gz"
    with tarfile.open(archive_path, "w:gz") as archive:
        for info, payload in zip(members, payloads, strict=True):
            info.size = len(payload)
            archive.addfile(info, io.BytesIO(payload) if payload else None)
    _write_publication_checksums(release)


def _replace_valid_archive(
    release: Path,
    *,
    capture: list[dict[str, object]] | None = None,
    source_bytes: bytes = SOURCE_BYTES,
) -> None:
    capture_bytes = (
        json.dumps(capture or _capture(), ensure_ascii=False, separators=(",", ":"))
        + "\n"
    ).encode("utf-8")
    source_info = tarfile.TarInfo(f"official-sources/{SOURCE_FILENAME}")
    capture_info = tarfile.TarInfo("official-sources/source_capture.json")
    _replace_archive(
        release,
        [source_info, capture_info],
        [source_bytes, capture_bytes],
    )


def test_certify_bundle_accepts_verified_cross_format_bundle(tmp_path: Path):
    release = _bundle(tmp_path)

    report = certify_bundle(release)

    assert report.passed is True
    assert report.row_count == 5
    assert set(report.checks) == {
        "publication_bundle",
        "core_objects",
        "public_columns",
        "release_metadata",
        "row_count",
        "record_ids",
        "hierarchy",
        "value_origin",
        "source_archive",
        "source_provenance",
        "csv_json_equivalence",
    }


def test_certify_bundle_rejects_placeholder_duckdb_bytes(tmp_path: Path):
    release = _bundle(tmp_path)
    (release / "arancel_mx.duckdb").write_bytes(b"duckdb fixture for bundle-only checks")
    _refresh_manifest_artifact_hashes(release)

    with pytest.raises(ValueError, match="DuckDB|readable|open"):
        certify_bundle(release)


def test_certify_bundle_rejects_corrupted_public_asset(tmp_path: Path):
    release = _bundle(tmp_path)
    (release / "arancel_mx.csv").write_bytes(b"corrupted")

    with pytest.raises(ValueError, match="checksum"):
        certify_bundle(release)


def test_certify_bundle_rejects_missing_asset(tmp_path: Path):
    release = _bundle(tmp_path)
    (release / "arancel_mx.csv").unlink()

    with pytest.raises(ValueError, match="exactly the six public assets"):
        certify_bundle(release)


def test_certify_bundle_rejects_unexpected_seventh_asset(tmp_path: Path):
    release = _bundle(tmp_path)
    (release / "debug.txt").write_text("debug", encoding="utf-8")

    with pytest.raises(ValueError, match="exactly the six public assets"):
        certify_bundle(release)


def test_certify_bundle_rejects_malformed_checksum_line(tmp_path: Path):
    release = _bundle(tmp_path)
    with (release / "SHA256SUMS").open("a", encoding="ascii") as stream:
        stream.write("malformed checksum line\n")

    with pytest.raises(ValueError, match="Invalid checksum line"):
        certify_bundle(release)


def test_certify_bundle_rejects_duplicate_checksum_entry(tmp_path: Path):
    release = _bundle(tmp_path)
    checksums = release / "SHA256SUMS"
    first_line = checksums.read_text(encoding="ascii").splitlines()[0]
    with checksums.open("a", encoding="ascii") as stream:
        stream.write(first_line + "\n")

    with pytest.raises(ValueError, match="Duplicate checksum entry"):
        certify_bundle(release)


@pytest.mark.parametrize(
    ("name", "kind"),
    [
        ("/absolute.txt", "file"),
        ("official-sources/../escape.txt", "file"),
        ("official-sources/symlink", "symlink"),
        ("official-sources/hardlink", "hardlink"),
    ],
)
def test_certify_bundle_rejects_unsafe_archive_members(
    tmp_path: Path, name: str, kind: str
):
    release = _bundle(tmp_path)
    info = tarfile.TarInfo(name)
    payload = b"unsafe"
    if kind == "symlink":
        info.type = tarfile.SYMTYPE
        info.linkname = "target"
        payload = b""
    elif kind == "hardlink":
        info.type = tarfile.LNKTYPE
        info.linkname = "target"
        payload = b""
    _replace_archive(release, [info], [payload])

    with pytest.raises(ValueError, match="unsafe source archive member"):
        certify_bundle(release)


def test_certify_bundle_recomputes_archived_source_hashes(tmp_path: Path):
    release = _bundle(tmp_path)
    _replace_valid_archive(release, source_bytes=b"tampered source")

    with pytest.raises(ValueError, match="source checksum mismatch"):
        certify_bundle(release)


def test_certify_bundle_requires_manifest_source_document_match(tmp_path: Path):
    release = _bundle(tmp_path)
    capture = _capture()
    capture[0]["source_document_id"] = "source-other"
    _replace_valid_archive(release, capture=capture)

    with pytest.raises(ValueError, match="source_documents"):
        certify_bundle(release)


def test_certify_bundle_requires_manifest_source_identity_match(tmp_path: Path):
    release = _bundle(tmp_path)
    capture = _capture()
    capture[0]["document_role"] = "other_role"
    _replace_valid_archive(release, capture=capture)

    with pytest.raises(ValueError, match="source_identity"):
        certify_bundle(release)


def test_certify_bundle_rejects_csv_json_value_drift(tmp_path: Path):
    release = _bundle(tmp_path)
    json_path = release / "arancel_mx.json"
    rows = json.loads(json_path.read_text(encoding="utf-8"))
    rows[0]["description"] = "different description"
    json_path.write_text(
        json.dumps(rows, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    _refresh_manifest_artifact_hashes(release)

    with pytest.raises(ValueError, match="CSV/JSON value mismatch"):
        certify_bundle(release)


def test_certify_bundle_rejects_noncanonical_json_columns(tmp_path: Path):
    release = _bundle(tmp_path)
    json_path = release / "arancel_mx.json"
    rows = json.loads(json_path.read_text(encoding="utf-8"))
    rows[0]["unexpected"] = "value"
    json_path.write_text(
        json.dumps(rows, ensure_ascii=False, separators=(",", ":")) + "\n",
        encoding="utf-8",
    )
    _refresh_manifest_artifact_hashes(release)

    with pytest.raises(ValueError, match="JSON columns"):
        certify_bundle(release)
