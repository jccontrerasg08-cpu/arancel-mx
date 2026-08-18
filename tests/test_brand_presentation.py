from __future__ import annotations

import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]

BRAND_ASSETS = (
    "docs/assets/arancel-mx-logo.svg",
    "docs/assets/arancel-mx-banner.svg",
    "docs/assets/arancel-mx-social.svg",
    "docs/assets/arancel-mx-cover.svg",
    "website/assets/arancel-mx-mark.svg",
    "website/assets/arancel-mx-logo.svg",
    "website/assets/arancel-mx-social.svg",
)


def _read(path: str) -> str:
    return (ROOT / path).read_text(encoding="utf-8")


def test_brand_assets_are_accessible_vector_svgs_without_embedded_raster() -> None:
    forbidden = ("data:image", "base64,", ".png", ".jpg", ".jpeg")
    for relative_path in BRAND_ASSETS:
        path = ROOT / relative_path
        assert path.is_file(), f"missing brand asset: {relative_path}"
        text = path.read_text(encoding="utf-8")
        root = ET.fromstring(text)
        assert root.tag.endswith("svg")
        assert root.attrib.get("viewBox"), f"missing viewBox: {relative_path}"
        tags = {element.tag.rsplit("}", 1)[-1] for element in root.iter()}
        assert "title" in tags, f"missing title: {relative_path}"
        assert "desc" in tags, f"missing desc: {relative_path}"
        lowered = text.lower()
        assert not any(token in lowered for token in forbidden), relative_path


def test_readmes_lead_with_product_story_and_five_consumption_surfaces() -> None:
    spanish = _read("README.md")
    english = _read("README.en.md")

    for phrase in (
        "Por qué existe",
        "Elige cómo usarlo",
        "Datos / DuckDB",
        "CLI",
        "Python",
        "HTTP / API",
        "Auditoría y reproducción",
        "pip install arancel-mx",
        "arancel-mx data download",
        "arancel-mx lookup 01012101",
        "data-YYYY.MM.DD",
    ):
        assert phrase in spanish

    for phrase in (
        "Why it exists",
        "Choose how to use it",
        "Data / DuckDB",
        "CLI",
        "Python",
        "HTTP / API",
        "Audit and reproduction",
        "pip install arancel-mx",
        "arancel-mx data download",
        "arancel-mx lookup 01012101",
        "data-YYYY.MM.DD",
    ):
        assert phrase in english

    assert "docs/assets/arancel-mx-banner.svg" in spanish
    assert "docs/assets/arancel-mx-banner.svg" in english


def test_public_site_keeps_hub_assets_and_stable_brand_boundary() -> None:
    index = _read("website/index.html")

    for fragment in (
        "/assets/arancel-mx-mark.svg",
        "/assets/site-brand.css",
        "/assets/hub-search.css",
        "/assets/site-bridge.js",
        "/assets/hub-search.js",
    ):
        assert fragment in index

    assert (ROOT / "website/assets/arancel-mx-logo.svg").is_file()
    assert (ROOT / "website/assets/arancel-mx-social.svg").is_file()


def test_brand_css_uses_stable_asset_selectors_not_generated_bundle_classes() -> None:
    styles = _read("website/assets/site-brand.css")
    assert "/assets/arancel-mx-mark.svg" in styles
    assert "/assets/arancel-mx-logo.svg" in styles
    assert "index-" not in styles


def test_integration_handoff_describes_post_132_hub_boundary() -> None:
    handoff = _read("docs/integration-handoff.md")
    lowered = handoff.lower()
    assert "operational" in lowered
    assert "neon" in lowered
    assert "proxy" in lowered
    assert "/v1/meta" in handoff
    assert "fb727ac" in handoff
