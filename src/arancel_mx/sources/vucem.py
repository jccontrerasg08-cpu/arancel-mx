"""Catalog and parsing helpers for VUCEM tariff classifier HTML pages."""

from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser
import re
from urllib.parse import urlparse


VUCEM_CLASSIFIER_INDEX_URL = "https://www.ventanillaunica.gob.mx/vucem/Clasificador.html"
VUCEM_FRACTION_SHEET_URL_TEMPLATE = (
    "https://www.ventanillaunica.gob.mx/Clasificador/data/buildHojas1/{code}.html"
)
VUCEM_SAMPLE_FRACTION_CODE = "90014002"


def fraction_sheet_url(code: str) -> str:
    """Return the official VUCEM HTML sheet URL for one 8-digit tariff fraction."""
    normalized = re.sub(r"\D", "", code)
    if not re.fullmatch(r"\d{8}", normalized):
        raise ValueError(f"VUCEM fraction code must contain 8 digits: {code!r}")
    return VUCEM_FRACTION_SHEET_URL_TEMPLATE.format(code=normalized)


VUCEM_SAMPLE_FRACTION_SHEET_URL = fraction_sheet_url(VUCEM_SAMPLE_FRACTION_CODE)


@dataclass(frozen=True)
class VucemFractionSheet:
    code: str
    description: str
    import_duty: str | None
    export_duty: str | None
    nico_rows: tuple[tuple[str, str, str | None, str | None], ...]


class _TableParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.tables: list[list[list[str]]] = []
        self._table: list[list[str]] | None = None
        self._row: list[str] | None = None
        self._cell_parts: list[str] | None = None

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag == "table":
            self._table = []
        elif tag == "tr" and self._table is not None:
            self._row = []
        elif tag in {"td", "th"} and self._row is not None:
            self._cell_parts = []

    def handle_data(self, data: str) -> None:
        if self._cell_parts is not None:
            self._cell_parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag in {"td", "th"} and self._row is not None and self._cell_parts is not None:
            self._row.append(" ".join(self._cell_parts).strip())
            self._cell_parts = None
        elif tag == "tr" and self._table is not None and self._row is not None:
            if any(cell.strip() for cell in self._row):
                self._table.append(self._row)
            self._row = None
        elif tag == "table" and self._table is not None:
            if self._table:
                self.tables.append(self._table)
            self._table = None


def _code_from_url(base_url: str) -> str:
    stem = urlparse(base_url).path.rsplit("/", 1)[-1]
    match = re.search(r"(\d{8})", stem)
    if not match:
        raise ValueError(f"VUCEM fraction sheet URL is missing an 8-digit code: {base_url}")
    return match.group(1)


def _normalize_code(value: str) -> str:
    return re.sub(r"\D", "", value)


def _find_fraction_row(
    tables: list[list[list[str]]],
    *,
    code: str,
) -> tuple[str, str | None, str | None] | None:
    for table in tables:
        for row in table:
            if not row:
                continue
            joined = " ".join(row)
            if _normalize_code(joined).startswith(code):
                description = row[1] if len(row) > 1 else joined
                import_duty = row[2] if len(row) > 2 else None
                export_duty = row[3] if len(row) > 3 else None
                return description, import_duty, export_duty
    return None


def _nico_rows(tables: list[list[list[str]]]) -> tuple[tuple[str, str, str | None, str | None], ...]:
    rows: list[tuple[str, str, str | None, str | None]] = []
    for table in tables:
        header = " ".join(table[0]).casefold() if table else ""
        if "nico" not in header:
            continue
        for row in table[1:]:
            if len(row) < 2:
                continue
            rows.append(
                (
                    row[0],
                    row[1],
                    row[2] if len(row) > 2 else None,
                    row[3] if len(row) > 3 else None,
                )
            )
    return tuple(rows)


def parse_fraction_sheet(html: str, *, base_url: str) -> VucemFractionSheet:
    """Parse one VUCEM buildHojas fraction sheet into structured tariff fields."""
    code = _code_from_url(base_url)
    if _normalize_code(html).find(code) == -1:
        raise ValueError(f"VUCEM fraction sheet HTML is missing code {code}")

    parser = _TableParser()
    parser.feed(html)
    fraction = _find_fraction_row(parser.tables, code=code)
    if fraction is None:
        raise ValueError(f"VUCEM fraction sheet HTML is missing a tariff row for {code}")
    description, import_duty, export_duty = fraction
    return VucemFractionSheet(
        code=code,
        description=description,
        import_duty=import_duty,
        export_duty=export_duty,
        nico_rows=_nico_rows(parser.tables),
    )


normalize_fraction_code = _normalize_code
TableParser = _TableParser
