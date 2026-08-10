"""Offline parsing for official LIGIE documents."""

from __future__ import annotations

from datetime import date
import hashlib
from pathlib import Path
import re
import unicodedata

import fitz
import pandas as pd

from arancel_mx.domain.normalization import canonical_json, code_level, normalize_code


def _text(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    return " ".join(str(value).split())


def _fold(value: object) -> str:
    normalized = unicodedata.normalize("NFKD", _text(value))
    return "".join(
        char for char in normalized if not unicodedata.combining(char)
    ).upper()


def _identifier(prefix: str, values: list[object]) -> str:
    digest = hashlib.sha256(canonical_json(values).encode("utf-8")).hexdigest()
    return f"{prefix}-{digest}"


def _deduplicate_by_id(rows: list[dict], id_field: str, label: str) -> list[dict]:
    unique: dict[str, dict] = {}
    for row in rows:
        row_id = row[id_field]
        previous = unique.get(row_id)
        if previous is None:
            unique[row_id] = row
        elif previous != row:
            raise ValueError(
                f"Conflicting {label} rows for {row.get('code') or row.get('nico10')}"
            )
    return list(unique.values())


def _classification_row(
    code: str,
    description: str,
    source_document_id: str,
    ligie_version: str,
    published_at: date | None,
    effective_from: date | None,
) -> dict:
    level = code_level(code)
    return {
        "classification_id": _identifier(
            "classification", [source_document_id, level, code, effective_from]
        ),
        "level": level,
        "code": code,
        "hs2": code[:2],
        "hs4": code[:4] if len(code) >= 4 else None,
        "hs6": code[:6] if len(code) >= 6 else None,
        "description": description,
        "ligie_version": ligie_version,
        "validity_basis": "legal" if effective_from else "observed_snapshot",
        "updated_at": published_at,
        "published_at": published_at,
        "classification_effective_from": effective_from,
        "classification_effective_to": None,
        "source_document_id": source_document_id,
    }


def parse_ligie_pdf_hierarchy(
    path: Path,
    source_document_id: str,
    ligie_version: str,
    published_at: date | None,
    effective_from: date | None,
) -> list[dict]:
    """Extract official HS2/HS4/HS6 labels from the consolidated LIGIE PDF."""
    rows: list[dict] = []
    page_texts: list[str] = []
    with fitz.open(path) as document:
        for page in document:
            page_text = page.get_text() or ""
            page_texts.append(page_text)
            for table in page.find_tables().tables:
                for code, description in _hierarchy_entries_from_table(table.extract()):
                    rows.append(
                        _classification_row(
                            code,
                            description,
                            source_document_id,
                            ligie_version,
                            published_at,
                            effective_from,
                        )
                    )
    for code, description in _chapter_entries_from_pages(page_texts):
        rows.append(
            _classification_row(
                code,
                description,
                source_document_id,
                ligie_version,
                published_at,
                effective_from,
            )
        )
    unique = _deduplicate_by_id(rows, "classification_id", "classification")
    rank = {"hs2": 0, "hs4": 1, "hs6": 2}
    return sorted(unique, key=lambda row: (rank[row["level"]], row["code"]))


def _chapter_entries_from_text(text: str) -> list[tuple[str, str]]:
    return _chapter_entries_from_pages([text])


def _chapter_entries_from_pages(page_texts: list[str]) -> list[tuple[str, str]]:
    entries: list[tuple[str, str]] = []
    heading = re.compile(r"Cap[ií]tulo\s+(\d{2})(?:\s+\([^)]*\))?", re.IGNORECASE)
    stop = re.compile(
        r"(?:Notas?(?:\s+de\s+subpartida)?\.?|Consideraciones|Subcap[ií]tulo|C[ÓO]DIGO|_+)",
        re.IGNORECASE,
    )
    repeated_header = re.compile(
        r"(?:LEY DE LOS IMPUESTOS GENERALES|CÁMARA DE DIPUTADOS|Secretaría General|"
        r"Secretaría de Servicios Parlamentarios|Última Reforma DOF|\d+ de \d+)",
        re.IGNORECASE,
    )
    active_code: str | None = None
    description: list[str] = []

    def flush() -> None:
        nonlocal active_code, description
        title = _text(" ".join(description))
        if active_code and title:
            entries.append((active_code, title))
        active_code = None
        description = []

    for text in page_texts:
        for candidate in (line.strip() for line in text.splitlines()):
            if not candidate or repeated_header.match(candidate):
                continue
            match = heading.fullmatch(candidate)
            if match:
                flush()
                active_code = match.group(1)
                continue
            if not active_code:
                continue
            if stop.match(candidate):
                flush()
                break
            description.append(candidate)
    flush()
    return entries


def _hierarchy_entries_from_table(table: list[list[object]]) -> list[tuple[str, str]]:
    entries: list[tuple[str, str]] = []
    pending_code: str | None = None
    pending_description: list[str] = []

    def flush() -> None:
        nonlocal pending_code, pending_description
        description = _text(" ".join(pending_description))
        if pending_code and description:
            entries.append((pending_code, description))
        pending_code = None
        pending_description = []

    for values in table:
        cells = [
            (index, _text(value))
            for index, value in enumerate(values or [])
            if _text(value)
        ]
        code_match: tuple[int, str] | None = None
        for index, cell in cells:
            try:
                candidate = normalize_code(cell)
            except ValueError:
                continue
            if len(candidate) in {4, 6, 8}:
                code_match = (index, candidate)
                break

        if code_match:
            flush()
            code_index, code = code_match
            if len(code) not in {4, 6}:
                continue
            descriptions = [
                cell
                for index, cell in cells
                if index > code_index
                and cell not in {"-", "--"}
                and _fold(cell)
                not in {"DESCRIPCION", "UNIDAD", "IMP", "IMP.", "EXP", "EXP."}
                and not re.fullmatch(
                    r"(?:\d+(?:[.,]\d+)?|EX\.?|PROHIBIDA)", _fold(cell)
                )
            ]
            pending_code = code
            if descriptions:
                pending_description.append(max(descriptions, key=len))
            continue

        if pending_code:
            cell_values = [cell for _index, cell in cells]
            if not cells or any(cell in {"-", "--"} for cell in cell_values):
                flush()
                continue
            continuations = [
                cell
                for cell in cell_values
                if not re.fullmatch(
                    r"(?:\d+(?:[.,]\d+)?|EX\.?|PROHIBIDA)", _fold(cell)
                )
            ]
            if continuations:
                pending_description.append(max(continuations, key=len))
    flush()
    return entries
