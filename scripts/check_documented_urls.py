"""Verify documented public URLs are well-formed and reachable."""

from __future__ import annotations

import argparse
import json
import os
import re
from pathlib import Path
from urllib.parse import urlparse

import requests

from arancel_mx.sources.registry import load_source_registry


REPOSITORY_URL = "https://github.com/jccontrerasg08-cpu/arancel-mx"
USER_AGENT = f"arancel-mx-url-check/1.0 (+{REPOSITORY_URL})"

EXTRA_DOCUMENTED_URLS = (
    "https://www.dof.gob.mx/nota_detalle.php?codigo=5656249&fecha=27/06/2022",
    "https://www.contributor-covenant.org/version/2/1/code_of_conduct/",
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

URL_PATTERN = re.compile(r"https?://[^\s\)\]\"'<>,`]+")
MARKDOWN_LINK_PATTERN = re.compile(r"\[[^\]]+\]\((https?://[^)]+)\)")


def registered_public_urls() -> tuple[str, ...]:
    """Return every canonical URL declared in the versioned source registry."""
    urls: list[str] = []
    for entry in load_source_registry().values():
        urls.append(entry.canonical_page)
        urls.extend(url for _, url in entry.direct_documents)
    return tuple(dict.fromkeys(urls))


def documented_public_urls() -> tuple[str, ...]:
    """Return the curated set of public URLs documented for users and operators."""
    return tuple(
        dict.fromkeys(
            (
                *registered_public_urls(),
                *EXTRA_DOCUMENTED_URLS,
                *README_RELEASE_URLS,
            )
        )
    )


def is_parseable_url(url: str) -> bool:
    """Return True when a URL is absolute, HTTPS, and free of trailing punctuation."""
    if url != url.rstrip(".,;:"):
        return False
    parsed = urlparse(url)
    if parsed.scheme.lower() != "https":
        return False
    if not parsed.netloc:
        return False
    if any(char in url for char in (" ", "\n", "\r", "\t", "`", "<", ">")):
        return False
    return True


def extract_bare_http_urls(text: str) -> list[str]:
    """Extract bare HTTP(S) URLs that are not already inside markdown link targets."""
    linked = {match.group(1) for match in MARKDOWN_LINK_PATTERN.finditer(text)}
    bare_urls: list[str] = []
    for match in URL_PATTERN.finditer(text):
        url = match.group(0).rstrip(".,;:")
        if url in linked:
            continue
        bare_urls.append(url)
    return bare_urls


def check_reachable(session: requests.Session, url: str, *, timeout: float) -> tuple[int, str]:
    """Return the HTTP status and final URL for one documented public endpoint."""
    last_error: requests.RequestException | None = None
    for attempt in range(3):
        try:
            response = session.head(url, allow_redirects=True, timeout=timeout)
            if response.status_code in {405, 501}:
                response = session.get(url, allow_redirects=True, timeout=timeout, stream=True)
                response.close()
            if response.status_code >= 400:
                raise requests.HTTPError(
                    f"{url} returned HTTP {response.status_code}",
                    response=response,
                )
            return response.status_code, response.url
        except requests.RequestException as exc:
            last_error = exc
            if attempt == 2:
                break
    assert last_error is not None
    raise last_error


def build_session() -> requests.Session:
    session = requests.Session()
    session.headers["User-Agent"] = USER_AGENT
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
            status, final_url = check_reachable(session, url, timeout=args.timeout)
            suffix = f" -> {final_url}" if final_url != url else ""
            print(f"OK [{status}] {url}{suffix}")
        except requests.RequestException as exc:
            failures.append(f"{url}: {exc}")
            print(f"FAIL {url}: {exc}")

    if failures:
        print("\nUnreachable documented URLs:")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
