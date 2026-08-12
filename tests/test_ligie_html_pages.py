from __future__ import annotations

import os
from pathlib import Path

import pytest
import requests

from arancel_mx.sources.html_pages import (
    DIPUTADOS_LEDGER_URL,
    LIGIE_HTML_PAGES,
    SNICE_BIBLIOTECA_JURIDICA_URL,
    SNICE_INDIVIDUAL_CLASSIFIER_URL,
    SNICE_LIGIE_INDEX_URL,
    SNICE_MODIFICATIONS_INDEX_URL,
    SNICE_NICO_INDEX_URL,
    fracciones_arancelarias_consult_urls,
    validate_ligie_html_page,
)
from scripts.check_documented_urls import build_session, check_reachable
from scripts.validate_ligie_html_pages import main as validate_ligie_html_pages_main


FIXTURES = Path(__file__).resolve().parent / "fixtures"


def test_ligie_html_page_catalog_covers_pipeline_and_consult_entrypoints() -> None:
    page_ids = {page.page_id for page in LIGIE_HTML_PAGES}
    assert {
        "diputados_ledger",
        "snice_ligie_index",
        "snice_nico_index",
        "snice_biblioteca_juridica",
        "snice_individual_classifier",
    } <= page_ids


def test_offline_fixtures_parse_diputados_ledger_and_snice_discovery_pages() -> None:
    validate_ligie_html_page(
        "diputados_ledger",
        (FIXTURES / "diputados" / "ligie_2022.html").read_text(encoding="utf-8"),
        base_url=DIPUTADOS_LEDGER_URL,
    )
    validate_ligie_html_page(
        "snice_ligie_index",
        (FIXTURES / "snice" / "ligie.info22.html").read_text(encoding="utf-8"),
        base_url=SNICE_LIGIE_INDEX_URL,
    )
    validate_ligie_html_page(
        "snice_nico_index",
        (FIXTURES / "snice" / "ligie.nico2022.html").read_text(encoding="utf-8"),
        base_url=SNICE_NICO_INDEX_URL,
    )
    validate_ligie_html_page(
        "snice_modifications_index",
        (FIXTURES / "snice" / "ligie.info22.mod.html").read_text(encoding="utf-8"),
        base_url=SNICE_MODIFICATIONS_INDEX_URL,
    )


def test_biblioteca_juridica_fixture_exposes_individual_fraction_consult_link() -> None:
    html = (FIXTURES / "snice" / "ligie.info22.ligiebibjur.html").read_text(encoding="utf-8")
    consult_urls = fracciones_arancelarias_consult_urls(html, SNICE_BIBLIOTECA_JURIDICA_URL)
    assert consult_urls == [
        "https://www.snice.gob.mx/cs/avi/snice/cp.consulta.fracciones.arancelarias.html"
    ]
    assert (
        validate_ligie_html_page("snice_biblioteca_juridica", html, base_url=SNICE_BIBLIOTECA_JURIDICA_URL)
        == consult_urls[0]
    )


def test_individual_classifier_fixture_is_parseable_html_shell() -> None:
    html = (FIXTURES / "snice" / "hce.mi.fraccion.arancelaria.html").read_text(encoding="utf-8")
    validate_ligie_html_page("snice_individual_classifier", html)


@pytest.mark.skipif(
    os.getenv("ARANCEL_MX_SKIP_URL_CHECKS") == "1",
    reason="live LIGIE HTML page checks disabled",
)
def test_live_ligie_html_pages_are_reachable_and_parseable() -> None:
    session = build_session()
    failures: list[str] = []
    derived_consult_urls: list[str] = []
    for page in LIGIE_HTML_PAGES:
        try:
            status, final_url = check_reachable(session, page.url, timeout=30.0)
            response = session.get(final_url, timeout=30.0)
            response.raise_for_status()
            derived = validate_ligie_html_page(page.page_id, response.text, base_url=final_url)
            assert 200 <= status < 400
            if derived:
                derived_consult_urls.append(derived)
        except (requests.RequestException, ValueError) as exc:
            failures.append(f"{page.page_id}: {exc}")

    if derived_consult_urls:
        for consult_url in derived_consult_urls:
            consult_status, _ = check_reachable(session, consult_url, timeout=30.0)
            assert 200 <= consult_status < 400, consult_url

    assert failures == []


def test_validate_ligie_html_pages_script_exits_zero_when_pages_parse(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    html_by_url = {
        DIPUTADOS_LEDGER_URL: (FIXTURES / "diputados" / "ligie_2022.html").read_text(encoding="utf-8"),
        SNICE_LIGIE_INDEX_URL: (FIXTURES / "snice" / "ligie.info22.html").read_text(encoding="utf-8"),
        SNICE_NICO_INDEX_URL: (FIXTURES / "snice" / "ligie.nico2022.html").read_text(encoding="utf-8"),
        SNICE_BIBLIOTECA_JURIDICA_URL: (
            FIXTURES / "snice" / "ligie.info22.ligiebibjur.html"
        ).read_text(encoding="utf-8"),
        SNICE_MODIFICATIONS_INDEX_URL: (
            FIXTURES / "snice" / "ligie.info22.mod.html"
        ).read_text(encoding="utf-8"),
        SNICE_INDIVIDUAL_CLASSIFIER_URL: (
            FIXTURES / "snice" / "hce.mi.fraccion.arancelaria.html"
        ).read_text(encoding="utf-8"),
    }

    class _FakeResponse:
        def __init__(self, text: str):
            self.text = text

        def raise_for_status(self):
            return None

    class _FakeSession:
        def get(self, url, timeout=None):
            return _FakeResponse(html_by_url[url])

    monkeypatch.setattr("scripts.validate_ligie_html_pages.build_session", lambda: _FakeSession())
    monkeypatch.setattr(
        "scripts.validate_ligie_html_pages.check_reachable",
        lambda _session, url, timeout=30.0: (200, url),
    )
    monkeypatch.setattr("sys.argv", ["validate_ligie_html_pages"])

    assert validate_ligie_html_pages_main() == 0
