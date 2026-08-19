from __future__ import annotations

import json
from pathlib import Path
from urllib.parse import urlparse


ROOT = Path(__file__).resolve().parents[1]
CATALOG_PATH = ROOT / "docs" / "research" / "external-trade-source-catalog.json"
MAP_PATH = ROOT / "docs" / "research" / "external-trade-coverage-map.md"
DOCS_INDEX_PATH = ROOT / "docs" / "README.md"
ROOT_README_PATH = ROOT / "README.md"


EXPECTED_IDS = {
    "ligie",
    "nico",
    "national_notes",
    "tariff_indicators",
    "customs_law",
    "foreign_trade_law",
    "rgce",
    "treaties",
    "non_tariff_measures",
    "foreign_trade_procedures",
    "importer_exporter_registry",
    "promotion_programs",
}
ALLOWED_MODEL_STATUS = {
    "included_in_verified_dataset",
    "official_reference",
    "external_transactional_service",
}


def test_external_trade_catalog_covers_the_comparable_public_domains() -> None:
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))

    assert catalog["schema_version"] == "1"
    assert catalog["purpose"].startswith("Navegación")
    assert {item["id"] for item in catalog["sources"]} == EXPECTED_IDS



def test_catalog_records_only_official_sources_and_declares_boundary() -> None:
    catalog = json.loads(CATALOG_PATH.read_text(encoding="utf-8"))

    for item in catalog["sources"]:
        assert item["model_status"] in ALLOWED_MODEL_STATUS
        assert item["source_role"]
        assert item["boundary"]
        assert "sdv.com.mx" not in item["official_url"]
        parsed = urlparse(item["official_url"])
        assert parsed.scheme == "https"
        assert parsed.netloc



def test_coverage_map_and_documentation_indexes_expose_the_catalog() -> None:
    coverage_map = MAP_PATH.read_text(encoding="utf-8")
    docs_index = DOCS_INDEX_PATH.read_text(encoding="utf-8")
    root_readme = ROOT_README_PATH.read_text(encoding="utf-8")

    assert "# Mapa de cobertura oficial de comercio exterior" in coverage_map
    assert "No es un simulador de costos" in coverage_map
    assert "external-trade-source-catalog.json" in coverage_map
    assert "Mapa de cobertura de comercio exterior" in docs_index
    assert "Mapa de cobertura oficial de comercio exterior" in root_readme
