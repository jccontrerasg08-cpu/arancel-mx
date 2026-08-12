"""Deterministic, read-only queries over the public ``arancel_mx`` view."""

from __future__ import annotations

from decimal import Decimal
import re
import unicodedata
from typing import Iterable

from arancel_mx.consumer.errors import InvalidCodeError, QueryError, RecordNotFoundError
from arancel_mx.consumer.hs_sections import section_for_chapter
from arancel_mx.consumer.models import Ficha, ProvenanceRecord, SearchResult, TariffRecord


_CODE_LENGTHS = {2, 4, 6, 8, 10}
_PARENT_LENGTH = {2: None, 4: 2, 6: 4, 8: 6, 10: 8}
_CHILD_LEVEL = {
    2: "hs4",
    4: "hs6",
    6: "fraccion8",
    8: "nico10",
    10: None,
}
_ROW_SELECT = """
    SELECT code, level, description, unit_name,
           igi_text, igi_kind, igi_value,
           ige_text, ige_kind, ige_value,
           dataset_version, schema_version,
           effective_from, effective_to, is_current
    FROM arancel_mx
"""


def format_code(code: str) -> str:
    """Format a normalized 2/4/6/8/10-digit code the way TIGIE browsers display it."""

    digits = normalize_code(code)
    if len(digits) == 2:
        return digits
    if len(digits) == 4:
        return f"{digits[:2]}.{digits[2:]}"
    if len(digits) == 6:
        return f"{digits[:4]}.{digits[4:]}"
    if len(digits) == 8:
        return f"{digits[:4]}.{digits[4:6]}.{digits[6:]}"
    return f"{digits[:4]}.{digits[4:6]}.{digits[6:8]} {digits[8:]}"


def normalize_code(value: str) -> str:
    """Normalize an HS/fraction/NICO code while rejecting ambiguous characters."""

    if not isinstance(value, str):
        raise InvalidCodeError("tariff code must be a string")
    text = value.strip()
    if not text:
        raise InvalidCodeError("tariff code is required")
    if re.search(r"[^0-9.\s-]", text):
        raise InvalidCodeError(f"invalid tariff code: {value!r}")
    digits = re.sub(r"[.\s-]", "", text)
    if not digits or len(digits) not in _CODE_LENGTHS:
        raise InvalidCodeError(f"invalid tariff code length: {value!r}")
    return digits


def _as_float(value: object) -> float | None:
    if value is None:
        return None
    if isinstance(value, Decimal):
        return float(value)
    return float(value)


def _parent_code(code: str) -> str | None:
    width = _PARENT_LENGTH[len(code)]
    return None if width is None else code[:width]


def _row_to_tariff_record(row: Iterable[object]) -> TariffRecord:
    values = tuple(row)
    code = str(values[0])
    return TariffRecord(
        code=code,
        level=str(values[1]),
        description=str(values[2]),
        unit_name=None if values[3] is None else str(values[3]),
        igi_text=None if values[4] is None else str(values[4]),
        igi_kind=None if values[5] is None else str(values[5]),
        igi_value=_as_float(values[6]),
        ige_text=None if values[7] is None else str(values[7]),
        ige_kind=None if values[8] is None else str(values[8]),
        ige_value=_as_float(values[9]),
        parent_code=_parent_code(code),
        dataset_version=str(values[10]),
        schema_version=str(values[11]),
        effective_from=values[12],  # DuckDB returns datetime.date for DATE columns.
        effective_to=values[13],
        is_current=bool(values[14]),
    )


def lookup(connection, code: str) -> TariffRecord:
    """Return the exact current public record for one normalized code."""

    normalized = normalize_code(code)
    rows = connection.execute(
        _ROW_SELECT
        + " WHERE code = ? AND is_current = TRUE ORDER BY record_version DESC LIMIT 2",
        [normalized],
    ).fetchall()
    if not rows:
        raise RecordNotFoundError(f"tariff record not found: {normalized}")
    if len(rows) > 1:
        raise QueryError(f"multiple current records found for tariff code: {normalized}")
    return _row_to_tariff_record(rows[0])


def _normalize_text(value: str) -> str:
    decomposed = unicodedata.normalize("NFKD", value)
    without_marks = "".join(
        character for character in decomposed if not unicodedata.combining(character)
    )
    return " ".join(without_marks.casefold().split())


def _search_code_candidate(text: str) -> str | None:
    if re.search(r"[^0-9.\s-]", text):
        return None
    digits = re.sub(r"[.\s-]", "", text)
    if not digits or len(digits) > 10:
        return None
    return digits


def search(connection, text: str, *, limit: int) -> tuple[SearchResult, ...]:
    """Search current records with stable scoring and tie-breaking."""

    if limit <= 0:
        raise ValueError("search limit must be greater than zero")
    if not isinstance(text, str) or not text.strip():
        raise QueryError("search text must not be empty")

    normalized_text = _normalize_text(text)
    query_tokens = tuple(token for token in normalized_text.split(" ") if token)
    code_candidate = _search_code_candidate(text.strip())

    rows = connection.execute(
        _ROW_SELECT + " WHERE is_current = TRUE ORDER BY code ASC, description ASC"
    ).fetchall()
    results: list[SearchResult] = []
    for row in rows:
        record = _row_to_tariff_record(row)
        score = 0
        match_kind = None

        if code_candidate is not None and record.code == code_candidate:
            score = 1000
            match_kind = "exact_code"
        elif code_candidate is not None and record.code.startswith(code_candidate):
            score = 700
            match_kind = "code_prefix"
        else:
            description = _normalize_text(record.description)
            matched = sum(1 for token in query_tokens if token in description)
            if matched:
                score = 300 + 25 * matched
                if matched == len(query_tokens):
                    score += 5
                match_kind = "description"

        if match_kind is not None:
            results.append(
                SearchResult(record=record, score=score, match_kind=match_kind)
            )

    results.sort(
        key=lambda item: (
            -item.score,
            item.record.code,
            item.record.description,
        )
    )
    return tuple(results[:limit])


def parent(connection, code: str) -> TariffRecord | None:
    """Return the direct current parent in the HS→fraction→NICO hierarchy."""

    record = lookup(connection, code)
    if record.parent_code is None:
        return None
    return lookup(connection, record.parent_code)


def _ancestor_codes(code: str) -> tuple[str, ...]:
    return tuple(code[:width] for width in (2, 4, 6, 8, 10) if width <= len(code))


def ficha(connection, code: str) -> Ficha:
    """Return the official hierarchy card for one code (chapter → NICO)."""

    record = lookup(connection, code)
    hierarchy = tuple(lookup(connection, ancestor) for ancestor in _ancestor_codes(record.code))
    return Ficha(
        record=record,
        formatted_code=format_code(record.code),
        section=section_for_chapter(record.code[:2]),
        hierarchy=hierarchy,
        children=children(connection, record.code),
    )


def chapters(connection) -> tuple[TariffRecord, ...]:
    """Return current HS2 chapters, sorted by code."""

    rows = connection.execute(
        _ROW_SELECT + " WHERE level = 'hs2' AND is_current = TRUE ORDER BY code ASC"
    ).fetchall()
    records = tuple(_row_to_tariff_record(row) for row in rows)
    codes = [record.code for record in records]
    if len(codes) != len(set(codes)):
        raise QueryError("multiple current records found for one HS2 chapter")
    return records


def children(connection, code: str) -> tuple[TariffRecord, ...]:
    """Return only direct current children, sorted by code."""

    record = lookup(connection, code)
    child_level = _CHILD_LEVEL[len(record.code)]
    if child_level is None:
        return ()
    child_width = {"hs4": 4, "hs6": 6, "fraccion8": 8, "nico10": 10}[child_level]
    rows = connection.execute(
        _ROW_SELECT
        + " WHERE level = ? AND is_current = TRUE AND code LIKE ? "
        + "AND length(code) = ? ORDER BY code ASC, description ASC",
        [child_level, f"{record.code}%", child_width],
    ).fetchall()
    return tuple(_row_to_tariff_record(row) for row in rows)


def provenance(connection, code: str) -> tuple[ProvenanceRecord, ...]:
    """Return complete source provenance with primary source first."""

    normalized = normalize_code(code)
    # Ensure the public lookup contract is respected before provenance traversal.
    lookup(connection, normalized)
    rows = connection.execute(
        """
        SELECT d.source_document_id, p.role, p.is_primary,
               d.authority, d.publication_venue, d.title, d.source_url, d.sha256,
               d.published_at, d.effective_from, d.effective_to
        FROM canonical_record c
        JOIN record_provenance p ON p.record_id = c.record_id
        JOIN source_document d ON d.source_document_id = p.source_document_id
        WHERE c.code = ? AND c.is_current = TRUE
        ORDER BY p.is_primary DESC, d.source_document_id ASC, p.role ASC
        """,
        [normalized],
    ).fetchall()
    return tuple(
        ProvenanceRecord(
            source_document_id=str(row[0]),
            role=str(row[1]),
            is_primary=bool(row[2]),
            authority=str(row[3]),
            publication_venue=str(row[4]),
            title=str(row[5]),
            source_url=str(row[6]),
            sha256=str(row[7]),
            published_at=row[8],
            effective_from=row[9],
            effective_to=row[10],
        )
        for row in rows
    )
