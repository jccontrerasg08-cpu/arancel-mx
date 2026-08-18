"""Controlled discovery of official PDF links from a registered DOF HTML page."""

from __future__ import annotations

from html.parser import HTMLParser
from urllib.parse import urljoin, urlparse


class _PdfLinkParser(HTMLParser):
    def __init__(self) -> None:
        super().__init__(convert_charrefs=True)
        self.hrefs: list[str] = []

    def handle_starttag(self, tag: str, attrs: list[tuple[str, str | None]]) -> None:
        if tag.lower() != "a":
            return
        for name, value in attrs:
            if name.lower() == "href" and value:
                self.hrefs.append(value)
                return


def discover_official_pdf_links(
    html: str,
    *,
    page_url: str,
    allowed_hosts: tuple[str, ...],
) -> tuple[str, ...]:
    """Return unique HTTPS PDF links on a registered official page.

    This function deliberately discovers only candidate source documents. Each URL
    must still be fetched through ``fetch_official_document`` so redirects, media
    type, size, capture hashing, and source provenance remain enforced.
    """

    page = urlparse(page_url)
    if page.scheme.lower() != "https":
        raise ValueError("registered DOF page must use https")
    normalized_hosts = {host.lower() for host in allowed_hosts}
    if not normalized_hosts:
        raise ValueError("allowed_hosts is required")

    parser = _PdfLinkParser()
    parser.feed(html)
    parser.close()

    links: list[str] = []
    seen: set[str] = set()
    for href in parser.hrefs:
        candidate = urljoin(page_url, href)
        parsed = urlparse(candidate)
        if parsed.scheme.lower() != "https":
            continue
        if (parsed.hostname or "").lower() not in normalized_hosts:
            continue
        if not parsed.path.lower().endswith(".pdf"):
            continue
        if candidate in seen:
            continue
        seen.add(candidate)
        links.append(candidate)
    return tuple(links)
