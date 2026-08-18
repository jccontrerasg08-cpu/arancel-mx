"""Versioned central operational storage for certified Arancel MX releases."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import date, datetime
from decimal import Decimal
import hashlib
import json
from pathlib import Path
import re
from typing import Protocol, Sequence

import duckdb

from arancel_mx.release.package import verify_publication_bundle


_SHA256 = re.compile(r"^[0-9a-f]{64}$")
_RELEASE_TAG = re.compile(r"^data-\d{4}\.\d{2}\.\d{2}$")


class PromotionError(ValueError):
    """Raised before a candidate release can mutate operational storage."""


class Transaction(Protocol):
    def __enter__(self) -> object: ...

    def __exit__(
        self,
        exc_type: object,
        exc_value: object,
        traceback: object,
    ) -> bool: ...


class OperationalConnection(Protocol):
    def transaction(self) -> Transaction: ...

    def execute(self, statement: str, values: tuple[object, ...] | None = None) -> object: ...


@dataclass(frozen=True)
class OperationalRelease:
    """Identity and observed timing for one independently certified release."""

    tag: str
    dataset_version: str
    schema_version: str
    manifest_sha256: str
    generated_at: datetime
    published_at: datetime
    source_checked_at: datetime


@dataclass(frozen=True)
class OperationalRecord:
    """One public canonical record copied from a certified release."""

    code: str
    level: str
    description: str
    record_hash: str
    source_document_ids: tuple[str, ...]
    payload: dict[str, object]


_OPERATIONAL_SCHEMA = """
CREATE TABLE IF NOT EXISTS operational_release (
    tag TEXT PRIMARY KEY,
    dataset_version TEXT NOT NULL,
    schema_version TEXT NOT NULL,
    manifest_sha256 TEXT NOT NULL UNIQUE,
    generated_at TIMESTAMPTZ NOT NULL,
    published_at TIMESTAMPTZ NOT NULL,
    source_checked_at TIMESTAMPTZ NOT NULL,
    promoted_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS operational_record (
    release_tag TEXT NOT NULL REFERENCES operational_release(tag),
    code TEXT NOT NULL,
    level TEXT NOT NULL,
    description TEXT NOT NULL,
    record_hash TEXT NOT NULL,
    source_document_ids JSONB NOT NULL,
    payload JSONB NOT NULL,
    PRIMARY KEY (release_tag, code)
);

CREATE TABLE IF NOT EXISTS operational_active_release (
    singleton BOOLEAN PRIMARY KEY DEFAULT TRUE CHECK (singleton),
    tag TEXT NOT NULL REFERENCES operational_release(tag),
    promoted_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_operational_record_current_lookup
    ON operational_record (code, release_tag);

CREATE OR REPLACE VIEW current_operational_record AS
SELECT record.*
FROM operational_record AS record
JOIN operational_active_release AS active ON active.tag = record.release_tag;
""".strip()


_INSERT_RELEASE = """
INSERT INTO operational_release (
    tag,
    dataset_version,
    schema_version,
    manifest_sha256,
    generated_at,
    published_at,
    source_checked_at
) VALUES (%s, %s, %s, %s, %s, %s, %s)
ON CONFLICT (tag) DO NOTHING
""".strip()


_INSERT_RECORD = """
INSERT INTO operational_record (
    release_tag,
    code,
    level,
    description,
    record_hash,
    source_document_ids,
    payload
) VALUES (%s, %s, %s, %s, %s, %s::jsonb, %s::jsonb)
ON CONFLICT (release_tag, code) DO NOTHING
""".strip()


_SET_ACTIVE_RELEASE = """
INSERT INTO operational_active_release (singleton, tag)
VALUES (TRUE, %s)
ON CONFLICT (singleton) DO UPDATE
SET tag = EXCLUDED.tag, promoted_at = CURRENT_TIMESTAMP
""".strip()


def _require_timezone(value: datetime, field: str) -> None:
    if value.tzinfo is None or value.utcoffset() is None:
        raise PromotionError(f"{field} must be timezone-aware")


def _validate_release(release: OperationalRelease) -> None:
    if not _RELEASE_TAG.fullmatch(release.tag):
        raise PromotionError("tag must use the immutable data-YYYY.MM.DD format")
    if release.dataset_version != release.tag.removeprefix("data-"):
        raise PromotionError("dataset_version must match tag")
    if not release.schema_version:
        raise PromotionError("schema_version is required")
    if not _SHA256.fullmatch(release.manifest_sha256):
        raise PromotionError("manifest_sha256 must be a lowercase SHA-256 digest")
    for field, value in (
        ("generated_at", release.generated_at),
        ("published_at", release.published_at),
        ("source_checked_at", release.source_checked_at),
    ):
        _require_timezone(value, field)


def _validate_record(record: OperationalRecord) -> None:
    if not record.code or not record.level or not record.description:
        raise PromotionError("operational records require code, level, and description")
    if not _SHA256.fullmatch(record.record_hash):
        raise PromotionError("record_hash must be a lowercase SHA-256 digest")
    if not record.source_document_ids:
        raise PromotionError("operational records require at least one source document")
    if not record.payload:
        raise PromotionError("operational records require a public payload")


def _json_value(value: object) -> object:
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Decimal):
        return str(value)
    return value


def _parse_datetime(value: object, field: str) -> datetime:
    if not isinstance(value, str):
        raise PromotionError(f"certified manifest is missing {field}")
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError as exc:
        raise PromotionError(f"certified manifest has invalid {field}") from exc
    _require_timezone(parsed, field)
    return parsed


def _source_document_ids(value: object) -> tuple[str, ...]:
    if not isinstance(value, str):
        raise PromotionError("public record source_document_ids_json must be text")
    try:
        parsed = json.loads(value)
    except json.JSONDecodeError as exc:
        raise PromotionError("public record source_document_ids_json is invalid") from exc
    if (
        not isinstance(parsed, list)
        or not parsed
        or any(not isinstance(item, str) or not item for item in parsed)
    ):
        raise PromotionError("public record source_document_ids_json must be a nonempty string list")
    return tuple(parsed)


def load_certified_release(
    release_dir: Path,
    *,
    published_at: datetime,
    source_checked_at: datetime,
) -> tuple[OperationalRelease, list[OperationalRecord]]:
    """Load public serving rows only after the exact six-asset bundle validates."""

    release_dir = Path(release_dir).resolve()
    manifest = verify_publication_bundle(release_dir)
    dataset_version = manifest.get("dataset_version")
    schema_version = manifest.get("schema_version")
    if not isinstance(dataset_version, str) or not dataset_version:
        raise PromotionError("certified manifest is missing dataset_version")
    if not isinstance(schema_version, str) or not schema_version:
        raise PromotionError("certified manifest is missing schema_version")
    manifest_path = release_dir / "manifest.json"
    release = OperationalRelease(
        tag=f"data-{dataset_version}",
        dataset_version=dataset_version,
        schema_version=schema_version,
        manifest_sha256=hashlib.sha256(manifest_path.read_bytes()).hexdigest(),
        generated_at=_parse_datetime(manifest.get("generated_at"), "generated_at"),
        published_at=published_at,
        source_checked_at=source_checked_at,
    )
    _validate_release(release)

    database = release_dir / "arancel_mx.duckdb"
    with duckdb.connect(str(database), read_only=True) as connection:
        result = connection.execute("SELECT * FROM arancel_mx")
        columns = [item[0] for item in result.description]
        rows = result.fetchall()
    records: list[OperationalRecord] = []
    for row in rows:
        payload = {
            column: _json_value(value)
            for column, value in zip(columns, row, strict=True)
        }
        records.append(
            OperationalRecord(
                code=str(payload.get("code") or ""),
                level=str(payload.get("level") or ""),
                description=str(payload.get("description") or ""),
                record_hash=str(payload.get("record_hash") or ""),
                source_document_ids=_source_document_ids(
                    payload.get("source_document_ids_json")
                ),
                payload=payload,
            )
        )
    if not records:
        raise PromotionError("certified release has no public records")
    return release, records


def ensure_schema(connection: OperationalConnection) -> None:
    """Create the versioned serving tables and the active-release view."""

    connection.execute(_OPERATIONAL_SCHEMA)


def promote_release(
    connection: OperationalConnection,
    release: OperationalRelease,
    records: Sequence[OperationalRecord],
) -> None:
    """Atomically make one pre-certified immutable release the serving version.

    The caller must have already certified the source bundle, manifest, and DuckDB.
    This boundary validates the supplied release identity before any database work and
    switches the active pointer only after all versioned public records were inserted.
    """

    _validate_release(release)
    for record in records:
        _validate_record(record)

    with connection.transaction():
        ensure_schema(connection)
        connection.execute(
            _INSERT_RELEASE,
            (
                release.tag,
                release.dataset_version,
                release.schema_version,
                release.manifest_sha256,
                release.generated_at,
                release.published_at,
                release.source_checked_at,
            ),
        )
        for record in records:
            connection.execute(
                _INSERT_RECORD,
                (
                    release.tag,
                    record.code,
                    record.level,
                    record.description,
                    record.record_hash,
                    json.dumps(record.source_document_ids, separators=(",", ":")),
                    json.dumps(record.payload, sort_keys=True, separators=(",", ":")),
                ),
            )
        connection.execute(_SET_ACTIVE_RELEASE, (release.tag,))


__all__ = [
    "OperationalConnection",
    "OperationalRecord",
    "OperationalRelease",
    "PromotionError",
    "ensure_schema",
    "load_certified_release",
    "promote_release",
]
