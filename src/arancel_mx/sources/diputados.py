"""Parse and compare the Cámara de Diputados LIGIE legal ledger."""

from __future__ import annotations

import hashlib
import re
import unicodedata
from dataclasses import dataclass
from datetime import date
from html.parser import HTMLParser
from pathlib import PurePosixPath
from urllib.parse import urljoin, urlparse


@dataclass(frozen=True)
class LedgerLink:
    role: str
    url: str
    label: str
    displayed_date: date | None = None
    media_type: str | None = None
    content_sha256: str | None = None


@dataclass(frozen=True)
class LedgerDocument:
    category: str
    ordinal: str
    title: str
    displayed_date: date | None
    links: tuple[LedgerLink, ...]


@dataclass(frozen=True)
class LedgerSnapshot:
    base_url: str
    last_law_reform: date
    latest_tariff_modification: date
    documents: tuple[LedgerDocument, ...]
    page_sha256: str


@dataclass(frozen=True)
class LegalChange:
    event_type: str
    detail: str


class _LedgerParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.all_text: list[str] = []
        self.rows: list[tuple[list[str], list[tuple[str, str]]]] = []
        self.loose_links: list[tuple[str, str]] = []
        self._row_cells: list[str] | None = None
        self._row_links: list[tuple[str, str]] | None = None
        self._cell_parts: list[str] | None = None
        self._link_href: str | None = None
        self._link_parts: list[str] | None = None

    def handle_starttag(self, tag: str, attrs) -> None:
        attrs_map = dict(attrs)
        if tag == "tr":
            self._row_cells, self._row_links = [], []
        elif tag in {"th", "td"} and self._row_cells is not None:
            self._cell_parts = []
        elif tag == "a":
            self._link_href = attrs_map.get("href")
            self._link_parts = []

    def handle_data(self, data: str) -> None:
        text = " ".join(data.split())
        if not text:
            return
        self.all_text.append(text)
        if self._cell_parts is not None:
            self._cell_parts.append(text)
        if self._link_parts is not None:
            self._link_parts.append(text)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._link_parts is not None:
            link = (self._link_href or "", " ".join(self._link_parts).strip())
            if self._row_links is not None:
                self._row_links.append(link)
            else:
                self.loose_links.append(link)
            self._link_href = None
            self._link_parts = None
        elif tag in {"th", "td"} and self._cell_parts is not None:
            if self._row_cells is None:
                raise ValueError("Diputados ledger parser closed a cell outside a row")
            self._row_cells.append(" ".join(self._cell_parts).strip())
            self._cell_parts = None
        elif tag == "tr" and self._row_cells is not None:
            self.rows.append((self._row_cells, self._row_links or []))
            self._row_cells = None
            self._row_links = None


_MONTHS = {
    "enero": 1,
    "febrero": 2,
    "marzo": 3,
    "abril": 4,
    "mayo": 5,
    "junio": 6,
    "julio": 7,
    "agosto": 8,
    "septiembre": 9,
    "octubre": 10,
    "noviembre": 11,
    "diciembre": 12,
}

_CORE_LEGAL_LINK_PATTERNS = (
    ("original", re.compile(r"^ligie_2022_orig(?:_|$)", re.IGNORECASE)),
    ("law_reform", re.compile(r"^ligie_2022_ref\d+(?:_|$)", re.IGNORECASE)),
    ("tariff_decree", re.compile(r"^ligie_2022_tarifa\d+(?:_|$)", re.IGNORECASE)),
)


def _fold(value: str) -> str:
    normalized = unicodedata.normalize("NFKD", value)
    return "".join(ch for ch in normalized if not unicodedata.combining(ch)).lower()


def _numeric_date(text: str) -> date | None:
    match = re.search(r"\b(\d{1,2})[-/](\d{1,2})[-/](\d{4})\b", text)
    return date(int(match.group(3)), int(match.group(2)), int(match.group(1))) if match else None


def _named_date(text: str) -> date | None:
    match = re.search(
        r"\b(\d{1,2})\s+de\s+([A-Za-zÁÉÍÓÚáéíóúñÑ]+)\s+de\s+(\d{4})\b",
        text,
    )
    if not match:
        return None
    month = _MONTHS.get(_fold(match.group(2)))
    return date(int(match.group(3)), month, int(match.group(1))) if month else None


def _link_role(label: str, url: str) -> tuple[str, str | None]:
    folded = _fold(label)
    suffix = PurePosixPath(urlparse(url).path).suffix.lower()
    if "dof" in folded:
        return "dof", "application/pdf"
    if "word" in folded or suffix == ".doc":
        return "word", "application/msword"
    if suffix == ".pdf":
        return "pdf", "application/pdf"
    return "document", None


def _category_for(section: str, title: str) -> str:
    if section != "complementary":
        return section
    folded = _fold(title)
    if "nota" in folded and "nacional" in folded:
        return "national_notes"
    if "nico" in folded or "identificacion comercial" in folded:
        return "nico_agreement"
    if "correlacion" in folded:
        return "correlation"
    return "unknown"


def _core_legal_category_from_links(raw_links: list[tuple[str, str]]) -> str | None:
    categories: set[str] = set()
    for href, _label in raw_links:
        filename = PurePosixPath(urlparse(href).path).name
        for category, pattern in _CORE_LEGAL_LINK_PATTERNS:
            if pattern.match(filename):
                categories.add(category)
    if len(categories) > 1:
        raise ValueError("ambiguous Diputados legal row link families")
    return next(iter(categories)) if categories else None


def parse_ligie_ledger(html: str, base_url: str) -> LedgerSnapshot:
    parser = _LedgerParser()
    parser.feed(html)
    full_text = " ".join(parser.all_text)
    folded_full = _fold(full_text)

    law_match = re.search(
        r"ultima reforma publicada.*?(\d{1,2}\s+de\s+[a-z]+\s+de\s+\d{4})",
        folded_full,
    )
    tariff_match = re.search(
        r"fracciones arancelarias.*?decreto dof\s+(\d{1,2}[-/]\d{1,2}[-/]\d{4})",
        folded_full,
    )
    last_law_reform = _named_date(law_match.group(1)) if law_match else None
    latest_tariff = _numeric_date(tariff_match.group(1)) if tariff_match else None
    if not last_law_reform or not latest_tariff:
        raise ValueError("Diputados LIGIE ledger is missing its law or tariff date")

    documents: list[LedgerDocument] = []
    for href, label in parser.loose_links:
        absolute = urljoin(base_url, href)
        if "texto vigente" in _fold(label) or urlparse(absolute).path.lower().endswith(
            "/pdf/ligie_2022.pdf"
        ):
            role, media_type = _link_role(label, absolute)
            documents.append(
                LedgerDocument(
                    "consolidated_text",
                    "current",
                    "Texto vigente LIGIE 2022",
                    last_law_reform,
                    (LedgerLink(role, absolute, label or "Texto vigente", None, media_type),),
                )
            )

    section = "unknown"
    for cells, raw_links in parser.rows:
        row_text = " ".join(cells).strip()
        folded = _fold(row_text)
        if "publicacion original" in folded:
            section = "original"
            continue
        if "decretos de reforma" in folded:
            section = "law_reform"
            continue
        if "decretos que modifican" in folded and "tarifa" in folded:
            section = "tariff_decree"
            continue
        if "acuerdos complementarios" in folded:
            section = "complementary"
            continue
        if not raw_links or not row_text:
            continue
        title = cells[1] if len(cells) > 1 else row_text
        category = _core_legal_category_from_links(raw_links) or _category_for(section, title)
        displayed_date = _numeric_date(row_text)
        links: list[LedgerLink] = []
        for href, label in raw_links:
            absolute = urljoin(base_url, href)
            role, media_type = _link_role(label, absolute)
            links.append(
                LedgerLink(role, absolute, label, _numeric_date(label), media_type)
            )
        documents.append(
            LedgerDocument(
                category,
                cells[0].strip() if cells else "",
                title,
                displayed_date,
                tuple(links),
            )
        )
    if not documents:
        raise ValueError("Diputados LIGIE ledger contains no recognized documents")
    return LedgerSnapshot(
        base_url=base_url,
        last_law_reform=last_law_reform,
        latest_tariff_modification=latest_tariff,
        documents=tuple(documents),
        page_sha256=hashlib.sha256(html.encode("utf-8")).hexdigest(),
    )


_EVENT_BY_CATEGORY = {
    "consolidated_text": "consolidated_text_changed",
    "original": "ligie_original_changed",
    "law_reform": "ligie_reform_changed",
    "tariff_decree": "tariff_decree_changed",
    "nico_agreement": "nico_agreement_changed",
    "national_notes": "national_notes_changed",
    "correlation": "correlation_changed",
    "unknown": "unknown_legal_change",
}


def _document_key(document: LedgerDocument) -> tuple[str, str, str]:
    return document.category, document.ordinal, " ".join(document.title.split())


def diff_ledgers(
    previous: LedgerSnapshot | None,
    current: LedgerSnapshot,
) -> tuple[LegalChange, ...]:
    before = {_document_key(document): document for document in previous.documents} if previous else {}
    after = {_document_key(document): document for document in current.documents}
    changes: list[LegalChange] = []
    for key in sorted(set(before) | set(after)):
        if before.get(key) == after.get(key):
            continue
        document = after.get(key) or before[key]
        changes.append(
            LegalChange(
                _EVENT_BY_CATEGORY.get(document.category, "unknown_legal_change"),
                f"{document.category}:{document.ordinal}:{document.title}",
            )
        )
    if previous and previous.last_law_reform != current.last_law_reform and not any(
        change.event_type == "ligie_reform_changed" for change in changes
    ):
        changes.append(LegalChange("ligie_reform_changed", "displayed law reform date"))
    if previous and previous.latest_tariff_modification != current.latest_tariff_modification and not any(
        change.event_type == "tariff_decree_changed" for change in changes
    ):
        changes.append(LegalChange("tariff_decree_changed", "displayed tariff modification date"))
    return tuple(changes)


_JOBS_BY_EVENT = {
    "ligie_original_changed": ("diputados_capture", "dof_verification", "ligie_discovery", "canonical_rebuild"),
    "ligie_reform_changed": ("diputados_capture", "dof_verification", "legal_timeline", "canonical_rebuild"),
    "tariff_decree_changed": ("diputados_capture", "dof_verification", "snice_tariff_discovery", "rate_timeline", "canonical_rebuild"),
    "nico_agreement_changed": ("diputados_capture", "dof_verification", "snice_nico_discovery", "nico_timeline", "canonical_rebuild"),
    "national_notes_changed": ("diputados_capture", "dof_verification", "national_notes", "canonical_rebuild"),
    "correlation_changed": ("diputados_capture", "dof_verification", "correlations", "canonical_rebuild"),
    "consolidated_text_changed": ("diputados_capture", "dof_verification", "full_legal_reconciliation", "canonical_rebuild"),
}


def route_changes(changes: tuple[LegalChange, ...]) -> tuple[str, ...]:
    jobs: list[str] = []
    for change in changes:
        if change.event_type not in _JOBS_BY_EVENT:
            raise ValueError(f"unknown_legal_change: {change.detail}")
        for job in _JOBS_BY_EVENT[change.event_type]:
            if job not in jobs:
                jobs.append(job)
    return tuple(jobs)
