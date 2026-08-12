"""Independent read-only certification of the six-file public release bundle."""

from __future__ import annotations

import csv
from decimal import Decimal
import hashlib
import json
from pathlib import Path, PurePosixPath
import tarfile
from typing import Any

from arancel_mx.certification.consumer import certify_duckdb
from arancel_mx.certification.reports import CertificationReport
from arancel_mx.domain.normalization import PUBLIC_COLUMNS
from arancel_mx.release.metadata import source_identity_from_manifest
from arancel_mx.release.package import SOURCE_ARCHIVE, verify_publication_bundle


_CAPTURE_FIELDS = (
    "dataset_key",
    "document_role",
    "filename",
    "sha256",
    "source_document_id",
    "source_url",
)

REQUIRED_SOURCE_ROLES = frozenset(
    {
        ("ligie", "ligie_snapshot"),
        ("nico", "nico_snapshot"),
        ("diputados_ligie", "legal_ledger"),
        ("diputados_ligie", "consolidated_text"),
        ("dof_law_reform", "law_reform"),
        ("dof_tariff_decree", "tariff_decree"),
    }
)


def _plain_decimal(value: Decimal) -> str:
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    return text or "0"


def _json_to_csv_text(value: object) -> str:
    if value is None:
        return ""
    if value is True:
        return "true"
    if value is False:
        return "false"
    if isinstance(value, Decimal):
        return _plain_decimal(value)
    if isinstance(value, int):
        return str(value)
    if isinstance(value, str):
        return value
    raise ValueError(f"Unsupported JSON public value type: {type(value).__name__}")


def _safe_archive_name(member: tarfile.TarInfo) -> PurePosixPath:
    name = member.name
    path = PurePosixPath(name)
    if (
        name.startswith("/")
        or "\\" in name
        or ".." in path.parts
        or member.issym()
        or member.islnk()
        or not member.isfile()
        or len(path.parts) != 2
        or path.parts[0] != "official-sources"
    ):
        raise ValueError(f"unsafe source archive member: {name}")
    return path


def _read_source_archive(release_dir: Path) -> tuple[list[dict[str, Any]], dict[str, bytes]]:
    archive_path = release_dir / SOURCE_ARCHIVE
    members_by_name: dict[str, bytes] = {}

    with tarfile.open(archive_path, "r:gz") as archive:
        for member in archive.getmembers():
            path = _safe_archive_name(member)
            name = str(path)
            if name in members_by_name:
                raise ValueError(f"duplicate source archive member: {name}")
            stream = archive.extractfile(member)
            if stream is None:
                raise ValueError(f"source archive member is unreadable: {name}")
            members_by_name[name] = stream.read()

    capture_name = "official-sources/source_capture.json"
    capture_bytes = members_by_name.get(capture_name)
    if capture_bytes is None:
        raise ValueError("source archive missing source_capture.json")
    try:
        captured = json.loads(capture_bytes.decode("utf-8"))
    except (UnicodeDecodeError, json.JSONDecodeError) as exc:
        raise ValueError("source archive source_capture.json is invalid") from exc
    if not isinstance(captured, list) or not captured:
        raise ValueError("source archive source_capture.json must be a non-empty list")

    normalized: list[dict[str, Any]] = []
    filenames: set[str] = set()
    for index, raw in enumerate(captured):
        if not isinstance(raw, dict):
            raise ValueError(f"source capture row {index} must be an object")
        row: dict[str, Any] = raw
        for field in _CAPTURE_FIELDS:
            value = row.get(field)
            if not isinstance(value, str) or not value.strip():
                raise ValueError(f"source capture row {index} has invalid {field}")
        filename = row["filename"]
        if Path(filename).name != filename or filename in filenames:
            raise ValueError(f"source capture row {index} has invalid filename")
        filenames.add(filename)
        member_name = f"official-sources/{filename}"
        content = members_by_name.get(member_name)
        if content is None:
            raise ValueError(f"source archive missing captured source: {filename}")
        actual = hashlib.sha256(content).hexdigest()
        if actual != row["sha256"].lower():
            raise ValueError(f"source checksum mismatch: {filename}")
        normalized.append(row)

    expected_members = {capture_name, *(f"official-sources/{name}" for name in filenames)}
    if set(members_by_name) != expected_members:
        raise ValueError("source archive contains unregistered source files")
    return normalized, members_by_name


def _manifest_source_documents(manifest: dict[str, Any]) -> dict[str, dict[str, Any]]:
    raw_documents = manifest.get("source_documents")
    if not isinstance(raw_documents, list) or not raw_documents:
        raise ValueError("manifest.source_documents must be a non-empty list")
    documents: dict[str, dict[str, Any]] = {}
    for index, raw in enumerate(raw_documents):
        if not isinstance(raw, dict):
            raise ValueError(f"manifest.source_documents[{index}] must be an object")
        document_id = raw.get("source_document_id")
        if not isinstance(document_id, str) or not document_id.strip():
            raise ValueError(f"manifest.source_documents[{index}] has invalid source_document_id")
        if document_id in documents:
            raise ValueError(f"manifest.source_documents contains duplicate {document_id}")
        documents[document_id] = raw
    return documents


def _certify_source_provenance(
    manifest: dict[str, Any], captured: list[dict[str, Any]]
) -> None:
    captured_by_id: dict[str, dict[str, Any]] = {}
    for row in captured:
        source_id = row["source_document_id"]
        if source_id in captured_by_id:
            raise ValueError(f"source capture contains duplicate source_document_id: {source_id}")
        captured_by_id[source_id] = row

    documents = _manifest_source_documents(manifest)
    if set(captured_by_id) != set(documents):
        raise ValueError("source capture does not match manifest.source_documents")
    for source_id, capture in captured_by_id.items():
        document = documents[source_id]
        if (
            document.get("source_url") != capture["source_url"]
            or str(document.get("sha256", "")).lower() != capture["sha256"].lower()
        ):
            raise ValueError(
                f"source capture does not match manifest.source_documents: {source_id}"
            )

    identities = source_identity_from_manifest(manifest)
    registry_version = manifest.get("registry_version")
    manifest_identity = [
        (
            item.dataset_key,
            item.document_role,
            item.source_url,
            item.sha256,
        )
        for item in identities
    ]
    if any(item.registry_version != registry_version for item in identities):
        raise ValueError("manifest.source_identity registry_version mismatch")
    capture_identity = [
        (
            row["dataset_key"],
            row["document_role"],
            row["source_url"],
            row["sha256"].lower(),
        )
        for row in captured
    ]
    if (
        len(set(manifest_identity)) != len(manifest_identity)
        or len(set(capture_identity)) != len(capture_identity)
        or sorted(manifest_identity) != sorted(capture_identity)
    ):
        raise ValueError("source capture does not match manifest.source_identity")

    present_roles = {(row["dataset_key"], row["document_role"]) for row in captured}
    missing_roles = sorted(REQUIRED_SOURCE_ROLES - present_roles)
    if missing_roles:
        raise ValueError(
            "publication bundle is missing required official source roles: "
            + ", ".join(f"{key}/{role}" for key, role in missing_roles)
        )


def _read_csv_rows(path: Path) -> list[dict[str, str]]:
    with path.open("r", encoding="utf-8", newline="") as stream:
        reader = csv.DictReader(stream)
        if reader.fieldnames != list(PUBLIC_COLUMNS):
            raise ValueError("CSV columns do not match the public contract")
        rows = list(reader)
    for index, row in enumerate(rows):
        if None in row or list(row) != list(PUBLIC_COLUMNS):
            raise ValueError(f"CSV row {index} does not match the public columns")
    return rows


def _read_json_rows(path: Path) -> list[dict[str, object]]:
    try:
        raw = json.loads(path.read_text(encoding="utf-8"), parse_float=Decimal)
    except json.JSONDecodeError as exc:
        raise ValueError("arancel_mx.json is invalid JSON") from exc
    if not isinstance(raw, list):
        raise ValueError("arancel_mx.json must contain a JSON array")
    rows: list[dict[str, object]] = []
    for index, row in enumerate(raw):
        if not isinstance(row, dict) or list(row) != list(PUBLIC_COLUMNS):
            raise ValueError(f"JSON columns do not match the public contract at row {index}")
        rows.append(row)
    return rows


def _keyed_csv(rows: list[dict[str, str]]) -> dict[str, dict[str, str]]:
    keyed: dict[str, dict[str, str]] = {}
    for row in rows:
        record_id = row["record_id"]
        if not record_id or record_id in keyed:
            raise ValueError(f"CSV contains invalid or duplicate record_id: {record_id}")
        keyed[record_id] = row
    return keyed


def _keyed_json(rows: list[dict[str, object]]) -> dict[str, dict[str, str]]:
    keyed: dict[str, dict[str, str]] = {}
    for row in rows:
        record_id = row.get("record_id")
        if not isinstance(record_id, str) or not record_id or record_id in keyed:
            raise ValueError(f"JSON contains invalid or duplicate record_id: {record_id}")
        keyed[record_id] = {
            column: _json_to_csv_text(row[column]) for column in PUBLIC_COLUMNS
        }
    return keyed


def _certify_csv_json(release_dir: Path, manifest: dict[str, Any]) -> int:
    csv_rows = _read_csv_rows(release_dir / "arancel_mx.csv")
    json_rows = _read_json_rows(release_dir / "arancel_mx.json")
    row_count = manifest.get("row_count")
    if row_count != len(csv_rows) or row_count != len(json_rows):
        raise ValueError("CSV/JSON row count does not match manifest.row_count")

    csv_by_id = _keyed_csv(csv_rows)
    json_by_id = _keyed_json(json_rows)
    if set(csv_by_id) != set(json_by_id):
        raise ValueError("CSV/JSON record_id sets do not match")
    for record_id in sorted(csv_by_id):
        csv_row = csv_by_id[record_id]
        json_row = json_by_id[record_id]
        for column in PUBLIC_COLUMNS:
            if csv_row[column] != json_row[column]:
                raise ValueError(
                    "CSV/JSON value mismatch: "
                    f"record_id={record_id} column={column}"
                )
    return len(csv_rows)


def certify_bundle(release_dir: Path) -> CertificationReport:
    """Certify hashes, archived evidence, provenance, DuckDB, and CSV/JSON equivalence."""
    release_dir = Path(release_dir).resolve()
    manifest = verify_publication_bundle(release_dir)
    duckdb_checks = certify_duckdb(release_dir / "arancel_mx.duckdb", manifest)
    captured, _members = _read_source_archive(release_dir)
    _certify_source_provenance(manifest, captured)
    row_count = _certify_csv_json(release_dir, manifest)
    return CertificationReport(
        passed=True,
        checks=(
            "publication_bundle",
            *duckdb_checks,
            "source_archive",
            "source_provenance",
            "required_source_roles",
            "csv_json_equivalence",
        ),
        row_count=row_count,
    )
