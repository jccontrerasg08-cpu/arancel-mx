from __future__ import annotations

import hashlib
import json
from pathlib import Path

import duckdb
import pytest

from arancel_mx.consumer.errors import DatasetIntegrityError, DatasetSchemaError
from arancel_mx.consumer.integrity import (
    SUPPORTED_SCHEMA_VERSIONS,
    load_manifest,
    parse_sha256sums,
    sha256_file,
    validate_duckdb,
    verify_api_digest,
)
from tests.consumer.conftest import create_consumer_duckdb


TAG = "data-2026.08.11"


def _manifest(path: Path, **updates: object) -> dict[str, object]:
    payload: dict[str, object] = {
        "dataset_version": "2026.08.11",
        "schema_version": "2",
        "validation_status": "passed",
    }
    payload.update(updates)
    path.write_text(json.dumps(payload), encoding="utf-8")
    return payload


def test_supported_schema_versions_are_explicit() -> None:
    assert SUPPORTED_SCHEMA_VERSIONS == frozenset({"2"})


def test_sha256_file_hashes_in_chunks(tmp_path: Path) -> None:
    path = tmp_path / "asset.bin"
    body = b"abc" * (1024 * 1024)
    path.write_bytes(body)
    assert sha256_file(path) == hashlib.sha256(body).hexdigest()


def test_parse_sha256sums_accepts_exact_two_column_contract() -> None:
    text = (
        f"{'a' * 64}  arancel_mx.duckdb\n"
        f"{'B' * 64}  manifest.json\r\n"
    )
    assert parse_sha256sums(text) == {
        "arancel_mx.duckdb": "a" * 64,
        "manifest.json": "b" * 64,
    }


def test_parse_sha256sums_rejects_invalid_hash() -> None:
    with pytest.raises(DatasetIntegrityError, match="SHA256SUMS"):
        parse_sha256sums("not-a-hash  arancel_mx.duckdb\n")


def test_parse_sha256sums_rejects_duplicate_filename() -> None:
    line = f"{'a' * 64}  arancel_mx.duckdb\n"
    with pytest.raises(DatasetIntegrityError, match="duplicate"):
        parse_sha256sums(line + line)


def test_parse_sha256sums_rejects_paths_and_single_space() -> None:
    with pytest.raises(DatasetIntegrityError):
        parse_sha256sums(f"{'a' * 64} path/arancel_mx.duckdb\n")
    with pytest.raises(DatasetIntegrityError):
        parse_sha256sums(f"{'a' * 64} arancel_mx.duckdb\n")


@pytest.mark.parametrize("missing", ["dataset_version", "schema_version", "validation_status"])
def test_manifest_requires_dataset_version_schema_version_and_validation_status(
    tmp_path: Path,
    missing: str,
) -> None:
    path = tmp_path / "manifest.json"
    payload = {
        "dataset_version": "2026.08.11",
        "schema_version": "2",
        "validation_status": "passed",
    }
    del payload[missing]
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(DatasetIntegrityError, match=missing):
        load_manifest(path)


def test_manifest_requires_validation_status_passed(tmp_path: Path) -> None:
    path = tmp_path / "manifest.json"
    _manifest(path, validation_status="failed")
    with pytest.raises(DatasetIntegrityError, match="validation_status"):
        load_manifest(path)


def test_manifest_requires_json_object(tmp_path: Path) -> None:
    path = tmp_path / "manifest.json"
    path.write_text("[]", encoding="utf-8")
    with pytest.raises(DatasetIntegrityError, match="JSON object"):
        load_manifest(path)


def test_manifest_invalid_json_is_integrity_error(tmp_path: Path) -> None:
    path = tmp_path / "manifest.json"
    path.write_text("{", encoding="utf-8")
    with pytest.raises(DatasetIntegrityError, match="invalid JSON"):
        load_manifest(path)


def test_api_digest_present_and_matching_is_verified(tmp_path: Path) -> None:
    path = tmp_path / "asset"
    path.write_bytes(b"hello")
    expected = hashlib.sha256(b"hello").hexdigest()
    assert verify_api_digest(path, expected) == "verified"


def test_api_digest_missing_is_unavailable(tmp_path: Path) -> None:
    path = tmp_path / "asset"
    path.write_bytes(b"hello")
    assert verify_api_digest(path, None) == "unavailable"


def test_api_digest_present_and_mismatched_raises_integrity_error(tmp_path: Path) -> None:
    path = tmp_path / "asset"
    path.write_bytes(b"hello")
    with pytest.raises(DatasetIntegrityError, match="GitHub digest"):
        verify_api_digest(path, "0" * 64)


def test_duckdb_opens_read_only(consumer_duckdb: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    real_connect = duckdb.connect
    calls: list[bool] = []

    def recording_connect(database: str, *, read_only: bool = False, **kwargs: object):
        calls.append(read_only)
        return real_connect(database, read_only=read_only, **kwargs)

    monkeypatch.setattr(duckdb, "connect", recording_connect)
    info = validate_duckdb(
        consumer_duckdb,
        manifest=None,
        expected_tag=None,
        release_verified=False,
        github_digest_state="not_applicable",
    )
    assert info.structural_valid is True
    assert calls == [True]


def test_duckdb_requires_arancel_mx_view(tmp_path: Path) -> None:
    path = create_consumer_duckdb(tmp_path / "missing-view.duckdb", include_view=False)
    with pytest.raises(DatasetIntegrityError, match="arancel_mx"):
        validate_duckdb(
            path,
            manifest=None,
            expected_tag=None,
            release_verified=False,
            github_digest_state="not_applicable",
        )


def test_duckdb_requires_dataset_release_row(tmp_path: Path) -> None:
    path = create_consumer_duckdb(tmp_path / "missing-release.duckdb", include_release=False)
    with pytest.raises(DatasetIntegrityError, match="dataset_release"):
        validate_duckdb(
            path,
            manifest=None,
            expected_tag=None,
            release_verified=False,
            github_digest_state="not_applicable",
        )


def test_duckdb_rejects_unsupported_schema(tmp_path: Path) -> None:
    path = create_consumer_duckdb(tmp_path / "schema.duckdb", schema_version="999")
    with pytest.raises(DatasetSchemaError, match="999"):
        validate_duckdb(
            path,
            manifest=None,
            expected_tag=None,
            release_verified=False,
            github_digest_state="not_applicable",
        )


def test_manifest_version_must_match_resolved_tag(consumer_duckdb: Path) -> None:
    manifest = {
        "dataset_version": "2026.08.10",
        "schema_version": "2",
        "validation_status": "passed",
    }
    with pytest.raises(DatasetIntegrityError, match="resolved tag"):
        validate_duckdb(
            consumer_duckdb,
            manifest=manifest,
            expected_tag=TAG,
            release_verified=True,
            github_digest_state="verified",
        )


def test_duckdb_release_version_must_match_manifest(consumer_duckdb: Path) -> None:
    manifest = {
        "dataset_version": "2026.08.10",
        "schema_version": "2",
        "validation_status": "passed",
    }
    with pytest.raises(DatasetIntegrityError, match="dataset version"):
        validate_duckdb(
            consumer_duckdb,
            manifest=manifest,
            expected_tag=None,
            release_verified=True,
            github_digest_state="verified",
        )


def test_duckdb_schema_must_match_manifest(consumer_duckdb: Path) -> None:
    manifest = {
        "dataset_version": "2026.08.11",
        "schema_version": "999",
        "validation_status": "passed",
    }
    with pytest.raises(DatasetIntegrityError, match="schema"):
        validate_duckdb(
            consumer_duckdb,
            manifest=manifest,
            expected_tag=TAG,
            release_verified=True,
            github_digest_state="verified",
        )


def test_duckdb_release_status_must_be_passed(tmp_path: Path) -> None:
    path = create_consumer_duckdb(tmp_path / "failed.duckdb", validation_status="failed")
    with pytest.raises(DatasetIntegrityError, match="validation_status"):
        validate_duckdb(
            path,
            manifest=None,
            expected_tag=None,
            release_verified=False,
            github_digest_state="not_applicable",
        )


def test_corrupt_duckdb_maps_to_dataset_integrity_error(tmp_path: Path) -> None:
    path = tmp_path / "corrupt.duckdb"
    path.write_bytes(b"not duckdb")
    with pytest.raises(DatasetIntegrityError, match="DuckDB") as raised:
        validate_duckdb(
            path,
            manifest=None,
            expected_tag=None,
            release_verified=False,
            github_digest_state="not_applicable",
        )
    assert isinstance(raised.value.__cause__, duckdb.Error)


def test_local_open_without_manifest_reports_release_verified_false(consumer_duckdb: Path) -> None:
    info = validate_duckdb(
        consumer_duckdb,
        manifest=None,
        expected_tag=None,
        release_verified=False,
        github_digest_state="not_applicable",
    )
    assert info.dataset_version == "2026.08.11"
    assert info.schema_version == "2"
    assert info.source == "local"
    assert info.release_verified is False
    assert info.github_digest_state == "not_applicable"


def test_managed_cache_validation_reports_release_verified_true(consumer_duckdb: Path) -> None:
    manifest = {
        "dataset_version": "2026.08.11",
        "schema_version": "2",
        "validation_status": "passed",
    }
    info = validate_duckdb(
        consumer_duckdb,
        manifest=manifest,
        expected_tag=TAG,
        release_verified=True,
        github_digest_state="verified",
    )
    assert info.source == "managed-cache"
    assert info.release_verified is True
    assert info.github_digest_state == "verified"


def test_validate_duckdb_rejects_duplicate_current_codes(tmp_path: Path) -> None:
    path = create_consumer_duckdb(tmp_path / "duplicate.duckdb")
    conn = duckdb.connect(str(path))
    try:
        conn.execute(
            """
            INSERT INTO canonical_record
            SELECT 'r-frac-dup' AS record_id, * EXCLUDE (record_id)
            FROM canonical_record
            WHERE record_id = 'r-frac'
            """
        )
        conn.execute(
            """
            INSERT INTO record_provenance
            SELECT 'r-frac-dup', source_document_id, role, is_primary
            FROM record_provenance
            WHERE record_id = 'r-frac'
            """
        )
    finally:
        conn.close()

    with pytest.raises(DatasetIntegrityError, match="multiple current rows"):
        validate_duckdb(
            path,
            manifest=None,
            expected_tag=None,
            release_verified=False,
            github_digest_state="not_applicable",
        )
