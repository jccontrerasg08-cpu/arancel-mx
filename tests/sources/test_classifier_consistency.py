from __future__ import annotations

from pathlib import Path

import pytest

from arancel_mx.sources.classifier_consistency import (
    descriptions_consistent,
    normalize_duty,
)
from arancel_mx.sources.siicex import SIICEX_HOME_URL, parse_fraction_document


FIXTURES = Path(__file__).resolve().parents[1] / "fixtures" / "siicex"


def test_parse_siicex_fraction_document_extracts_tariff_fields() -> None:
    html = (FIXTURES / "fraction.90014002.OpenDocument.html").read_text(encoding="utf-8")
    document = parse_fraction_document(html, expected_code="90014002")
    assert document.code == "90014002"
    assert "cristal oftálmico" in document.description.casefold()
    assert document.import_duty == "Ex."
    assert document.export_duty == "Ex."


def test_fraction_row_requires_an_exact_code_match() -> None:
    html = """
    <table>
      <tr><td>Fracción:</td><td>0190014002</td><td>otra fracción</td></tr>
    </table>
    """
    with pytest.raises(ValueError, match="missing a tariff row"):
        parse_fraction_document(html, expected_code="90014002")


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


def test_siicex_home_url_is_documented_http_endpoint() -> None:
    assert SIICEX_HOME_URL == "http://www.siicex-caaarem.org.mx/"
