"""Discovery and parsing for official Mexican LIGIE and NICO documents."""

from __future__ import annotations

from datetime import date
import hashlib
from html.parser import HTMLParser
from pathlib import Path
import re
import unicodedata
from urllib.parse import urljoin, urlparse

import pandas as pd
import fitz

from .arancel_mx import canonical_json, code_level, normalize_code, parse_duty


def _text(value: object) -> str:
    if value is None or pd.isna(value):
        return ""
    return " ".join(str(value).split())


def _fold(value: object) -> str:
    normalized = unicodedata.normalize("NFKD", _text(value))
    return "".join(char for char in normalized if not unicodedata.combining(char)).upper()


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
            raise ValueError(f"Conflicting {label} rows for {row.get('code') or row.get('nico10')}")
    return list(unique.values())


def _find_columns(frame: pd.DataFrame, kind: str) -> tuple[int, dict[str, int]] | None:
    for row_index in range(min(len(frame), 80)):
        cells = [_fold(value) for value in frame.iloc[row_index].tolist()]
        next_cells = (
            [_fold(value) for value in frame.iloc[row_index + 1].tolist()]
            if row_index + 1 < len(frame)
            else [""] * len(cells)
        )
        positions: dict[str, int] = {}
        for column_index, current_cell in enumerate(cells):
            combined_cell = f"{current_cell} {next_cells[column_index]}".strip()
            if "CODIGO" in current_cell or "FRACCION ARANCELARIA" in current_cell or current_cell == "FRACCION":
                positions.setdefault("code", column_index)
            if "DESCRIPCION" in current_cell:
                positions.setdefault("description", column_index)
            if "UNIDAD" in current_cell:
                positions.setdefault("unit", column_index)
            if re.search(r"(?:^|\s)IMP\.?(?:\s|$)", combined_cell) or "IMPORTACION" in combined_cell or "IMPUESTO DE IMPORT" in combined_cell:
                positions.setdefault("igi", column_index)
            if re.search(r"(?:^|\s)EXP\.?(?:\s|$)", combined_cell) or "EXPORTACION" in combined_cell or "IMPUESTO DE EXPORT" in combined_cell:
                positions.setdefault("ige", column_index)
            if current_cell == "NICO" or "NUMERO DE IDENTIFICACION COMERCIAL" in current_cell:
                positions.setdefault("nico", column_index)
        required = {"code", "description", "nico"} if kind == "nico" else {"code", "description"}
        if required.issubset(positions) and not (kind == "ligie" and "nico" in positions):
            return row_index, positions
    return None


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
            "classification",
            [source_document_id, level, code, effective_from],
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


def parse_ligie_workbook(
    path: Path,
    source_document_id: str,
    ligie_version: str,
    published_at: date | None,
    effective_from: date | None,
) -> tuple[list[dict], list[dict]]:
    classifications: list[dict] = []
    rates: list[dict] = []
    sheets = pd.read_excel(path, sheet_name=None, header=None, dtype=object)
    for frame in sheets.values():
        header = _find_columns(frame, "ligie")
        if not header:
            continue
        header_index, columns = header
        for values in frame.iloc[header_index + 1 :].itertuples(index=False, name=None):
            try:
                code = normalize_code(values[columns["code"]])
            except (IndexError, ValueError):
                continue
            if len(code) == 10:
                continue
            description = _text(values[columns["description"]])
            if not description:
                continue
            classifications.append(
                _classification_row(
                    code,
                    description,
                    source_document_id,
                    ligie_version,
                    published_at,
                    effective_from,
                )
            )
            if len(code) != 8:
                continue
            unit_code = _text(values[columns["unit"]]) if "unit" in columns else ""
            igi_source = values[columns["igi"]] if "igi" in columns else None
            ige_source = values[columns["ige"]] if "ige" in columns else None
            igi_kind, igi_value, igi_text = parse_duty(igi_source)
            ige_kind, ige_value, ige_text = parse_duty(ige_source)
            if not any((unit_code, igi_text, ige_text)):
                continue
            rates.append(
                {
                    "rate_revision_id": _identifier(
                        "rate",
                        [source_document_id, code, effective_from, unit_code, igi_text, ige_text],
                    ),
                    "code": code,
                    "unit_code": unit_code or None,
                    "unit_name": None,
                    "igi_text": igi_text,
                    "igi_kind": igi_kind,
                    "igi_value": igi_value,
                    "ige_text": ige_text,
                    "ige_kind": ige_kind,
                    "ige_value": ige_value,
                    "ligie_version": ligie_version,
                    "updated_at": published_at,
                    "published_at": published_at,
                    "rate_effective_from": effective_from,
                    "rate_effective_to": None,
                    "source_document_id": source_document_id,
                }
            )
    return (
        _deduplicate_by_id(classifications, "classification_id", "classification"),
        _deduplicate_by_id(rates, "rate_revision_id", "rate"),
    )


def parse_nico_workbook(
    path: Path,
    source_document_id: str,
    ligie_version: str,
    published_at: date | None,
    effective_from: date | None,
) -> list[dict]:
    rows: list[dict] = []
    sheets = pd.read_excel(path, sheet_name=None, header=None, dtype=object)
    for frame in sheets.values():
        header = _find_columns(frame, "nico")
        if not header:
            continue
        header_index, columns = header
        for values in frame.iloc[header_index + 1 :].itertuples(index=False, name=None):
            try:
                fraccion8 = normalize_code(values[columns["code"]])
                nico2 = normalize_code(values[columns["nico"]], component_width=2)
            except (IndexError, ValueError):
                continue
            if len(fraccion8) != 8:
                continue
            description = _text(values[columns["description"]])
            if not description:
                continue
            nico10 = f"{fraccion8}{nico2}"
            rows.append(
                {
                    "nico_revision_id": _identifier(
                        "nico",
                        [source_document_id, nico10, effective_from],
                    ),
                    "level": "nico10",
                    "code": nico10,
                    "nico10": nico10,
                    "fraccion8": fraccion8,
                    "nico2": nico2,
                    "description": description,
                    "ligie_version": ligie_version,
                    "validity_basis": "legal" if effective_from else "observed_snapshot",
                    "updated_at": published_at,
                    "published_at": published_at,
                    "classification_effective_from": effective_from,
                    "classification_effective_to": None,
                    "source_document_id": source_document_id,
                }
            )
    return _deduplicate_by_id(rows, "nico_revision_id", "NICO")


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
                            code, description, source_document_id, ligie_version,
                            published_at, effective_from,
                        )
                    )
    for code, description in _chapter_entries_from_pages(page_texts):
        rows.append(
            _classification_row(
                code, description, source_document_id, ligie_version,
                published_at, effective_from,
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
        cells = [(index, _text(value)) for index, value in enumerate(values or []) if _text(value)]
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
                and _fold(cell) not in {"DESCRIPCION", "UNIDAD", "IMP", "IMP.", "EXP", "EXP."}
                and not re.fullmatch(r"(?:\d+(?:[.,]\d+)?|EX\.?|PROHIBIDA)", _fold(cell))
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
                if not re.fullmatch(r"(?:\d+(?:[.,]\d+)?|EX\.?|PROHIBIDA)", _fold(cell))
            ]
            if continuations:
                pending_description.append(max(continuations, key=len))
    flush()
    return entries


class _LinkParser(HTMLParser):
    def __init__(self):
        super().__init__()
        self.links: list[tuple[str, str]] = []
        self._href: str | None = None
        self._text: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        self._href = next((value for name, value in attrs if name.lower() == "href"), None)
        self._text = []

    def handle_data(self, data: str) -> None:
        if self._href is not None:
            self._text.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag.lower() == "a" and self._href:
            self.links.append((self._href, _text(" ".join(self._text))))
            self._href = None
            self._text = []


def _official_host(url: str) -> bool:
    host = (urlparse(url).hostname or "").lower()
    return host == "snice.gob.mx" or host.endswith(".snice.gob.mx") or host == "dof.gob.mx" or host.endswith(".dof.gob.mx")


def _document_links(html: str, base_url: str, context: str) -> list[dict]:
    parser = _LinkParser()
    parser.feed(html)
    documents: list[dict] = []
    for href, title in parser.links:
        url = urljoin(base_url, href)
        if not _official_host(url):
            continue
        searchable = _fold(f"{title} {url}")
        suffix = Path(urlparse(url).path).suffix.lower()
        if suffix in {".xls", ".xlsx"} and "NICO" in searchable:
            kind = "nico"
        elif context == "ligie" and (
            suffix in {".xls", ".xlsx"}
            and re.search(r"LIGIE|TIGIE|FRACCIONESARANCELARIAS", searchable)
            and not re.search(
                r"ARANCEL.CUPO|NIVELESARANCELARIOS|TABLASDECORRELACION|DECRETO|IMMEX|PROSEC|FRONTERA|CHETUMAL|VEHICULOSUSADOS",
                searchable,
            )
        ):
            kind = "ligie"
        elif context == "modification" and (
            suffix in {".xls", ".xlsx"}
            or suffix == ".pdf"
            or "DOF.GOB.MX" in searchable
        ):
            kind = "modification"
        else:
            continue
        documents.append({"kind": kind, "title": title or Path(url).name, "source_url": url})
    return documents


def _year_pages(html: str, base_url: str, context: str) -> list[str]:
    parser = _LinkParser()
    parser.feed(html)
    if context == "nico":
        pattern = re.compile(r"ligie\.nico\d+\.mod(\d{2})\.html$", re.I)
        minimum_year = 22
    elif context == "modification":
        pattern = re.compile(r"ligie\.info\d+\.mod(\d{2})\.html$", re.I)
        minimum_year = 23
    else:
        return []
    pages: set[str] = set()
    for href, _title in parser.links:
        url = urljoin(base_url, href)
        match = pattern.search(urlparse(url).path)
        if _official_host(url) and match and int(match.group(1)) >= minimum_year:
            pages.add(url)
    return sorted(pages)


def discover_official_documents(
    client,
    ligie_index_url: str,
    nico_index_url: str,
    modifications_index_url: str,
    timeout_s: float = 30.0,
) -> list[dict]:
    documents: list[dict] = []
    seen: set[str] = set()
    for kind, index_url in (
        ("ligie", ligie_index_url),
        ("nico", nico_index_url),
        ("modification", modifications_index_url),
    ):
        response = client.get(index_url, timeout=timeout_s)
        response.raise_for_status()
        page_documents = _document_links(response.text, response.url, kind)
        for year_url in _year_pages(response.text, response.url, kind):
            year_response = client.get(year_url, timeout=timeout_s)
            year_response.raise_for_status()
            page_documents.extend(
                _document_links(year_response.text, year_response.url, kind)
            )
        for document in page_documents:
            if document["source_url"] in seen:
                continue
            seen.add(document["source_url"])
            documents.append(document)
    missing = {"ligie", "nico", "modification"} - {
        document["kind"] for document in documents
    }
    if missing:
        raise ValueError(
            "Official discovery did not find: " + ", ".join(sorted(missing))
        )
    return documents
