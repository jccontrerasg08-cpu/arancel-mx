"""Extract tariff rows from DOF decrees that modify the LIGIE Tarifa.

Decrees publish their changes as a table with the columns CÓDIGO, DESCRIPCIÓN,
UNIDAD and the import and export duties. Some tables add a column of hierarchy
dashes or empty spacer cells, so columns are located from each table's header.
Only rows with an eight-digit tariff fraction are returned; headings,
subheadings, notes and annex tables without a description are skipped. A row
that a page break splits keeps the text of both halves.
"""

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
import re

import pymupdf

_FRACTION = re.compile(r"^(\d{4})\.(\d{2})\.(\d{2})$")
# Chapter, heading or subheading codes (01, 01.01, 0101.21): rows without rates.
_HEADING = re.compile(r"^\d{2}(?:\.\d{2})?$|^\d{4}\.\d{2}$")
_DASHES = re.compile(r"^[-–—\s]*$")


@dataclass(frozen=True)
class DecreeRow:
    code: str
    description: str
    unit: str | None
    igi: str | None
    ige: str | None


@dataclass(frozen=True)
class _Columns:
    code: int
    description: int
    unit: int


def _clean(value: object) -> str:
    return " ".join(str(value or "").split())


def _fraction_code(value: object) -> str | None:
    match = _FRACTION.fullmatch(_clean(value).replace(" ", ""))
    return "".join(match.groups()) if match else None


def _is_header(row: list[object]) -> bool:
    return any(_clean(cell).casefold().startswith(("código", "codigo")) for cell in row)


def _header_columns(row: list[object]) -> _Columns | None:
    """Locate the columns of a Tarifa table; other tables (annexes) return None."""
    folded = [_clean(cell).casefold() for cell in row]
    if not any(cell.startswith(("cuota", "impuesto")) for cell in folded):
        return None
    try:
        code = next(
            i for i, cell in enumerate(folded) if cell.startswith(("código", "codigo"))
        )
        description = next(
            i
            for i, cell in enumerate(folded)
            if cell.startswith(("descripción", "descripcion"))
        )
        unit = next(i for i, cell in enumerate(folded) if cell.startswith("unidad"))
    except StopIteration:
        return None
    return _Columns(code, description, unit)


def _row(
    raw: list[object], columns: _Columns
) -> tuple[str | None, bool, str, str | None, str | None, str | None]:
    # The code sits in the CÓDIGO column or, in some layouts, one cell to its right.
    code_cells = [
        _clean(cell).replace(" ", "")
        for cell in raw[columns.code : columns.description]
    ]
    code = next((c for c in map(_fraction_code, code_cells) if c), None)
    marker_cells = [_clean(cell) for cell in raw[columns.code : columns.unit]]
    # Uncoded subheadings carry hierarchy dashes ("-", "--") and section titles
    # (SUBCAPÍTULO ...) are in capitals; neither continues the previous fraction.
    has_dashes = any(cell and _DASHES.fullmatch(cell) for cell in marker_cells)
    is_title = any(
        cell.startswith(("SUBCAPÍTULO", "CAPÍTULO", "SECCIÓN")) for cell in marker_cells
    )
    is_heading = code is None and (
        has_dashes
        or is_title
        or any(_HEADING.fullmatch(cell) for cell in code_cells if cell)
    )
    description = " ".join(
        _clean(cell)
        for cell in raw[columns.code + 1 : columns.unit]
        if _clean(cell)
        and not _DASHES.fullmatch(_clean(cell))
        and not _fraction_code(cell)
        and not _HEADING.fullmatch(_clean(cell).replace(" ", ""))
    )
    # Unit and duties are the non-empty cells from the UNIDAD column on. Some
    # layouts pad them with spacer cells or shift the unit one cell right.
    values = [_clean(cell) for cell in raw[columns.unit :] if _clean(cell)]
    unit: str | None
    igi: str | None
    ige: str | None
    if len(values) >= 3:
        unit, igi, ige = values[0], values[1], values[2]
    elif len(values) == 2:
        unit, igi, ige = None, values[0], values[1]
    else:
        unit, igi, ige = None, (values[0] if values else None), None
    return code, is_heading, description, unit, igi, ige


def parse_decree_rows(path: Path) -> list[DecreeRow]:
    """Return the fraction rows of every Tarifa table in the decree, in order."""
    rows: list[DecreeRow] = []
    columns: _Columns | None = None
    # Continuation lines belong to the last coded row, which may be a heading.
    last_was_fraction = False
    with pymupdf.open(path) as document:
        for page in document:
            for table in page.find_tables().tables:
                for raw in table.extract():
                    if _is_header(raw):
                        # A table that is not a Tarifa table (an annex) resets the
                        # columns, so its rows are skipped.
                        columns = _header_columns(raw)
                        continue
                    if columns is None or len(raw) <= columns.unit:
                        continue
                    code, is_heading, description, unit, igi, ige = _row(raw, columns)
                    if is_heading:
                        last_was_fraction = False
                        continue
                    if code is None:
                        # A wrapped line or page break split the previous row.
                        if rows and last_was_fraction and description and not igi:
                            last = rows[-1]
                            rows[-1] = DecreeRow(
                                last.code,
                                f"{last.description} {description}",
                                last.unit,
                                last.igi,
                                last.ige,
                            )
                        continue
                    last_was_fraction = bool(description)
                    if not description:
                        continue
                    rows.append(DecreeRow(code, description, unit, igi, ige))
    return rows
