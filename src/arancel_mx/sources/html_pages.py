"""Catalog and validation helpers for official LIGIE HTML pages."""

from __future__ import annotations

from dataclasses import dataclass
from html.parser import HTMLParser
import re
import unicodedata
from urllib.parse import urljoin, urlparse

from arancel_mx.pipeline.reconcile import discover_registered_sources
from arancel_mx.sources.diputados import parse_ligie_ledger
from arancel_mx.sources.registry import RegistryEntry, load_source_registry


DIPUTADOS_LEDGER_URL = "https://www.diputados.gob.mx/LeyesBiblio/ref/ligie_2022.htm"
SNICE_LIGIE_INDEX_URL = "https://www.snice.gob.mx/cs/avi/snice/ligie.info22.html"
SNICE_NICO_INDEX_URL = "https://www.snice.gob.mx/cs/avi/snice/ligie.nico2022.html"
SNICE_MODIFICATIONS_INDEX_URL = (
    "https://www.snice.gob.mx/cs/avi/snice/ligie.info22.mod.html"
)
SNICE_BIBLIOTECA_JURIDICA_URL = (
    "https://www.snice.gob.mx/cs/avi/snice/ligie.info22.ligiebibjur.html"
)
SNICE_INDIVIDUAL_CLASSIFIER_URL = (
    "https://www.snice.gob.mx/cs/avi/snice/hce.mi.fraccion.arancelaria.html"
)


@dataclass(frozen=True)
class LigieHtmlPage:
    page_id: str
    url: str
    role: str


LIGIE_HTML_PAGES: tuple[LigieHtmlPage, ...] = (
    LigieHtmlPage("diputados_ledger", DIPUTADOS_LEDGER_URL, "legal_ledger"),
    LigieHtmlPage("snice_ligie_index", SNICE_LIGIE_INDEX_URL, "ligie_discovery"),
    LigieHtmlPage("snice_nico_index", SNICE_NICO_INDEX_URL, "nico_discovery"),
    LigieHtmlPage(
        "snice_modifications_index",
        SNICE_MODIFICATIONS_INDEX_URL,
        "modification_discovery",
    ),
    LigieHtmlPage(
        "snice_biblioteca_juridica",
        SNICE_BIBLIOTECA_JURIDICA_URL,
        "official_consult_index",
    ),
    LigieHtmlPage(
        "snice_individual_classifier",
        SNICE_INDIVIDUAL_CLASSIFIER_URL,
        "individual_classifier",
    ),
)


def _fold(value: object) -> str:
    normalized = unicodedata.normalize("NFKD", " ".join(str(value or "").split()))
    return "".join(
        char for char in normalized if not unicodedata.combining(char)
    ).casefold()


class _LinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.links: list[tuple[str, str]] = []
        self._href: str | None = None
        self._parts: list[str] = []

    def handle_starttag(self, tag: str, attrs) -> None:
        if tag == "a":
            self._href = dict(attrs).get("href")
            self._parts = []
        elif tag == "iframe":
            src = dict(attrs).get("src")
            if src:
                self.links.append((src, "iframe"))

    def handle_data(self, data: str) -> None:
        if self._href is not None:
            self._parts.append(data)

    def handle_endtag(self, tag: str) -> None:
        if tag == "a" and self._href is not None:
            self.links.append((self._href, " ".join(self._parts)))
            self._href = None
            self._parts = []


def extract_links(html: str, base_url: str) -> list[tuple[str, str]]:
    parser = _LinkParser()
    parser.feed(html)
    return [
        (urljoin(base_url, href), title)
        for href, title in parser.links
        if href and not href.startswith("#")
    ]


def fracciones_arancelarias_consult_urls(html: str, base_url: str) -> list[str]:
    """Return absolute URLs for the official Fracciones Arancelarias consult entry points."""
    matches: list[str] = []
    for url, title in extract_links(html, base_url):
        folded = _fold(f"{title} {url}")
        if "fracciones arancelarias" in folded or "fraccion arancelaria" in folded:
            matches.append(url)
    return matches


def validate_diputados_ledger_html(html: str, base_url: str = DIPUTADOS_LEDGER_URL) -> None:
    snapshot = parse_ligie_ledger(html, base_url)
    if not snapshot.documents:
        raise ValueError("Diputados ledger HTML did not yield any documents")
    if not snapshot.last_law_reform or not snapshot.latest_tariff_modification:
        raise ValueError("Diputados ledger HTML is missing law or tariff dates")


def validate_snice_discovery_html(
    html: str,
    entry: RegistryEntry,
    *,
    required_role: str,
    base_url: str | None = None,
) -> None:
    class _Client:
        def __init__(self, text: str, url: str):
            self.text = text
            self.url = url

        def get(self, url, timeout=None):
            return self

        def raise_for_status(self):
            return None

    page_url = base_url or entry.canonical_page
    discovered = discover_registered_sources(
        {entry.dataset_key: entry},
        _Client(html, page_url),
    )
    roles = {item.document_role for item in discovered if item.dataset_key == entry.dataset_key}
    if required_role not in roles:
        raise ValueError(
            f"SNICE discovery HTML for {entry.dataset_key} is missing {required_role}; found {sorted(roles)}"
        )


def validate_biblioteca_juridica_html(
    html: str,
    base_url: str = SNICE_BIBLIOTECA_JURIDICA_URL,
) -> str:
    consult_urls = fracciones_arancelarias_consult_urls(html, base_url)
    if not consult_urls:
        raise ValueError("Biblioteca Jurídica HTML is missing a Fracciones Arancelarias consult link")
    return consult_urls[0]


def validate_individual_classifier_html(html: str) -> None:
    folded = _fold(html)
    markers = (
        "mi fraccion arancelaria",
        "fraccion arancelaria",
        "hce.mi.fraccion.arancelaria",
        "clasificador",
        "buscador",
    )
    if not any(marker in folded for marker in markers):
        raise ValueError("individual classifier HTML is missing expected consult markers")
    if "<iframe" not in html.lower() and "hce." not in folded and "consulta" not in folded:
        raise ValueError("individual classifier HTML does not expose an embeddable consult surface")


def validate_ligie_html_page(page_id: str, html: str, *, base_url: str | None = None) -> str | None:
    """Validate one official HTML page and optionally return a derived consult URL."""
    registry = load_source_registry()
    if page_id == "diputados_ledger":
        validate_diputados_ledger_html(html, base_url or DIPUTADOS_LEDGER_URL)
        return None
    if page_id == "snice_ligie_index":
        validate_snice_discovery_html(
            html,
            registry["ligie"],
            required_role="ligie_snapshot",
            base_url=base_url,
        )
        return None
    if page_id == "snice_nico_index":
        validate_snice_discovery_html(
            html,
            registry["nico"],
            required_role="nico_snapshot",
            base_url=base_url,
        )
        return None
    if page_id == "snice_modifications_index":
        if not re.search(r"ligie\.info\d+\.mod\d+\.html", html, flags=re.I):
            if "modificaciones" not in _fold(html):
                raise ValueError("SNICE modifications index HTML is missing modification markers")
        return None
    if page_id == "snice_biblioteca_juridica":
        return validate_biblioteca_juridica_html(
            html,
            base_url or SNICE_BIBLIOTECA_JURIDICA_URL,
        )
    if page_id == "snice_individual_classifier":
        validate_individual_classifier_html(html)
        return None
    raise ValueError(f"unknown LIGIE HTML page id: {page_id}")
