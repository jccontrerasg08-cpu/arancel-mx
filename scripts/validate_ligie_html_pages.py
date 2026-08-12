"""Fetch and validate official LIGIE HTML pages used for discovery and consult."""

from __future__ import annotations

import argparse

import requests

from arancel_mx.sources.html_pages import (
    OPERATIONAL_HTML_PAGES,
    HtmlAccessTarget,
    collect_ligie_html_access_targets,
    ensure_html_body_accessible,
    validate_ligie_html_page,
)
from scripts.check_documented_urls import build_session, check_reachable, fetch_html_body


def _fetch_html(
    session: requests.Session,
    url: str,
    *,
    timeout: float,
) -> tuple[int, str, str]:
    return fetch_html_body(session, url, timeout=timeout)


def _check_binary_target(
    session: requests.Session,
    target: HtmlAccessTarget,
    *,
    timeout: float,
) -> tuple[int, str]:
    status, final_url = check_reachable(session, target.url, timeout=timeout)
    if target.kind == "snapshot":
        response = session.head(final_url, allow_redirects=True, timeout=timeout)
        if response.status_code in {405, 501}:
            response = session.get(final_url, allow_redirects=True, timeout=timeout, stream=True)
            response.close()
        content_length = response.headers.get("Content-Length")
        if content_length is not None and int(content_length) < 1024:
            raise ValueError(f"{final_url} snapshot looks too small ({content_length} bytes)")
    return status, final_url


def validate_ligie_html_site(
    session: requests.Session,
    *,
    timeout: float = 30.0,
) -> list[str]:
    """Validate cataloged HTML pages and every linked resource they expose."""
    failures: list[str] = []
    visited: set[str] = set()

    def process_html_page(page_id: str, url: str, label: str) -> None:
        if url in visited:
            return
        visited.add(url)
        try:
            status, final_url, html = _fetch_html(session, url, timeout=timeout)
            validate_ligie_html_page(page_id, html, base_url=final_url)
            print(f"OK [{status}] {label}: {final_url}")
            for target in collect_ligie_html_access_targets(page_id, html, base_url=final_url):
                process_target(target)
        except Exception as exc:
            failures.append(f"{label} ({url}): {exc}")
            print(f"FAIL {label} ({url}) -> {exc}")

    def process_target(target: HtmlAccessTarget) -> None:
        if target.url in visited:
            return
        visited.add(target.url)
        try:
            if target.kind == "html_page":
                if not target.page_id:
                    raise ValueError(f"missing page_id for html_page target: {target.url}")
                process_html_page(target.page_id, target.url, target.page_id)
                return
            if target.kind == "embed" and target.url.lower().endswith((".html", ".htm")):
                status, final_url, html = _fetch_html(session, target.url, timeout=timeout)
                ensure_html_body_accessible(html, url=final_url)
                print(f"OK [{status}] embed: {final_url}")
                return
            status, final_url = _check_binary_target(session, target, timeout=timeout)
            print(f"OK [{status}] {target.kind}: {final_url}")
        except Exception as exc:
            failures.append(f"{target.kind} ({target.url}): {exc}")
            print(f"FAIL {target.kind} ({target.url}) -> {exc}")

    for page in OPERATIONAL_HTML_PAGES:
        process_html_page(page.page_id, page.url, page.page_id)

    return failures


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="Per-request timeout in seconds.",
    )
    args = parser.parse_args()

    failures = validate_ligie_html_site(build_session(), timeout=args.timeout)
    if failures:
        print("\nInvalid LIGIE HTML pages or linked resources:")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
