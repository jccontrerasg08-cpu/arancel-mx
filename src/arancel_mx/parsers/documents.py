"""Offline parsing for official LIGIE documents."""

from __future__ import annotations

from datetime import date
from html import unescape
import hashlib
from pathlib import Path
import re

import pymupdf

from arancel_mx.domain.normalization import canonical_json, code_level, fold_text, normalize_code


def _text(value: object) -> str:
    if value is None:
        return ""
    return " ".join(str(value).split())


def _fold(value: object) -> str:
    return fold_text(value).upper()


_CHAPTER_HEADING = re.compile(r"Cap[ií]tulo\s+(\d{1,2})(?![.\d])", re.IGNORECASE)
_SECTION_HEADING = re.compile(r"Secci[oó]n\s+([IVXLCDM]+)\b", re.IGNORECASE)
_NOTE_START = re.compile(r"(?m)^\s*(\d+)\.\s+")
_SCOPE_BOUNDARY = re.compile(
    r"(?m)(?=^[ \t]*(?:Cap[ií]tulo\s+\d{1,2}(?![.\d])|Secci[oó]n\s+[IVXLCDM]+\b|"
    r"Art[ií]culo\s+|TRANSITORIOS\b))",
    re.IGNORECASE,
)
_SECTION_CHAPTER_RANGES = {
    "I": ("01", "05"),
    "II": ("06", "14"),
    "III": ("15", "15"),
    "IV": ("16", "24"),
    "V": ("25", "27"),
    "VI": ("28", "38"),
    "VII": ("39", "40"),
    "VIII": ("41", "43"),
    "IX": ("44", "46"),
    "X": ("47", "49"),
    "XI": ("50", "63"),
    "XII": ("64", "67"),
    "XIII": ("68", "70"),
    "XIV": ("71", "71"),
    "XV": ("72", "83"),
    "XVI": ("84", "85"),
    "XVII": ("86", "89"),
    "XVIII": ("90", "92"),
    "XIX": ("93", "93"),
    "XX": ("94", "96"),
    "XXI": ("97", "97"),
}


def _section_chapters(roman: str) -> tuple[str, ...]:
    """Return the LIGIE chapters to which a section-level note applies."""
    start, end = _SECTION_CHAPTER_RANGES[roman]
    return tuple(f"{number:02d}" for number in range(int(start), int(end) + 1))


def parse_national_notes_html(html: str, source_document_id: str) -> list[dict]:
    """Extract numbered LIGIE national notes from SNICE or official DOF HTML.

    National notes published at section level apply to every chapter in the
    corresponding Harmonized System section. They are materialized once per
    applicable chapter so the consumer's chapter lookup remains complete.
    """
    if not source_document_id:
        raise ValueError("source_document_id is required")
    stripped = re.sub(r"(?is)<(script|style).*?</\1>", " ", html)
    stripped = re.sub(r"(?i)<br\s*/?>", "\n", stripped)
    stripped = re.sub(r"(?i)</(p|div|h[1-6]|li|tr)>", "\n", stripped)
    text = unescape(re.sub(r"<[^>]+>", " ", stripped))
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{2,}", "\n", text)
    rows: list[dict] = []
    for block in _SCOPE_BOUNDARY.split(text):
        chapters: tuple[str, ...]
        chapter_heading = _CHAPTER_HEADING.search(block)
        section_heading = _SECTION_HEADING.search(block)
        if chapter_heading:
            chapters = (chapter_heading.group(1).zfill(2),)
            scope_type = "chapter"
            scope_value = chapters[0]
        elif section_heading:
            scope_type = "section"
            scope_value = section_heading.group(1).upper()
            chapters = _section_chapters(scope_value)
        else:
            continue
        starts = list(_NOTE_START.finditer(block))
        for index, match in enumerate(starts):
            end = starts[index + 1].start() if index + 1 < len(starts) else len(block)
            body = " ".join(block[match.end() : end].split())
            if not body:
                raise ValueError("national note is missing text")
            for chapter in chapters:
                rows.append(
                    {
                        "chapter": chapter,
                        "scope_type": scope_type,
                        "scope_value": scope_value,
                        "note_number": match.group(1),
                        "text": body,
                        "source_document_id": source_document_id,
                    }
                )
    if not rows:
        raise ValueError("national notes HTML contains no numbered notes")
    return rows


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
    pending_code: str | None = None
    pending_description: list[str] = []
    with pymupdf.open(path) as document:
        for page in document:
            page_text = page.get_text() or ""
            page_texts.append(page_text)
            for table in page.find_tables().tables:
                extracted, pending_code, pending_description = _hierarchy_entries_from_table(
                    table.extract(),
                    pending_code=pending_code,
                    pending_description=pending_description,
                )
                for code, description in extracted:
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
    leftover = _text(" ".join(pending_description))
    if pending_code and leftover:
        rows.append(
            _classification_row(
                pending_code,
                leftover,
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


def _hierarchy_entries_from_table(
    table: list[list[object]],
    *,
    pending_code: str | None = None,
    pending_description: list[str] | None = None,
) -> tuple[list[tuple[str, str]], str | None, list[str]]:
    """Extract HS4/HS6 labels, carrying an unfinished heading across tables/pages.

    Official LIGIE PDFs split long partida text at page boundaries. The next page
    often starts with the remainder (for example ``molido.``) before a dash
    grouping row. Empty padding rows must not flush that pending heading.
    """

    entries: list[tuple[str, str]] = []
    pending_description = list(pending_description or [])

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
            if not cells:
                continue
            if any(cell in {"-", "--"} for cell in cell_values):
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
    if pending_code and not pending_description:
        pending_code = None
    return entries, pending_code, pending_description
