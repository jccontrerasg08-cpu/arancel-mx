from pathlib import Path

from arancel_mx.sources.diputados import parse_ligie_ledger


FIXTURE = Path(__file__).parents[1] / "fixtures" / "diputados" / "ligie_2022.html"
BASE_URL = "https://www.diputados.gob.mx/LeyesBiblio/ref/ligie_2022.htm"


def test_parser_keeps_law_tariff_dates_and_document_families_distinct():
    snapshot = parse_ligie_ledger(FIXTURE.read_text(encoding="utf-8"), BASE_URL)

    assert snapshot.last_law_reform.isoformat() == "2025-12-29"
    assert snapshot.latest_tariff_modification.isoformat() == "2026-04-23"
    assert {document.category for document in snapshot.documents} == {
        "consolidated_text",
        "original",
        "law_reform",
        "tariff_decree",
        "nico_agreement",
        "national_notes",
        "correlation",
    }
