"""Carry the NOM rows of the previous release when Annex 2.4.1 cannot be read (decision 0004).

The rows are never re-derived or edited: they are the previous release's own ``nom_requirement`` rows,
accepted only when they provably belong to that release (dataset version and DuckDB SHA-256 match its
manifest) and only for fractions that still exist. Anything that does not check out means "no carry".
"""

from __future__ import annotations

from collections.abc import Collection, Mapping
from datetime import date, datetime
import hashlib
import json
from pathlib import Path
from typing import Any

import duckdb

DATABASE_ASSET = "arancel_mx.duckdb"
_CARRYABLE = {"available", "carried_forward"}
_SOURCE_COLUMNS = (
    "source_document_id",
    "authority",
    "publication_venue",
    "title",
    "source_url",
    "media_type",
    "sha256",
    "local_path",
    "published_at",
    "effective_from",
    "effective_to",
    "observed_at",
    "retrieved_at",
)
_ROW_COLUMNS = (
    "fraction8",
    "numeral",
    "numeral_meaning",
    "section",
    "nom",
    "scope",
    "nico_json",
    "annex_page",
    "source_document_id",
)


_ROWS_SQL = (
    "SELECT fraction8, numeral, numeral_meaning, section, nom, scope, nico_json, annex_page, "
    "source_document_id FROM nom_requirement "
    "ORDER BY fraction8, numeral, nom, section NULLS FIRST, scope NULLS FIRST"
)
_SOURCE_SQL = (
    "SELECT source_document_id, authority, publication_venue, title, source_url, media_type, sha256, "
    "local_path, published_at, effective_from, effective_to, observed_at, retrieved_at "
    "FROM source_document WHERE source_document_id = ?"
)


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with Path(path).open("rb") as handle:
        for chunk in iter(lambda: handle.read(1 << 20), b""):
            digest.update(chunk)
    return digest.hexdigest()


def _jsonable(value: Any) -> Any:
    return value.isoformat() if isinstance(value, (date, datetime)) else value


def extract_previous_nom(database: Path, manifest: Mapping[str, object]) -> dict[str, object]:
    """Read the previous release's NOM rows after proving the file is the one its manifest describes."""
    hashes = manifest.get("artifact_sha256")
    expected = hashes.get(DATABASE_ASSET) if isinstance(hashes, Mapping) else None
    actual = file_sha256(database)
    if actual != expected:
        raise ValueError("previous database does not match the SHA-256 in its manifest")
    connection = duckdb.connect(str(database), read_only=True)
    try:
        rows = connection.execute(_ROWS_SQL).fetchall()
        source_ids = sorted({row[-1] for row in rows})
        sources = []
        for source_id in source_ids:
            row = connection.execute(_SOURCE_SQL, [source_id]).fetchone()
            if row is None:
                raise ValueError(f"previous NOM row cites an unknown source: {source_id}")
            sources.append({name: _jsonable(value) for name, value in zip(_SOURCE_COLUMNS, row)})
    finally:
        connection.close()
    return {
        "dataset_version": manifest.get("dataset_version"),
        "database_sha256": actual,
        "rows": [dict(zip(_ROW_COLUMNS, row)) for row in rows],
        "source_documents": sources,
    }


def load_previous_nom(path: Path | None) -> dict[str, object] | None:
    if path is None or not Path(path).exists():
        return None
    value = json.loads(Path(path).read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("previous NOM file must contain a JSON object")
    return value


def _as_date(value: object) -> object:
    return date.fromisoformat(str(value)) if value else None


def _source_document(raw: Mapping[str, object]) -> dict[str, object]:
    document = dict(raw)
    for field in ("published_at", "effective_from", "effective_to", "observed_at"):
        document[field] = _as_date(document.get(field))
    retrieved = str(document["retrieved_at"])
    document["retrieved_at"] = datetime.fromisoformat(retrieved)
    return document


def carry_forward(
    previous_nom: Mapping[str, object] | None,
    previous_manifest: Mapping[str, object] | None,
    fractions: Collection[str],
    reason: str,
) -> tuple[list[dict[str, object]], list[dict[str, object]], dict[str, object]] | None:
    """Rows, their source documents and release metadata for a carried annex, or None if unsafe."""
    if not previous_nom or not previous_manifest:
        return None
    previous_annex = previous_manifest.get("nom_annex")
    if not isinstance(previous_annex, Mapping) or previous_annex.get("status") not in _CARRYABLE:
        return None
    version = previous_manifest.get("dataset_version")
    hashes = previous_manifest.get("artifact_sha256")
    if (
        previous_nom.get("dataset_version") != version
        or not isinstance(hashes, Mapping)
        or previous_nom.get("database_sha256") != hashes.get(DATABASE_ASSET)
    ):
        return None
    raw_rows = previous_nom.get("rows")
    raw_sources = previous_nom.get("source_documents")
    if not isinstance(raw_rows, list) or not raw_rows or not isinstance(raw_sources, list):
        return None
    expected = previous_annex.get("rows")
    if isinstance(expected, int) and expected != len(raw_rows):
        return None

    known = set(fractions)
    rows: list[dict[str, object]] = []
    for raw in raw_rows:
        if not isinstance(raw, Mapping) or raw.get("fraction8") not in known:
            continue
        row = {key: raw.get(key) for key in _ROW_COLUMNS if key != "nico_json"}
        try:
            row["nico"] = json.loads(str(raw["nico_json"]))
        except (KeyError, ValueError):
            return None
        rows.append(row)
    if not rows:
        return None
    used = {str(row["source_document_id"]) for row in rows}
    try:
        documents = [
            _source_document(item)
            for item in raw_sources
            if isinstance(item, Mapping) and item.get("source_document_id") in used
        ]
    except (KeyError, ValueError):
        return None
    if {str(item["source_document_id"]) for item in documents} != used:
        return None

    origin = previous_annex.get("carried_from") if previous_annex.get("status") == "carried_forward" else version
    status: dict[str, object] = {
        "status": "carried_forward",
        "carried_from": origin,
        "reason": reason[:300],
        "rows": len(rows),
        "dropped_rows": len(raw_rows) - len(rows),
    }
    for key in ("records", "fractions", "requirements", "numerals", "sections", "first_page", "last_page"):
        if key in previous_annex:
            status[key] = previous_annex[key]
    status["source_document_id"] = sorted(used)[0]
    return rows, documents, status
