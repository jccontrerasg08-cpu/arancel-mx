"""Fetch and validate official LIGIE HTML pages used for discovery and consult."""

from __future__ import annotations

import argparse

import requests

from arancel_mx.sources.html_pages import LIGIE_HTML_PAGES, validate_ligie_html_page
from scripts.check_documented_urls import USER_AGENT, check_reachable, build_session


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--timeout",
        type=float,
        default=30.0,
        help="Per-request timeout in seconds.",
    )
    args = parser.parse_args()

    session = build_session()
    failures: list[str] = []
    for page in LIGIE_HTML_PAGES:
        try:
            status, final_url = check_reachable(session, page.url, timeout=args.timeout)
            if status >= 400:
                raise requests.HTTPError(f"{page.url} returned HTTP {status}")
            response = session.get(final_url, timeout=args.timeout)
            response.raise_for_status()
            derived = validate_ligie_html_page(
                page.page_id,
                response.text,
                base_url=final_url,
            )
            suffix = f" -> {derived}" if derived else ""
            print(f"OK [{status}] {page.page_id}: {final_url}{suffix}")
        except Exception as exc:
            failures.append(f"{page.page_id} ({page.url}): {exc}")
            print(f"FAIL {page.page_id}: {exc}")

    if failures:
        print("\nInvalid LIGIE HTML pages:")
        for failure in failures:
            print(f"  - {failure}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
