"""Layered integrity validation for downloaded and local consumer datasets."""

from __future__ import annotations

import hashlib
import json
from pathlib import Path
import re
from typing import Literal, Mapping

import duckdb

from arancel_mx.consumer.errors import DatasetIntegrityError, DatasetSchemaError
from arancel_mx.consumer.models import DatasetInfo


SUPPORTED_SCHEMA_VERSIONS = frozenset({"2"})
_SHA256_LINE_RE = re.compile(r"^([0-9a-fA-F]{64})  ([A-Za-z0-9_.-]+)$")
_REQUIRED_MANIFEST_FIELDS = ("dataset_version", "schema_version", "validation_status")


def sha256_file(path: Path) -> str:
    """Return the SHA-256 digest of a file using bounded-memory reads."""

    digest = hashlib.sha256()
    try:
        with Path(path).open("rb") as stream:
            for chunk in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(chunk)
    except OSError as exc:
        raise DatasetIntegrityError(f"cannot hash dataset asset: {path}") from exc
    return digest.hexdigest()


def parse_sha256sums(text: str) -> dict[str, str]:
    """Parse the repository's strict ``<sha256><two spaces><basename>`` contract."""

    declared: dict[str, str] = {}
    lines = text.splitlines()
    if not lines:
        raise DatasetIntegrityError("SHA256SUMS is empty")
    for line in lines:
        match = _SHA256_LINE_RE.fullmatch(line)
        if match is None:
            raise DatasetIntegrityError(f"invalid SHA256SUMS line: {line!r}")
        digest, filename = match.groups()
        if filename in declared:
            raise DatasetIntegrityError(f"duplicate SHA256SUMS filename: {filename}")
        declared[filename] = digest.lower()
    return declared


def _validate_manifest_mapping(manifest: Mapping[str, object]) -> dict[str, object]:
    result = dict(manifest)
    for field in _REQUIRED_MANIFEST_FIELDS:
        value = result.get(field)
        if not isinstance(value, str) or not value.strip():
            raise DatasetIntegrityError(f"manifest missing or invalid {field}")
    if result["validation_status"] != "passed":
        raise DatasetIntegrityError("manifest validation_status must be passed")
    return result


def load_manifest(path: Path) -> dict[str, object]:
    """Load and validate the minimum release-manifest contract used by consumers."""

    try:
        payload = json.loads(Path(path).read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise DatasetIntegrityError("manifest contains invalid JSON") from exc
    except OSError as exc:
        raise DatasetIntegrityError(f"cannot read manifest: {path}") from exc
    if not isinstance(payload, dict):
        raise DatasetIntegrityError("manifest must be a JSON object")
    return _validate_manifest_mapping(payload)


def verify_api_digest(
    path: Path,
    expected: str | None,
) -> Literal["verified", "unavailable"]:
    """Verify GitHub's API-provided SHA-256 when the platform exposes one."""

    if expected is None:
        return "unavailable"
    if re.fullmatch(r"[0-9a-fA-F]{64}", expected) is None:
        raise DatasetIntegrityError("GitHub digest is malformed")
    actual = sha256_file(Path(path))
    if actual != expected.lower():
        raise DatasetIntegrityError(
            f"GitHub digest mismatch for {Path(path).name}: expected={expected.lower()} actual={actual}"
        )
    return "verified"


def _validate_expected_tag(manifest: Mapping[str, object], expected_tag: str | None) -> None:
    if expected_tag is None:
        return
    if not expected_tag.startswith("data-"):
        raise DatasetIntegrityError(f"invalid resolved tag: {expected_tag}")
    expected_version = expected_tag.removeprefix("data-")
    if manifest["dataset_version"] != expected_version:
        raise DatasetIntegrityError(
            "manifest dataset version does not match resolved tag: "
            f"tag={expected_tag} manifest={manifest['dataset_version']}"
        )


def validate_duckdb(
    path: Path,
    *,
    manifest: Mapping[str, object] | None,
    expected_tag: str | None,
    release_verified: bool,
    github_digest_state: Literal["verified", "unavailable", "not_applicable"],
) -> DatasetInfo:
    """Validate the released public view and release metadata in read-only mode."""

    db_path = Path(path)
    checked_manifest = (
        None if manifest is None else _validate_manifest_mapping(manifest)
    )
    if checked_manifest is not None:
        _validate_expected_tag(checked_manifest, expected_tag)

    try:
        conn = duckdb.connect(str(db_path), read_only=True)
    except duckdb.Error as exc:
        raise DatasetIntegrityError(f"cannot open DuckDB dataset: {db_path}") from exc

    try:
        try:
            columns = [row[0] for row in conn.execute("DESCRIBE arancel_mx").fetchall()]
        except duckdb.Error as exc:
            raise DatasetIntegrityError("required arancel_mx view is missing or invalid") from exc
        required_columns = {
            "record_id",
            "code",
            "level",
            "description",
            "dataset_version",
            "schema_version",
            "is_current",
        }
        missing_columns = required_columns - set(columns)
        if missing_columns:
            raise DatasetIntegrityError(
                f"arancel_mx view is missing required columns: {sorted(missing_columns)}"
            )

        try:
            rows = conn.execute(
                """
                SELECT dataset_version, schema_version, validation_status
                FROM dataset_release
                """
            ).fetchall()
        except duckdb.Error as exc:
            raise DatasetIntegrityError("required dataset_release table is missing") from exc
        if len(rows) != 1:
            raise DatasetIntegrityError(
                f"dataset_release must contain exactly one row, found {len(rows)}"
            )
        dataset_version, schema_version, validation_status = rows[0]
        dataset_version = str(dataset_version)
        schema_version = str(schema_version)
        if validation_status != "passed":
            raise DatasetIntegrityError("dataset_release validation_status must be passed")

        if checked_manifest is not None:
            manifest_version = str(checked_manifest["dataset_version"])
            manifest_schema = str(checked_manifest["schema_version"])
            if dataset_version != manifest_version:
                raise DatasetIntegrityError(
                    "DuckDB dataset version does not match manifest: "
                    f"database={dataset_version} manifest={manifest_version}"
                )
            if schema_version != manifest_schema:
                raise DatasetIntegrityError(
                    "DuckDB schema does not match manifest: "
                    f"database={schema_version} manifest={manifest_schema}"
                )

        if schema_version not in SUPPORTED_SCHEMA_VERSIONS:
            raise DatasetSchemaError(
                f"unsupported dataset schema version: {schema_version}; "
                f"supported={sorted(SUPPORTED_SCHEMA_VERSIONS)}"
            )

        return DatasetInfo(
            dataset_version=dataset_version,
            schema_version=schema_version,
            path=str(db_path),
            source="managed-cache" if release_verified else "local",
            structural_valid=True,
            release_verified=release_verified,
            github_digest_state=github_digest_state,
        )
    except (DatasetIntegrityError, DatasetSchemaError):
        raise
    except duckdb.Error as exc:
        raise DatasetIntegrityError(f"DuckDB validation failed: {db_path}") from exc
    finally:
        conn.close()
