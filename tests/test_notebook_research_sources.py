from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
RESEARCH = ROOT / "docs" / "research"


def _load(name: str) -> dict:
    return json.loads((RESEARCH / name).read_text(encoding="utf-8"))


def test_notebook_source_inventory_reconciles_visible_entries() -> None:
    inventory = _load("notebooklm-source-inventory-2026-11-21.json")
    sources = inventory["sources"]
    assert inventory["ui_source_count"] == 41
    assert inventory["visible_entries"] == 42
    assert len(sources) == 42
    assert len({entry["title"] for entry in sources}) == 41
    assert [entry["order"] for entry in sources] == list(range(1, 43))
    assert sum(entry["source_type"] == "federal_law" for entry in sources) == 26
    assert sum(entry["url"] == inventory["explicit_duplicate_url"] for entry in sources) == 2
    assert all(entry["content_copied"] is False for entry in sources)
    assert inventory["pdf_header_sampling"]["unique_pdf_urls"] == 25
    assert inventory["pdf_header_sampling"]["returned_pdf_urls"] == 25
    assert inventory["pdf_header_sampling"]["extracted_last_reform_dates"] == 22


def test_notebook_links_do_not_claim_unobserved_import_urls() -> None:
    inventory = _load("notebooklm-source-inventory-2026-11-21.json")
    for entry in inventory["sources"]:
        assert entry["link_basis"] in {
            "shown_literal_in_notebook",
            "public_reference_suggested_not_original_url",
            "unknown",
        }
        if entry["link_basis"] == "unknown":
            assert entry["url"] is None
        elif entry["url"]:
            url = urlparse(entry["url"])
            assert url.scheme == "https" and url.hostname
        if entry["link_basis"] == "shown_literal_in_notebook":
            assert entry["url"] == entry["title"]


def test_legal_freshness_and_amount_updates_are_distinct() -> None:
    catalog = _load("external-trade-source-catalog.json")
    laws = {item["id"]: item for item in catalog["legal_framework"]["laws"]}
    assert catalog["legal_framework"]["last_verified_at"] == "2026-11-21"
    assert laws["lisr"]["last_reform_dof"] == "2026-11-13"
    assert laws["lfd"]["last_reform_dof"] == "2026-11-13"
    assert laws["lfd"]["last_amount_update_dof"] == "2025-12-28"
    assert laws["lieps"]["last_reform_dof"] == "2025-11-07"
    assert laws["lieps"]["last_amount_update_dof"] == "2025-12-22"
    assert laws["lfisan"]["last_reform_dof"] == "2021-11-12"
    assert laws["lfisan"]["last_amount_update_dof"] == "2025-12-28"
    pages = catalog["legal_framework"]["official_pages"]
    assert len({page["id"] for page in pages}) == len(pages)
    assert "sat_rgce_2026_modifications" in {page["id"] for page in pages}
    assert "quality_infrastructure_regulation_2026" in {page["id"] for page in pages}
    rgce = next(s for s in catalog["sources"] if s["id"] == "rgce")
    assert "27-12-2025" in rgce["publication_or_version"]
    assert rgce["modifications_index_url"].startswith("https://www.sat.gob.mx/")


def test_statistical_sources_include_vintage_and_censorship() -> None:
    catalog = _load("inegi-analytics-catalog.json")
    sources = {source["id"]: source for source in catalog["sources"]}
    assert len(sources) == len(catalog["sources"])
    assert sources["inegi_bcmm_cube_monthly"]["confidentiality_code"] == "C"
    assert sources["inegi_bcmm_cube_monthly"]["valuation_basis"] == "FOB"
    assert sources["inegi_tigie_scian_correlation"]["type"] == (
        "statistical_mapping_not_legal_tariff_release"
    )
    index = (ROOT / "docs" / "README.md").read_text(encoding="utf-8")
    assert "notebooklm-source-audit-2026-11-21.md" in index
    assert "notebooklm-source-inventory-2026-11-21.json" in index
