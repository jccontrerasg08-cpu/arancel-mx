from __future__ import annotations

from pathlib import Path

import pytest

from arancel_mx.sources.classifier_consistency import (
    ClassifierRecord,
    compare_classifier_records,
    compare_vucem_and_siicex_fractions,
    descriptions_consistent,
    normalize_duty,
)
from arancel_mx.sources.siicex import (
    SIICEX_SAMPLE_FRACTION_DOCUMENT_URL,
    SIICEX_TARIFA_INDEX_URL,
    parse_fraction_document,
)
from arancel_mx.sources.vucem import VUCEM_SAMPLE_FRACTION_SHEET_URL, parse_fraction_sheet


FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "siicex"


def test_parse_siicex_fraction_document_extracts_tariff_fields() -> None:
    html = (FIXTURES / "fraction.90014002.OpenDocument.html").read_text(encoding="utf-8")
    document = parse_fraction_document(html, expected_code="90014002")
    assert document.code == "90014002"
    assert "cristal oftálmico" in document.description.casefold()
    assert document.import_duty == "Ex."
    assert document.export_duty == "Ex."


def test_vucem_and_siicex_reference_fraction_fixtures_match() -> None:
    vucem_html = (
        Path(__file__).resolve().parents[1] / "fixtures" / "vucem" / "buildHojas1.90014002.html"
    ).read_text(encoding="utf-8")
    siicex_html = (FIXTURES / "fraction.90014002.OpenDocument.html").read_text(encoding="utf-8")
    discrepancies = compare_vucem_and_siicex_fractions(
        parse_fraction_sheet(vucem_html, base_url=VUCEM_SAMPLE_FRACTION_SHEET_URL),
        parse_fraction_document(siicex_html, expected_code="90014002"),
    )
    assert discrepancies == []


def test_compare_classifier_records_flags_duty_mismatch() -> None:
    left = ClassifierRecord("vucem", "90014002", "Lentes de cristal oftálmico", "Ex.", "Ex.")
    right = ClassifierRecord("siicex", "90014002", "Lentes de cristal oftálmico", "10%", "Ex.")
    assert compare_classifier_records(left, right) == [
        "import duty mismatch: vucem='Ex.' siicex='10%'"
    ]


def test_normalize_duty_treats_exempt_variants_equivalently() -> None:
    assert normalize_duty("Ex.") == normalize_duty("Ex")
    assert normalize_duty("Exento") == "ex"


def test_descriptions_consistent_accepts_subset_phrasing() -> None:
    long_text = (
        "Lentes de cristal oftálmico, sin graduación, destinados a la fabricación de "
        "anteojos de seguridad, con espesor igual o superior a 3 mm sin exceder de 3.8 mm."
    )
    short_text = "Lentes de cristal oftálmico para anteojos de seguridad"
    assert descriptions_consistent(long_text, short_text)


def test_siicex_tarifa_index_url_is_documented_http_endpoint() -> None:
    assert SIICEX_TARIFA_INDEX_URL.startswith("http://www.siicex-caaarem.org.mx/")
    assert "TarifaW?OpenView" in SIICEX_TARIFA_INDEX_URL
    assert "OpenDocument" in SIICEX_SAMPLE_FRACTION_DOCUMENT_URL
