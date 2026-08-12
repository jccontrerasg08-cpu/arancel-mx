"""Catalog and validation helpers for official LIGIE HTML pages."""

from __future__ import annotations

from dataclasses import dataclass
from html import unescape
from html.parser import HTMLParser
import re
import unicodedata
from urllib.parse import urljoin, urlparse

from arancel_mx.pipeline.reconcile import discover_registered_sources
from arancel_mx.sources.diputados import parse_ligie_ledger
from arancel_mx.sources.registry import RegistryEntry, load_source_registry
from arancel_mx.sources.siicex import (
    SIICEX_HOME_URL,
    SIICEX_SAMPLE_FRACTION_FIXTURE_URL,
    parse_fraction_document,
    validate_home_html,
)
from arancel_mx.sources.vucem import (
    VUCEM_CLASSIFIER_INDEX_URL,
    VUCEM_SAMPLE_FRACTION_SHEET_URL,
    parse_fraction_sheet,
)


DIPUTADOS_LEDGER_URL = "https://www.diputados.gob.mx/LeyesBiblio/ref/ligie_2022.htm"
SNICE_LIGIE_INDEX_URL = "https://www.snice.gob.mx/cs/avi/snice/ligie.info22.html"
SNICE_NICO_INDEX_URL = "https://www.snice.gob.mx/cs/avi/snice/ligie.nico2022.html"
SNICE_MODIFICATIONS_INDEX_URL = (
    "https://www.snice.gob.mx/cs/avi/snice/ligie.info22.mod.html"
)
SNICE_LEGAL_LIBRARY_INDEX_URL = (
    "https://www.snice.gob.mx/cs/avi/snice/biblioteca.juridica.html"
)
SNICE_BIBLIOTECA_JURIDICA_URL = (
    "https://www.snice.gob.mx/cs/avi/snice/ligie.info22.ligiebibjur.html"
)
SNICE_INDIVIDUAL_CLASSIFIER_URL = (
    "https://www.snice.gob.mx/cs/avi/snice/hce.mi.fraccion.arancelaria.html"
)
SNICE_FRACTION_CONSULT_URL = (
    "https://www.snice.gob.mx/cs/avi/snice/cp.consulta.fracciones.arancelarias.html"
)

MIN_HTML_BODY_BYTES = 256

_CONSULT_REFERENCE_MARKERS = (
    "fracciones arancelarias",
    "fraccion arancelaria",
    "fracciones.arancelarias",
    "cp.consulta.fracciones.arancelarias",
    "hce.consulta.fracciones.arancelarias",
    "hce.mi.fraccion.arancelaria",
)

_RAW_URL_PATTERN = re.compile(
    r"""(?:href|src|action|data-url|data-src)\s*=\s*["']([^"']+)["']""",
    re.IGNORECASE,
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
        "snice_legal_library_index",
        SNICE_LEGAL_LIBRARY_INDEX_URL,
        "legal_library_discovery",
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

VUCEM_HTML_PAGES: tuple[LigieHtmlPage, ...] = (
    LigieHtmlPage(
        "vucem_classifier_index",
        VUCEM_CLASSIFIER_INDEX_URL,
        "classifier_discovery",
    ),
    LigieHtmlPage(
        "vucem_fraction_sheet",
        VUCEM_SAMPLE_FRACTION_SHEET_URL,
        "fraction_sheet",
    ),
)

SIICEX_HTML_PAGES: tuple[LigieHtmlPage, ...] = (
    LigieHtmlPage(
        "siicex_home",
        SIICEX_HOME_URL,
        "classifier_discovery",
    ),
)

OPERATIONAL_HTML_PAGES: tuple[LigieHtmlPage, ...] = (
    LIGIE_HTML_PAGES + VUCEM_HTML_PAGES + SIICEX_HTML_PAGES
)


@dataclass(frozen=True)
class HtmlAccessTarget:
    """A linked resource that must be reachable to use a cataloged HTML page."""

    url: str
    kind: str
    page_id: str | None = None


def _fold(value: object) -> str:
    normalized = unicodedata.normalize("NFKD", " ".join(str(value or "").split()))
    return "".join(
        char for char in normalized if not unicodedata.combining(char)
    ).casefold()


def _fold_html(html: str) -> str:
    """Fold visible HTML text after decoding entities and normalizing accents."""
    return _fold(unescape(html))


def _fold_path(url: str) -> str:
    return _fold(urlparse(url).path)


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


def extract_iframe_srcs(html: str, base_url: str) -> list[str]:
    """Return absolute iframe src URLs embedded in one HTML page."""
    return [
        url
        for url, title in extract_links(html, base_url)
        if title == "iframe"
    ]


def _raw_linked_urls(html: str, base_url: str) -> list[str]:
    """Return absolute URLs referenced by legacy SNICE HTML attributes and scripts."""
    urls: list[str] = []
    for match in _RAW_URL_PATTERN.finditer(html):
        urls.append(urljoin(base_url, unescape(match.group(1))))
    return list(dict.fromkeys(urls))


def _references_consult_target(*, folded: str, url: str) -> bool:
    haystack = f"{folded} {_fold_path(url)}"
    return any(marker in haystack for marker in _CONSULT_REFERENCE_MARKERS)


def ensure_html_body_accessible(html: str, *, url: str) -> None:
    """Fail when an HTML response is empty or too small to contain page content."""
    encoded = html.encode("utf-8")
    if len(encoded) < MIN_HTML_BODY_BYTES:
        raise ValueError(
            f"{url} returned an unusually small HTML body ({len(encoded)} bytes)"
        )
    folded = _fold(html)
    if "<html" not in folded and "<body" not in folded and "<table" not in folded:
        raise ValueError(f"{url} does not look like an HTML document")


def ligie_entry_urls(html: str, base_url: str) -> list[str]:
    """Return absolute URLs that point to the official LIGIE section on SNICE."""
    matches: list[str] = []
    for url, title in extract_links(html, base_url):
        folded = _fold_html(f"{title} {url}")
        path_folded = _fold_path(url)
        if (
            "ligie.info" in folded
            or "impuestos generales de importacion" in folded
            or "ligie.info" in path_folded
        ):
            matches.append(url)
    return matches


def fracciones_arancelarias_consult_urls(html: str, base_url: str) -> list[str]:
    """Return absolute URLs for the official Fracciones Arancelarias consult entry points."""
    matches: list[str] = []
    candidates: list[str] = []
    candidates.extend(url for url, _title in extract_links(html, base_url))
    candidates.extend(extract_iframe_srcs(html, base_url))
    candidates.extend(_raw_linked_urls(html, base_url))
    for url in dict.fromkeys(candidates):
        if _references_consult_target(folded=_fold_html(url), url=url):
            matches.append(url)
    if not matches:
        folded_html = _fold_html(html)
        if any(marker in folded_html for marker in _CONSULT_REFERENCE_MARKERS):
            matches.append(SNICE_FRACTION_CONSULT_URL)
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


def validate_legal_library_index_html(
    html: str,
    base_url: str = SNICE_LEGAL_LIBRARY_INDEX_URL,
) -> str:
    folded = _fold_html(html)
    has_library_marker = (
        "biblioteca juridica" in folded
        or ("biblioteca" in folded and "juridica" in folded)
        or "codigos y leyes" in folded
    )
    if not has_library_marker:
        raise ValueError("SNICE legal library index HTML is missing Biblioteca Jurídica markers")
    ligie_urls = ligie_entry_urls(html, base_url)
    if not ligie_urls:
        raise ValueError("SNICE legal library index HTML is missing a LIGIE entry link")
    return ligie_urls[0]


def validate_biblioteca_juridica_html(
    html: str,
    base_url: str = SNICE_BIBLIOTECA_JURIDICA_URL,
) -> str:
    consult_urls = fracciones_arancelarias_consult_urls(html, base_url)
    if consult_urls:
        return consult_urls[0]
    folded = _fold_html(html)
    if "ligie" in folded and ("biblioteca" in folded or "juridica" in folded):
        return SNICE_FRACTION_CONSULT_URL
    raise ValueError("Biblioteca Jurídica HTML is missing a Fracciones Arancelarias consult link")


def validate_individual_classifier_html(html: str, *, base_url: str | None = None) -> None:
    folded = _fold_html(html)
    lowered = html.lower()
    canonical = bool(base_url and "hce.mi.fraccion.arancelaria" in _fold_path(base_url))
    markers = (
        "mi fraccion arancelaria",
        "fraccion arancelaria",
        "hce.mi.fraccion.arancelaria",
        "clasificador",
        "buscador",
        "hce.mi.fraccion",
    )
    if any(marker in folded for marker in markers):
        has_embed_surface = any(
            token in lowered or token in folded
            for token in ("<iframe", "<frame", "hce.", "consulta", "frameset")
        )
        if has_embed_surface or canonical:
            return
    if canonical:
        canonical_markers = (
            "hce.mi.fraccion.arancelaria",
            "hce.consulta.fracciones.arancelarias",
            "clasificador",
            "fraccion arancelaria",
            "snice",
            "ligie",
            "impuestos generales de importacion",
        )
        if any(marker in folded for marker in canonical_markers):
            return
        if any(token in lowered for token in ("<frame", "<iframe", "<frameset", "hce.")):
            return
    raise ValueError("individual classifier HTML is missing expected consult markers")


def validate_fraction_consult_html(html: str) -> None:
    folded = _fold_html(html)
    lowered = html.lower()
    markers = (
        "fracciones arancelarias",
        "fraccion arancelaria",
        "cp.consulta.fracciones.arancelarias",
        "consulta",
        "hce.",
    )
    if not any(marker in folded for marker in markers):
        raise ValueError("fraction consult HTML is missing expected consult markers")
    has_embed_surface = any(
        token in lowered or token in folded
        for token in ("<iframe", "<frame", "hce.", "consulta", "frameset")
    )
    if not has_embed_surface:
        raise ValueError("fraction consult HTML does not expose an embeddable consult surface")


def validate_vucem_classifier_index_html(html: str) -> None:
    folded = _fold_html(html)
    markers = (
        "fracciones arancelarias",
        "clasificador",
        "ventanilla",
        "vucem",
    )
    if not any(marker in folded for marker in markers):
        raise ValueError("VUCEM classifier index HTML is missing expected consult markers")


def validate_vucem_fraction_sheet_html(html: str, *, base_url: str) -> None:
    folded = _fold_html(html)
    markers = (
        "fraccion arancelaria",
        "importacion",
        "exportacion",
        "arancel",
        "igi",
        "ige",
        "ligie",
        "tigie",
    )
    if not any(marker in folded for marker in markers):
        raise ValueError("VUCEM fraction sheet HTML is missing tariff markers")
    if "<table" not in html.lower():
        raise ValueError("VUCEM fraction sheet HTML does not expose tariff table content")
    sheet = parse_fraction_sheet(html, base_url=base_url)
    if not sheet.description.strip():
        raise ValueError("VUCEM fraction sheet HTML is missing a fraction description")


def validate_siicex_fraction_document_html(
    html: str,
    *,
    base_url: str = SIICEX_SAMPLE_FRACTION_FIXTURE_URL,
) -> None:
    folded = _fold(html)
    if "fraccion" not in folded and "hts code" not in folded:
        raise ValueError("SIICEX fraction document HTML is missing fraction markers")
    if "<table" not in html.lower():
        raise ValueError("SIICEX fraction document HTML does not expose tariff table content")
    document = parse_fraction_document(html, expected_code=None)
    if not document.description.strip():
        raise ValueError("SIICEX fraction document HTML is missing a fraction description")


def collect_ligie_html_access_targets(
    page_id: str,
    html: str,
    *,
    base_url: str,
) -> tuple[HtmlAccessTarget, ...]:
    """Return linked resources that must be reachable to use one cataloged HTML page."""
    targets: list[HtmlAccessTarget] = []
    derived = _derived_consult_url(page_id, html, base_url)
    if page_id == "snice_legal_library_index" and derived:
        targets.append(HtmlAccessTarget(derived, "html_page", "snice_ligie_index"))
    if page_id == "snice_biblioteca_juridica" and derived:
        targets.append(HtmlAccessTarget(derived, "html_page", "snice_fraction_consult"))
    if page_id == "snice_individual_classifier":
        for iframe_url in extract_iframe_srcs(html, base_url):
            targets.append(HtmlAccessTarget(iframe_url, "embed", None))
    if page_id in {"snice_ligie_index", "snice_nico_index"}:
        registry = load_source_registry()
        entry = registry["ligie" if page_id == "snice_ligie_index" else "nico"]
        required_role = "ligie_snapshot" if page_id == "snice_ligie_index" else "nico_snapshot"

        class _Client:
            def __init__(self, text: str, url: str):
                self.text = text
                self.url = url

            def get(self, url, timeout=None):
                return self

            def raise_for_status(self):
                return None

        discovered = discover_registered_sources({entry.dataset_key: entry}, _Client(html, base_url))
        for document in discovered:
            if document.document_role == required_role:
                targets.append(HtmlAccessTarget(document.source_url, "snapshot", None))
    if page_id == "diputados_ledger":
        snapshot = parse_ligie_ledger(html, base_url)
        for document in snapshot.documents:
            if document.category == "consolidated_text":
                for link in document.links:
                    targets.append(HtmlAccessTarget(link.url, "document", None))
    return tuple(targets)


def _derived_consult_url(page_id: str, html: str, base_url: str) -> str | None:
    if page_id == "snice_legal_library_index":
        ligie_urls = ligie_entry_urls(html, base_url)
        return ligie_urls[0] if ligie_urls else None
    if page_id == "snice_biblioteca_juridica":
        consult_urls = fracciones_arancelarias_consult_urls(html, base_url)
        return consult_urls[0] if consult_urls else None
    return None


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
            if "modificaciones" not in _fold_html(html):
                raise ValueError("SNICE modifications index HTML is missing modification markers")
        return None
    if page_id == "snice_legal_library_index":
        return validate_legal_library_index_html(
            html,
            base_url or SNICE_LEGAL_LIBRARY_INDEX_URL,
        )
    if page_id == "snice_biblioteca_juridica":
        return validate_biblioteca_juridica_html(
            html,
            base_url or SNICE_BIBLIOTECA_JURIDICA_URL,
        )
    if page_id == "snice_fraction_consult":
        validate_fraction_consult_html(html)
        return None
    if page_id == "snice_individual_classifier":
        validate_individual_classifier_html(html, base_url=base_url or SNICE_INDIVIDUAL_CLASSIFIER_URL)
        return None
    if page_id == "vucem_classifier_index":
        validate_vucem_classifier_index_html(html)
        return None
    if page_id == "vucem_fraction_sheet":
        validate_vucem_fraction_sheet_html(html, base_url=base_url or VUCEM_SAMPLE_FRACTION_SHEET_URL)
        return None
    if page_id == "siicex_home":
        validate_home_html(html)
        return None
    if page_id == "siicex_fraction_document":
        validate_siicex_fraction_document_html(
            html,
            base_url=base_url or SIICEX_SAMPLE_FRACTION_FIXTURE_URL,
        )
        return None
    raise ValueError(f"unknown LIGIE HTML page id: {page_id}")
