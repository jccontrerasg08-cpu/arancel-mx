from __future__ import annotations

import os
from pathlib import Path

import pytest
import requests

from scripts.check_documented_urls import (
    EXTERNALLY_UNPROBEABLE_URLS,
    EXTRA_DOCUMENTED_URLS,
    MARKDOWN_LINK_PATTERN,
    README_RELEASE_URLS,
    build_session,
    check_reachable,
    describe_request_failure,
    documented_public_urls,
    liveness_probe_urls,
    main,
    extract_bare_http_urls,
    fetch_html_body,
    is_parseable_url,
    probe_documented_urls,
    registered_public_urls,
    sanitize_documented_url,
)


ROOT = Path(__file__).resolve().parents[1]
SOURCE_DOC_PATH = ROOT / "docs" / "sources.md"


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


def test_transport_unprobeable_urls_remain_documented_but_are_excluded_from_liveness() -> None:
    documented = set(documented_public_urls())
    probe_urls = set(liveness_probe_urls())
    assert EXTERNALLY_UNPROBEABLE_URLS == {
        "https://www.ventanillaunica.gob.mx/vucem/Clasificador.html",
        "https://www.ventanillaunica.gob.mx/Clasificador/data/buildHojas1/90014002.html",
        "https://www.diputados.gob.mx/LeyesBiblio/ref/ligie_2022.htm",
        "https://www.diputados.gob.mx/LeyesBiblio/pdf/LIGIE_2022.pdf",
        "http://www.siicex-caaarem.org.mx/",
    }
    assert EXTERNALLY_UNPROBEABLE_URLS <= documented
    assert EXTERNALLY_UNPROBEABLE_URLS.isdisjoint(probe_urls)
    assert len(probe_urls) == len(documented) - len(EXTERNALLY_UNPROBEABLE_URLS)


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
    heading = "## páginas canónicas documentadas"
    if heading not in lowered:
        raise AssertionError("docs/sources.md is missing its canonical source-links section")
    start = lowered.index(heading)
    section = text[start + len(heading) :]
    if "\n## " in section:
        section = section.split("\n## ", 1)[0]
    return section


def test_source_guide_exposes_official_urls_as_parseable_markdown_links() -> None:
    text = SOURCE_DOC_PATH.read_text(encoding="utf-8")
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
        "docs/sources.md must expose canonical official URLs as markdown links, "
        f"not bare text: {sorted(bare_urls)}"
    )
    assert linked_urls, "docs/sources.md must document at least one official HTTPS link"
    assert all(is_parseable_url(url) for url in linked_urls)


def test_describe_request_failure_labels_tls_without_hiding_details() -> None:
    detail = describe_request_failure(requests.exceptions.SSLError("SSL_ERROR_SYSCALL"))
    assert detail.startswith("TLS transport failure")
    assert "SSL_ERROR_SYSCALL" in detail
    assert describe_request_failure(requests.Timeout("Read timed out.")) == "Read timed out."


def test_fetch_html_body_does_not_stack_connection_retries(monkeypatch: pytest.MonkeyPatch) -> None:
    sleeps: list[float] = []

    class _Session:
        def get(self, url: str, **kwargs: object) -> object:
            raise requests.ConnectionError("Network is unreachable")

    monkeypatch.setattr("scripts.check_documented_urls.time.sleep", sleeps.append)
    with pytest.raises(requests.ConnectionError, match="unreachable"):
        fetch_html_body(
            _Session(),  # type: ignore[arg-type]
            "https://www.snice.gob.mx/cs/avi/snice/ligie.info22.html",
            timeout=5,
        )

    assert sleeps == []


def test_probe_retries_only_urls_that_failed_the_first_pass(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    monkeypatch.setattr("scripts.check_documented_urls.time.sleep", lambda _seconds: None)
    seen: list[str] = []

    class _Response:
        status_code = 200
        url = "https://www.snice.gob.mx/cs/avi/snice/ligie.info22.html"
        text = "<html><body>" + ("LIGIE " * 80) + "</body></html>"

        def raise_for_status(self) -> None:
            return None

    class _Session:
        def get(self, url: str, **kwargs: object) -> _Response:
            seen.append(url)
            if url.endswith("ligie.info22.html") and seen.count(url) == 1:
                raise requests.Timeout("Read timed out.")
            response = _Response()
            response.url = url
            return response

    urls = (
        "https://www.snice.gob.mx/cs/avi/snice/ligie.nico2022.html",
        "https://www.snice.gob.mx/cs/avi/snice/ligie.info22.html",
    )
    session = _Session()
    remaining = probe_documented_urls(session, urls, timeout=5)  # type: ignore[arg-type]
    assert remaining == [urls[1]]
    remaining = probe_documented_urls(session, remaining, timeout=5)  # type: ignore[arg-type]
    assert remaining == []
    assert seen.count(urls[0]) == 1
    assert seen.count(urls[1]) == 2
    output = capsys.readouterr().out
    assert "FAIL" in output
    assert "OK [200]" in output


def test_url_check_waits_for_transient_failures_before_declaring_them_unreachable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    url = "https://github.com/jccontrerasg08-cpu/arancel-mx/actions"
    attempts: list[tuple[str, ...]] = []
    sleeps: list[float] = []
    outcomes = [[url], [url], []]

    monkeypatch.setattr("scripts.check_documented_urls.liveness_probe_urls", lambda: (url,))
    monkeypatch.setattr("scripts.check_documented_urls.build_session", object)
    monkeypatch.setattr("scripts.check_documented_urls.time.sleep", sleeps.append)

    def probe(_session: object, urls: tuple[str, ...] | list[str], *, timeout: float) -> list[str]:
        attempts.append(tuple(urls))
        return outcomes.pop(0)

    monkeypatch.setattr("scripts.check_documented_urls.probe_documented_urls", probe)
    monkeypatch.setattr("sys.argv", ["check_documented_urls.py"])

    assert main() == 0
    assert attempts == [(url,), (url,), (url,)]
    assert sleeps == [1.5, 3.0]


@pytest.mark.skipif(
    os.getenv("ARANCEL_MX_SKIP_URL_CHECKS") == "1",
    reason="documented URL reachability checks disabled",
)
def test_documented_public_urls_are_reachable() -> None:
    session = build_session()
    failures: list[str] = []
    for url in liveness_probe_urls():
        try:
            status, _final_url = check_reachable(session, url, timeout=30.0)
            assert 200 <= status < 400
        except requests.RequestException as exc:
            failures.append(f"{url}: {exc}")
    assert failures == []
