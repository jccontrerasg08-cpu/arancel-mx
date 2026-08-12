from __future__ import annotations

import os
from pathlib import Path

import pytest

from arancel_mx.sources.html_pages import (
    DIPUTADOS_LEDGER_URL,
    OPERATIONAL_HTML_PAGES,
    SNICE_BIBLIOTECA_JURIDICA_URL,
    SNICE_FRACTION_CONSULT_URL,
    SNICE_INDIVIDUAL_CLASSIFIER_URL,
    SNICE_LEGAL_LIBRARY_INDEX_URL,
    SNICE_LIGIE_INDEX_URL,
    SNICE_MODIFICATIONS_INDEX_URL,
    SNICE_NICO_INDEX_URL,
    collect_ligie_html_access_targets,
    ensure_html_body_accessible,
    fracciones_arancelarias_consult_urls,
    ligie_entry_urls,
    validate_ligie_html_page,
)
from scripts.check_documented_urls import looks_like_html_url
from arancel_mx.sources.siicex import SIICEX_HOME_URL
from arancel_mx.sources.vucem import (
    VUCEM_CLASSIFIER_INDEX_URL,
    VUCEM_SAMPLE_FRACTION_CODE,
    VUCEM_SAMPLE_FRACTION_SHEET_URL,
    fraction_sheet_url,
    parse_fraction_sheet,
)
from scripts.validate_ligie_html_pages import main as validate_ligie_html_pages_main


FIXTURES = Path(__file__).resolve().parent / "fixtures"
_FAKE_HTML = "<!doctype html><html><body>" + ("consulta fracciones arancelarias " * 20) + "</body></html>"


def test_operational_html_page_catalog_covers_pipeline_and_consult_entrypoints() -> None:
    page_ids = {page.page_id for page in OPERATIONAL_HTML_PAGES}
    assert {
        "diputados_ledger",
        "snice_ligie_index",
        "snice_nico_index",
        "snice_legal_library_index",
        "snice_biblioteca_juridica",
        "snice_individual_classifier",
        "vucem_classifier_index",
        "vucem_fraction_sheet",
        "siicex_home",
    } <= page_ids


def test_fraction_sheet_url_builds_official_vucem_path() -> None:
    assert (
        fraction_sheet_url("90014002")
        == "https://www.ventanillaunica.gob.mx/Clasificador/data/buildHojas1/90014002.html"
    )


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


def test_legal_library_index_fixture_exposes_ligie_entry_link() -> None:
    html = (FIXTURES / "snice" / "biblioteca.juridica.html").read_text(encoding="utf-8")
    ligie_urls = ligie_entry_urls(html, SNICE_LEGAL_LIBRARY_INDEX_URL)
    assert ligie_urls == ["https://www.snice.gob.mx/cs/avi/snice/ligie.info22.html"]
    assert (
        validate_ligie_html_page("snice_legal_library_index", html, base_url=SNICE_LEGAL_LIBRARY_INDEX_URL)
        == ligie_urls[0]
    )


def test_snice_validators_accept_entity_encoded_legacy_html() -> None:
    legal_library_html = (
        "<!doctype html><html><body>"
        "<h1>Biblioteca Jur&iacute;dica</h1>"
        "<h4>C&oacute;digos y Leyes</h4>"
        "<a href='ligie.info22.html'>Ley de los Impuestos Generales de Importaci&oacute;n y de Exportaci&oacute;n.</a>"
        "</body></html>"
    )
    biblioteca_html = (
        "<!doctype html><html><body>"
        "<h1>LIGIE</h1>"
        "<a href='cp.consulta.fracciones.arancelarias.html'>Consulta</a>"
        "</body></html>"
    )
    classifier_html = (
        "<!doctype html><html><body>"
        "<h1>Mi Fracci&oacute;n Arancelaria</h1>"
        "<iframe src='hce.mi.fraccion.arancelaria.app.html'></iframe>"
        "</body></html>"
    )
    validate_ligie_html_page(
        "snice_legal_library_index",
        legal_library_html,
        base_url=SNICE_LEGAL_LIBRARY_INDEX_URL,
    )
    consult_url = validate_ligie_html_page(
        "snice_biblioteca_juridica",
        biblioteca_html,
        base_url=SNICE_BIBLIOTECA_JURIDICA_URL,
    )
    assert consult_url.endswith("cp.consulta.fracciones.arancelarias.html")
    validate_ligie_html_page("snice_individual_classifier", classifier_html)
    assert fracciones_arancelarias_consult_urls(biblioteca_html, SNICE_BIBLIOTECA_JURIDICA_URL) == [
        SNICE_FRACTION_CONSULT_URL
    ]


def test_snice_validators_accept_frame_and_script_embedded_consult_paths() -> None:
    biblioteca_html = (
        "<!doctype html><html><frameset>"
        "<frame src='cp.consulta.fracciones.arancelarias.html'>"
        "</frameset></html>"
    )
    classifier_html = (
        "<!doctype html><html><head>"
        "<script>var app='hce.mi.fraccion.arancelaria.app.html';</script>"
        "</head><body><p>SNICE LIGIE</p></body></html>"
    )
    assert fracciones_arancelarias_consult_urls(biblioteca_html, SNICE_BIBLIOTECA_JURIDICA_URL)
    validate_ligie_html_page(
        "snice_biblioteca_juridica",
        "<html><body><h1>LIGIE Biblioteca Jur&iacute;dica</h1></body></html>",
        base_url=SNICE_BIBLIOTECA_JURIDICA_URL,
    )
    validate_ligie_html_page(
        "snice_individual_classifier",
        classifier_html,
        base_url=SNICE_INDIVIDUAL_CLASSIFIER_URL,
    )


def test_biblioteca_juridica_fixture_exposes_individual_fraction_consult_link() -> None:
    html = (FIXTURES / "snice" / "ligie.info22.ligiebibjur.html").read_text(encoding="utf-8")
    consult_urls = fracciones_arancelarias_consult_urls(html, SNICE_BIBLIOTECA_JURIDICA_URL)
    assert consult_urls == [SNICE_FRACTION_CONSULT_URL]
    assert (
        validate_ligie_html_page("snice_biblioteca_juridica", html, base_url=SNICE_BIBLIOTECA_JURIDICA_URL)
        == consult_urls[0]
    )


def test_fraction_consult_fixture_is_parseable_html_shell() -> None:
    html = (FIXTURES / "snice" / "cp.consulta.fracciones.arancelarias.html").read_text(encoding="utf-8")
    validate_ligie_html_page("snice_fraction_consult", html)


def test_vucem_fraction_sheet_fixture_exposes_tariff_and_nico_rows() -> None:
    html = (FIXTURES / "vucem" / "buildHojas1.90014002.html").read_text(encoding="utf-8")
    validate_ligie_html_page("vucem_fraction_sheet", html, base_url=VUCEM_SAMPLE_FRACTION_SHEET_URL)
    sheet = parse_fraction_sheet(html, base_url=VUCEM_SAMPLE_FRACTION_SHEET_URL)
    assert sheet.code == VUCEM_SAMPLE_FRACTION_CODE
    assert "cristal oftálmico" in sheet.description.casefold()
    assert sheet.import_duty == "Ex."
    assert sheet.export_duty == "Ex."
    assert sheet.nico_rows[0][0] == "00"


def test_siicex_home_and_fraction_document_fixtures_parse() -> None:
    home_html = (FIXTURES / "siicex" / "home.html").read_text(encoding="utf-8")
    fraction_html = (FIXTURES / "siicex" / "fraction.90014002.OpenDocument.html").read_text(encoding="utf-8")
    validate_ligie_html_page("siicex_home", home_html, base_url=SIICEX_HOME_URL)
    validate_ligie_html_page(
        "siicex_fraction_document",
        fraction_html,
        base_url="http://www.siicex-caaarem.org.mx/Bases/tigiei.nsf/example?OpenDocument",
    )


def test_vucem_classifier_index_fixture_is_parseable() -> None:
    html = (FIXTURES / "vucem" / "Clasificador.html").read_text(encoding="utf-8")
    validate_ligie_html_page("vucem_classifier_index", html, base_url=VUCEM_CLASSIFIER_INDEX_URL)


def test_collect_access_targets_follows_ligie_entry_consult_and_snapshot_links() -> None:
    legal_library_html = (FIXTURES / "snice" / "biblioteca.juridica.html").read_text(encoding="utf-8")
    biblioteca_html = (FIXTURES / "snice" / "ligie.info22.ligiebibjur.html").read_text(encoding="utf-8")
    ligie_index_html = (FIXTURES / "snice" / "ligie.info22.html").read_text(encoding="utf-8")
    classifier_html = (FIXTURES / "snice" / "hce.mi.fraccion.arancelaria.html").read_text(encoding="utf-8")
    ledger_html = (FIXTURES / "diputados" / "ligie_2022.html").read_text(encoding="utf-8")

    legal_targets = collect_ligie_html_access_targets(
        "snice_legal_library_index",
        legal_library_html,
        base_url=SNICE_LEGAL_LIBRARY_INDEX_URL,
    )
    assert legal_targets[0].url == SNICE_LIGIE_INDEX_URL
    assert legal_targets[0].page_id == "snice_ligie_index"

    biblioteca_targets = collect_ligie_html_access_targets(
        "snice_biblioteca_juridica",
        biblioteca_html,
        base_url=SNICE_BIBLIOTECA_JURIDICA_URL,
    )
    assert biblioteca_targets[0].url == SNICE_FRACTION_CONSULT_URL
    assert biblioteca_targets[0].page_id == "snice_fraction_consult"

    ligie_targets = collect_ligie_html_access_targets(
        "snice_ligie_index",
        ligie_index_html,
        base_url=SNICE_LIGIE_INDEX_URL,
    )
    assert any(target.kind == "snapshot" for target in ligie_targets)

    classifier_targets = collect_ligie_html_access_targets(
        "snice_individual_classifier",
        classifier_html,
        base_url=SNICE_INDIVIDUAL_CLASSIFIER_URL,
    )
    assert classifier_targets[0].kind == "embed"

    ledger_targets = collect_ligie_html_access_targets(
        "diputados_ledger",
        ledger_html,
        base_url=DIPUTADOS_LEDGER_URL,
    )
    assert any(target.kind == "document" for target in ledger_targets)


def test_ensure_html_body_accessible_rejects_tiny_pages() -> None:
    with pytest.raises(ValueError, match="unusually small"):
        ensure_html_body_accessible("<html><body>x</body></html>", url="https://example.test/page.html")


def test_looks_like_html_url_detects_documented_html_endpoints() -> None:
    assert looks_like_html_url(SNICE_LIGIE_INDEX_URL)
    assert looks_like_html_url(VUCEM_SAMPLE_FRACTION_SHEET_URL)
    assert not looks_like_html_url(SIICEX_HOME_URL)
    assert looks_like_html_url("https://www.dof.gob.mx/nota_detalle.php?codigo=1")
    assert not looks_like_html_url("https://www.diputados.gob.mx/LeyesBiblio/pdf/LIGIE_2022.pdf")


def test_individual_classifier_fixture_is_parseable_html_shell() -> None:
    html = (FIXTURES / "snice" / "hce.mi.fraccion.arancelaria.html").read_text(encoding="utf-8")
    validate_ligie_html_page("snice_individual_classifier", html)


@pytest.mark.skipif(
    os.getenv("ARANCEL_MX_SKIP_URL_CHECKS") == "1",
    reason="live LIGIE HTML page checks disabled",
)
def test_live_ligie_html_pages_are_reachable_and_parseable() -> None:
    from scripts.check_documented_urls import build_session
    from scripts.validate_ligie_html_pages import validate_ligie_html_site

    failures = validate_ligie_html_site(build_session(), timeout=30.0)
    assert failures == []


def test_validate_ligie_html_pages_script_exits_zero_when_pages_parse(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    html_by_url = {
        DIPUTADOS_LEDGER_URL: (FIXTURES / "diputados" / "ligie_2022.html").read_text(encoding="utf-8"),
        SNICE_LIGIE_INDEX_URL: (FIXTURES / "snice" / "ligie.info22.html").read_text(encoding="utf-8"),
        SNICE_NICO_INDEX_URL: (FIXTURES / "snice" / "ligie.nico2022.html").read_text(encoding="utf-8"),
        SNICE_LEGAL_LIBRARY_INDEX_URL: (
            FIXTURES / "snice" / "biblioteca.juridica.html"
        ).read_text(encoding="utf-8"),
        SNICE_BIBLIOTECA_JURIDICA_URL: (
            FIXTURES / "snice" / "ligie.info22.ligiebibjur.html"
        ).read_text(encoding="utf-8"),
        SNICE_FRACTION_CONSULT_URL: (
            FIXTURES / "snice" / "cp.consulta.fracciones.arancelarias.html"
        ).read_text(encoding="utf-8"),
        SNICE_MODIFICATIONS_INDEX_URL: (
            FIXTURES / "snice" / "ligie.info22.mod.html"
        ).read_text(encoding="utf-8"),
        SNICE_INDIVIDUAL_CLASSIFIER_URL: (
            FIXTURES / "snice" / "hce.mi.fraccion.arancelaria.html"
        ).read_text(encoding="utf-8"),
        VUCEM_CLASSIFIER_INDEX_URL: (FIXTURES / "vucem" / "Clasificador.html").read_text(encoding="utf-8"),
        VUCEM_SAMPLE_FRACTION_SHEET_URL: (
            FIXTURES / "vucem" / "buildHojas1.90014002.html"
        ).read_text(encoding="utf-8"),
        SIICEX_HOME_URL: (FIXTURES / "siicex" / "home.html").read_text(encoding="utf-8"),
        "https://www.snice.gob.mx/cs/avi/snice/hce.mi.fraccion.arancelaria.app.html": _FAKE_HTML,
        "https://www.snice.gob.mx/cs/avi/snice/hce.consulta.fracciones.arancelarias.app.html": _FAKE_HTML,
        "https://www.snice.gob.mx/files/FRACCIONESARANCELARIAS_20260810.XLSX": "snapshot",
        "https://www.snice.gob.mx/files/NICO-AGOSTO26-LIGIE_20260810-20260810.XLSX": "snapshot",
        "https://www.diputados.gob.mx/LeyesBiblio/pdf/LIGIE_2022.pdf": "document",
    }

    class _FakeResponse:
        def __init__(self, text: str):
            self.text = text
            self.status_code = 200
            self.url = ""
            self.headers = {"Content-Length": "4096"}

        def raise_for_status(self):
            return None

        def close(self):
            return None

    class _FakeSession:
        def get(self, url, timeout=None, allow_redirects=True, stream=False):
            payload = html_by_url[url]
            text = payload if isinstance(payload, str) and payload not in {"snapshot", "document"} else _FAKE_HTML
            response = _FakeResponse(text)
            response.url = url
            return response

        def head(self, url, timeout=None, allow_redirects=True):
            response = _FakeResponse("ok")
            response.url = url
            return response

    monkeypatch.setattr("scripts.validate_ligie_html_pages.build_session", lambda: _FakeSession())
    monkeypatch.setattr("sys.argv", ["validate_ligie_html_pages"])

    assert validate_ligie_html_pages_main() == 0
