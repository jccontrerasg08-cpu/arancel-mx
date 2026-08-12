from __future__ import annotations

import os
from pathlib import Path

import pytest
import requests

from scripts.check_documented_urls import (
    EXTRA_DOCUMENTED_URLS,
    MARKDOWN_LINK_PATTERN,
    README_RELEASE_URLS,
    build_session,
    check_reachable,
    documented_public_urls,
    extract_bare_http_urls,
    is_parseable_url,
    registered_public_urls,
    sanitize_documented_url,
)


ROOT = Path(__file__).resolve().parents[1]
README_PATHS = (ROOT / "README.md", ROOT / "README.en.md")


def test_registered_public_urls_are_https_and_unique() -> None:
    urls = registered_public_urls()
    assert urls
    assert len(urls) == len(set(urls))
    assert all(is_parseable_url(url) for url in urls)


def test_documented_public_urls_include_registry_readme_and_governance_links() -> None:
    documented = set(documented_public_urls())
    for url in registered_public_urls():
        assert url in documented
    for url in EXTRA_DOCUMENTED_URLS:
        assert url in documented
    for url in README_RELEASE_URLS:
        assert url in documented


def test_documented_public_urls_have_no_trailing_punctuation() -> None:
    for url in documented_public_urls():
        assert url == sanitize_documented_url(url), f"trailing punctuation in documented URL: {url!r}"


def test_sanitize_documented_url_strips_trailing_colons_and_commas() -> None:
    assert (
        sanitize_documented_url(
            "https://www.ventanillaunica.gob.mx/vucem/clasificador.html:"
        )
        == "https://www.ventanillaunica.gob.mx/vucem/clasificador.html"
    )
    assert sanitize_documented_url("https://example.com/path,") == "https://example.com/path"


def _official_sources_section(text: str) -> str:
    lowered = text.lower()
    for heading in ("## fuentes oficiales", "## official sources"):
        if heading in lowered:
            start = lowered.index(heading)
            section = text[start + len(heading) :]
            if "\n## " in section:
                section = section.split("\n## ", 1)[0]
            return section
    raise AssertionError("README is missing an official sources section")


def test_readme_official_sources_use_parseable_markdown_links() -> None:
    for readme_path in README_PATHS:
        text = readme_path.read_text(encoding="utf-8")
        section = _official_sources_section(text)
        linked_urls = {
            match.group(1)
            for match in MARKDOWN_LINK_PATTERN.finditer(section)
            if match.group(1).startswith("https://")
        }
        bare_urls = {
            url
            for url in extract_bare_http_urls(section)
            if url.startswith("https://")
        }
        assert bare_urls == set(), (
            f"{readme_path.name} must expose official source URLs as markdown links, "
            f"not bare text: {sorted(bare_urls)}"
        )
        assert linked_urls, f"{readme_path.name} must document at least one official HTTPS link"
        assert all(is_parseable_url(url) for url in linked_urls)


@pytest.mark.skipif(
    os.getenv("ARANCEL_MX_SKIP_URL_CHECKS") == "1",
    reason="documented URL reachability checks disabled",
)
def test_documented_public_urls_are_reachable() -> None:
    session = build_session()
    failures: list[str] = []
    for url in documented_public_urls():
        try:
            status, _final_url = check_reachable(session, url, timeout=30.0)
            assert 200 <= status < 400
        except requests.RequestException as exc:
            failures.append(f"{url}: {exc}")
    assert failures == []
