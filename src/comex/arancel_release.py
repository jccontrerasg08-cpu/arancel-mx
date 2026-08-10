"""End-to-end, token-free construction of a current official arancel release."""

from __future__ import annotations

from datetime import date, datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import re
import tempfile
from typing import Any
from urllib.parse import urljoin
from zoneinfo import ZoneInfo

import requests

from .arancel_build import export_arancel_release, materialize_arancel
from .arancel_sources import (
    discover_official_documents,
    parse_ligie_workbook,
    parse_ligie_pdf_hierarchy,
    parse_nico_workbook,
)
from .db import connect, init_db
from .etl import SniceNicoSource


DIPUTADOS_LIGIE_REFERENCE_URL = "https://www.diputados.gob.mx/LeyesBiblio/ref/ligie_2022.htm"
DIPUTADOS_LIGIE_CURRENT_PDF_URL = "https://www.diputados.gob.mx/LeyesBiblio/pdf/LIGIE_2022.pdf"
MEXICO_CITY = ZoneInfo("America/Mexico_City")
HIERARCHY_PARSER_VERSION = 4


def _sha256(data: bytes) -> str:
    return hashlib.sha256(data).hexdigest()


def _source_id(url: str, digest: str) -> str:
    return hashlib.sha256(f"{url}|{digest}".encode("utf-8")).hexdigest()


def _current_documents(documents: list[dict[str, str]]) -> tuple[dict[str, str], dict[str, str]]:
    ligie = [document for document in documents if document["kind"] == "ligie"]
    nico = [
        document
        for document in documents
        if document["kind"] == "nico"
        and Path(document["source_url"].split("?", 1)[0]).name.upper().startswith("NICO-")
    ]
    if not ligie or not nico:
        raise ValueError("Discovery did not find consolidated current LIGIE and NICO workbooks")
    return sorted(ligie, key=lambda row: row["source_url"])[-1], sorted(
        nico, key=lambda row: row["source_url"]
    )[-1]


def _capture_current_sources(source_dir: Path, timeout_s: float) -> list[dict[str, Any]]:
    source_dir.mkdir(parents=True, exist_ok=True)
    capture_path = source_dir / "source_capture.json"
    captured: list[dict[str, Any]] = []
    if capture_path.exists():
        captured = json.loads(capture_path.read_text(encoding="utf-8"))
        for row in captured:
            local_path = source_dir / row["filename"]
            if not local_path.is_file() or _sha256(local_path.read_bytes()) != row["sha256"]:
                raise ValueError(f"Captured source checksum mismatch: {local_path}")

    source = SniceNicoSource()
    session = requests.Session()
    session.headers["User-Agent"] = os.getenv(
        "ARANCEL_MX_USER_AGENT", "arancel-mx/1.0 (+https://github.com/)"
    )
    if not captured:
        documents = discover_official_documents(
            session,
            source.ligie_index_url,
            source.nico_index_url,
            source.modifications_index_url,
            timeout_s,
        )
        selected = zip(("ligie.xlsx", "nico.xlsx"), _current_documents(documents), strict=True)
        for filename, document in selected:
            response = session.get(document["source_url"], timeout=timeout_s)
            response.raise_for_status()
            data = response.content
            digest = _sha256(data)
            (source_dir / filename).write_bytes(data)
            retrieved = datetime.now(timezone.utc).replace(microsecond=0)
            captured.append(
                {
                    "kind": document["kind"],
                    "filename": filename,
                    "source_document_id": _source_id(document["source_url"], digest),
                    "authority": "Secretaría de Economía",
                    "publication_venue": "SNICE",
                    "title": document["title"],
                    "source_url": document["source_url"],
                    "media_type": response.headers.get("Content-Type", "application/octet-stream").split(";", 1)[0],
                    "sha256": digest,
                    "published_at": None,
                    "effective_from": None,
                    "effective_to": None,
                    "observed_at": retrieved.astimezone(MEXICO_CITY).date().isoformat(),
                    "retrieved_at": retrieved.isoformat().replace("+00:00", "Z"),
                }
            )

    if not any(row["kind"] == "hierarchy" for row in captured):
        index_response = session.get(DIPUTADOS_LIGIE_REFERENCE_URL, timeout=timeout_s)
        index_response.raise_for_status()
        linked_urls = {
            urljoin(index_response.url, href)
            for href in re.findall(r'href=["\']([^"\']+)', index_response.text, re.IGNORECASE)
        }
        if DIPUTADOS_LIGIE_CURRENT_PDF_URL not in linked_urls:
            raise ValueError("Cámara de Diputados reference page does not link the current LIGIE PDF")
        response = session.get(DIPUTADOS_LIGIE_CURRENT_PDF_URL, timeout=timeout_s)
        response.raise_for_status()
        data = response.content
        digest = _sha256(data)
        filename = "ligie_current.pdf"
        (source_dir / filename).write_bytes(data)
        retrieved = datetime.now(timezone.utc).replace(microsecond=0)
        captured.append(
            {
                "kind": "hierarchy",
                "filename": filename,
                "source_document_id": _source_id(DIPUTADOS_LIGIE_CURRENT_PDF_URL, digest),
                "authority": "Cámara de Diputados del H. Congreso de la Unión",
                "publication_venue": "LeyesBiblio",
                "title": "Ley de los Impuestos Generales de Importación y de Exportación - texto vigente",
                "source_url": DIPUTADOS_LIGIE_CURRENT_PDF_URL,
                "reference_url": DIPUTADOS_LIGIE_REFERENCE_URL,
                "media_type": "application/pdf",
                "sha256": digest,
                "published_at": "2026-04-23",
                "effective_from": None,
                "effective_to": None,
                "observed_at": retrieved.astimezone(MEXICO_CITY).date().isoformat(),
                "retrieved_at": retrieved.isoformat().replace("+00:00", "Z"),
            }
        )

    for row in captured:
        retrieved = datetime.fromisoformat(row["retrieved_at"].replace("Z", "+00:00"))
        row["observed_at"] = retrieved.astimezone(MEXICO_CITY).date().isoformat()
    capture_path.write_text(
        json.dumps(captured, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )
    return captured


def _document_row(source_dir: Path, captured: dict[str, Any]) -> dict[str, Any]:
    return {
        **captured,
        "local_path": str((source_dir / captured["filename"]).resolve()),
        "observed_at": date.fromisoformat(captured["observed_at"]),
        "retrieved_at": datetime.fromisoformat(captured["retrieved_at"].replace("Z", "+00:00")),
    }


def _apply_observed_updates(
    documents: list[dict[str, Any]], *row_groups: list[dict[str, Any]]
) -> None:
    """Fill operational update dates without inventing publication/effective dates."""
    observed_by_source = {
        row["source_document_id"]: row["observed_at"] for row in documents
    }
    for rows in row_groups:
        for row in rows:
            if row.get("updated_at") is None:
                row["updated_at"] = observed_by_source[row["source_document_id"]]


def _cached_hierarchy(source_dir: Path, source: dict[str, Any]) -> list[dict[str, Any]]:
    cache_path = source_dir / f"hierarchy-{source['sha256'][:16]}-v{HIERARCHY_PARSER_VERSION}.json"
    if cache_path.exists():
        payload = json.loads(cache_path.read_text(encoding="utf-8"))
        if (
            payload.get("source_sha256") != source["sha256"]
            or payload.get("parser_version") != HIERARCHY_PARSER_VERSION
        ):
            raise ValueError("Hierarchy cache metadata does not match its filename")
        return payload["rows"]

    rows = parse_ligie_pdf_hierarchy(
        source_dir / source["filename"],
        source["source_document_id"],
        "LIGIE-2022",
        None,
        None,
    )
    payload = {
        "source_sha256": source["sha256"],
        "parser_version": HIERARCHY_PARSER_VERSION,
        "row_count": len(rows),
        "rows": rows,
    }
    temporary = cache_path.with_suffix(".tmp")
    temporary.write_text(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":"), default=str) + "\n",
        encoding="utf-8",
    )
    temporary.replace(cache_path)
    return rows


def build_arancel_release(
    source_dir: Path | str,
    output_dir: Path | str,
    dataset_version: str,
    effective_as_of: date | str,
    timeout_s: float | None = None,
) -> dict[str, object]:
    """Capture current official workbooks, validate a candidate, then export it."""
    source_dir = Path(source_dir).resolve()
    output_dir = Path(output_dir).resolve()
    if output_dir.exists():
        raise FileExistsError(f"Release directory already exists: {output_dir}")
    effective_date = (
        effective_as_of
        if isinstance(effective_as_of, date)
        else date.fromisoformat(effective_as_of)
    )
    timeout = timeout_s or float(os.getenv("ARANCEL_MX_HTTP_TIMEOUT", "30"))
    captured = _capture_current_sources(source_dir, timeout)
    documents = [_document_row(source_dir, row) for row in captured]
    by_kind = {row["kind"]: row for row in documents}

    classifications, rates = parse_ligie_workbook(
        source_dir / by_kind["ligie"]["filename"],
        by_kind["ligie"]["source_document_id"],
        "LIGIE-2022",
        None,
        None,
    )
    classifications.extend(_cached_hierarchy(source_dir, by_kind["hierarchy"]))
    classifications.extend(
        parse_nico_workbook(
            source_dir / by_kind["nico"]["filename"],
            by_kind["nico"]["source_document_id"],
            "LIGIE-2022",
            None,
            None,
        )
    )
    _apply_observed_updates(documents, classifications, rates)
    if not classifications or not rates:
        raise ValueError("Official workbooks produced no canonical classifications or rates")

    generated_at = datetime.now(timezone.utc).replace(microsecond=0)
    release = {
        "dataset_version": dataset_version,
        "schema_version": "1.0.0",
        "ligie_version": "LIGIE-2022",
        "effective_as_of": effective_date,
        "generated_at": generated_at,
    }
    output_dir.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.TemporaryDirectory(prefix="arancel-mx-", dir=output_dir.parent) as tmp:
        candidate = Path(tmp) / "arancel_mx.duckdb"
        init_db(candidate)
        with connect(candidate) as conn:
            summary = materialize_arancel(conn, documents, classifications, rates, release)
        manifest = export_arancel_release(candidate, output_dir)
    return {**manifest, **summary}
