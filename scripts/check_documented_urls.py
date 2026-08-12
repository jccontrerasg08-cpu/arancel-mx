"""Verify documented public URLs are well-formed and reachable."""

from __future__ import annotations

import argparse
import re
from urllib.parse import urlparse

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.ssl_ import create_urllib3_context

from arancel_mx.sources.html_pages import (
    OPERATIONAL_HTML_PAGES,
    SNICE_BIBLIOTECA_JURIDICA_URL,
    SNICE_INDIVIDUAL_CLASSIFIER_URL,
    SNICE_MODIFICATIONS_INDEX_URL,
    ensure_html_body_accessible,
)
from arancel_mx.sources.registry import load_source_registry


REPOSITORY_URL = "https://github.com/jccontrerasg08-cpu/arancel-mx"
USER_AGENT = f"arancel-mx-url-check/1.0 (+{REPOSITORY_URL})"

DOF_NICO_METHODOLOGY_URL = (
    "https://dof.gob.mx/nota_detalle.php?codigo=5656249&fecha=27/06/2022"
)

EXTRA_DOCUMENTED_URLS = (
    DOF_NICO_METHODOLOGY_URL,
    "https://www.contributor-covenant.org/version/2/1/code_of_conduct/",
    SNICE_MODIFICATIONS_INDEX_URL,
    SNICE_BIBLIOTECA_JURIDICA_URL,
    SNICE_INDIVIDUAL_CLASSIFIER_URL,
)

README_RELEASE_URLS = (
    f"{REPOSITORY_URL}/releases/latest",
    f"{REPOSITORY_URL}/releases/latest/download/arancel_mx.duckdb",
    f"{REPOSITORY_URL}/releases/latest/download/arancel_mx.csv",
    f"{REPOSITORY_URL}/releases/latest/download/arancel_mx.json",
    f"{REPOSITORY_URL}/releases/latest/download/manifest.json",
    f"{REPOSITORY_URL}/releases/latest/download/SHA256SUMS",
    f"{REPOSITORY_URL}/releases/latest/download/official-sources.tar.gz",
    f"{REPOSITORY_URL}/actions",
)

URL_PATTERN = re.compile(r"https?://[^\s\)\]\"'<>,`:]+")
MARKDOWN_LINK_PATTERN = re.compile(r"\[[^\]]+\]\((https?://[^)]+)\)")
TRAILING_URL_PUNCTUATION = ".,;:"


def sanitize_documented_url(url: str) -> str:
    """Strip trailing punctuation that markdown or log formatting may leave on a URL."""
    return url.strip().rstrip(TRAILING_URL_PUNCTUATION)


def registered_public_urls() -> tuple[str, ...]:
    """Return every canonical URL declared in the versioned source registry."""
    urls: list[str] = []
    for entry in load_source_registry().values():
        urls.append(entry.canonical_page)
        urls.extend(url for _, url in entry.direct_documents)
    return tuple(dict.fromkeys(urls))


def documented_public_urls() -> tuple[str, ...]:
    """Return the curated set of public URLs documented for users and operators."""
    html_page_urls = tuple(page.url for page in OPERATIONAL_HTML_PAGES)
    return tuple(
        dict.fromkeys(
            (
                *registered_public_urls(),
                *EXTRA_DOCUMENTED_URLS,
                *README_RELEASE_URLS,
                *html_page_urls,
            )
        )
    )


def extract_bare_http_urls(text: str) -> list[str]:
    """Extract bare HTTP(S) URLs that are not already inside markdown link targets."""
    linked = {sanitize_documented_url(match.group(1)) for match in MARKDOWN_LINK_PATTERN.finditer(text)}
    bare_urls: list[str] = []
    for match in URL_PATTERN.finditer(text):
        url = sanitize_documented_url(match.group(0))
        if url in linked:
            continue
        bare_urls.append(url)
    return bare_urls


def is_parseable_url(url: str) -> bool:
    """Return True when a URL is absolute, HTTPS (or allowed HTTP), and well-formed."""
    cleaned = sanitize_documented_url(url)
    if cleaned != url.strip():
        return False
    parsed = urlparse(cleaned)
    scheme = parsed.scheme.lower()
    if scheme not in {"https", "http"}:
        return False
    if scheme == "http":
        from arancel_mx.sources.siicex import SIICEX_HTTP_HOSTS

        if parsed.netloc.lower() not in SIICEX_HTTP_HOSTS:
            return False
    if not parsed.netloc:
        return False
    if any(char in cleaned for char in (" ", "\n", "\r", "\t", "`", "<", ">")):
        return False
    return True


def looks_like_html_url(url: str) -> bool:
    """Return True when a documented URL should return an HTML document body."""
    parsed = urlparse(sanitize_documented_url(url))
    path = parsed.path.lower()
    query = parsed.query.lower()
    return path.endswith((".html", ".htm", ".php")) or "openview" in query or "opendocument" in query


def fetch_html_body(
    session: requests.Session,
    url: str,
    *,
    timeout: float,
) -> tuple[int, str, str]:
    """Download one HTML page, verify it is usable, and return status, final URL, and body."""
    cleaned = sanitize_documented_url(url)
    last_error: requests.RequestException | ValueError | None = None
    for attempt in range(3):
        try:
            response = session.get(cleaned, allow_redirects=True, timeout=timeout)
            response.raise_for_status()
            ensure_html_body_accessible(response.text, url=response.url)
            return response.status_code, response.url, response.text
        except (requests.RequestException, ValueError) as exc:
            last_error = exc
            if attempt == 2:
                break
    assert last_error is not None
    raise last_error


def fetch_accessible_html(
    session: requests.Session,
    url: str,
    *,
    timeout: float,
) -> tuple[int, str]:
    """Download one HTML page and verify it contains usable content."""
    status, final_url, _html = fetch_html_body(session, url, timeout=timeout)
    return status, final_url


def check_documented_url(
    session: requests.Session,
    url: str,
    *,
    timeout: float,
) -> tuple[int, str]:
    """Return the HTTP status and final URL for one documented public endpoint."""
    cleaned = sanitize_documented_url(url)
    if looks_like_html_url(cleaned):
        return fetch_accessible_html(session, cleaned, timeout=timeout)
    return check_reachable(session, cleaned, timeout=timeout)


def check_reachable(session: requests.Session, url: str, *, timeout: float) -> tuple[int, str]:
    """Return the HTTP status and final URL for one documented public endpoint."""
    cleaned = sanitize_documented_url(url)
    last_error: requests.RequestException | None = None
    for attempt in range(3):
        try:
            response = session.head(cleaned, allow_redirects=True, timeout=timeout)
            if response.status_code in {405, 501}:
                response = session.get(cleaned, allow_redirects=True, timeout=timeout, stream=True)
                response.close()
            if response.status_code >= 400:
                raise requests.HTTPError(
                    f"{cleaned} returned HTTP {response.status_code}",
                    response=response,
                )
            return response.status_code, response.url
        except requests.RequestException as exc:
            last_error = exc
            if attempt == 2:
                break
    assert last_error is not None
    raise last_error


class _LegacyGovernmentSslAdapter(HTTPAdapter):
    """Allow HTTPS to legacy Mexican government hosts with weak DH parameters."""

    def init_poolmanager(self, *args, **kwargs):
        context = create_urllib3_context()
        context.set_ciphers("DEFAULT:@SECLEVEL=1")
        kwargs["ssl_context"] = context
        return super().init_poolmanager(*args, **kwargs)


def build_session() -> requests.Session:
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT
    session.mount("https://", _LegacyGovernmentSslAdapter())
    return session


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="Per-request timeout in seconds.",
    )
    args = parser.parse_args()

    malformed = [url for url in documented_public_urls() if not is_parseable_url(url)]
    if malformed:
        print("Malformed documented URLs:")
        for url in malformed:
            print(f"  - {url}")
        return 1

    session = build_session()
    failures: list[str] = []
    for url in documented_public_urls():
        try:
            status, final_url = check_documented_url(session, url, timeout=args.timeout)
            suffix = f" -> {final_url}" if final_url != sanitize_documented_url(url) else ""
            print(f"OK [{status}] {url}{suffix}")
        except (requests.RequestException, ValueError) as exc:
            failures.append(f"{url} -> {exc}")
            print(f"FAIL {url} -> {exc}")

    if failures:
        print("\nUnreachable documented URLs:")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
