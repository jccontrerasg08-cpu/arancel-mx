from __future__ import annotations

import re
import xml.etree.ElementTree as ET
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
README_MAX_CHARS = 10_000
PUBLIC_HUB_URL = "https://arancel-mx.vercel.app/"

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
    """Read a tracked presentation file as UTF-8 text."""
    return (ROOT / path).read_text(encoding="utf-8")


def _markdown_links(path: str) -> list[str]:
    """Return complete Markdown link targets from one tracked document."""
    return re.findall(r"\[[^\]]+\]\(([^)]+)\)", _read(path))


def _local_markdown_targets(path: str) -> list[Path]:
    """Return local Markdown targets referenced by one Markdown document."""
    source_dir = (ROOT / path).parent
    targets: list[Path] = []
    for target in _markdown_links(path):
        if target.startswith(("http://", "https://", "#", "mailto:")):
            continue
        clean_target = target.split("#", 1)[0]
        if clean_target.endswith(".md"):
            targets.append((source_dir / clean_target).resolve())
    return targets


def test_brand_assets_are_accessible_vector_svgs_without_embedded_raster() -> None:
    """Require accessible vector-only SVG masters with no raster escape hatch."""
    forbidden = ("data:image", "base64,", ".png", ".jpg", ".jpeg")
    for relative_path in BRAND_ASSETS:
        path = ROOT / relative_path
        assert path.is_file(), f"missing brand asset: {relative_path}"
        text = path.read_text(encoding="utf-8")
        # These are trusted, version-controlled project assets, never user-supplied XML.
        root = ET.fromstring(text)  # noqa: S314
        assert root.tag.endswith("svg")
        assert root.attrib.get("viewBox"), f"missing viewBox: {relative_path}"
        tags = {element.tag.rsplit("}", 1)[-1] for element in root.iter()}
        assert "title" in tags, f"missing title: {relative_path}"
        assert "desc" in tags, f"missing desc: {relative_path}"
        assert "image" not in tags, f"embedded image element: {relative_path}"
        lowered = text.lower()
        assert not any(token in lowered for token in forbidden), relative_path


def test_readmes_are_compact_landing_pages_with_matching_user_routes() -> None:
    """Keep both repository front pages short, symmetrical and action-oriented."""
    spanish = _read("README.md")
    english = _read("README.en.md")

    assert len(spanish) <= README_MAX_CHARS
    assert len(english) <= README_MAX_CHARS

    for phrase in (
        "## Qué puedes hacer",
        "## Empieza en 60 segundos",
        "## Por qué confiar",
        "## Documentación",
        "## Alcance",
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
        "## What you can do",
        "## Start in 60 seconds",
        "## Why trust it",
        "## Documentation",
        "## Scope",
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

    assert PUBLIC_HUB_URL in _markdown_links("README.md")
    assert PUBLIC_HUB_URL in _markdown_links("README.en.md")
    assert spanish.count("\n## ") <= 7
    assert english.count("\n## ") <= 7
    assert "docs/assets/arancel-mx-banner.svg" in spanish
    assert "docs/assets/arancel-mx-banner.svg" in english


def test_documentation_hub_routes_by_intent_and_keeps_specialized_research_off_root() -> None:
    """Make docs/ the canonical deep-navigation layer instead of the root README."""
    docs_index = _read("docs/README.md")

    for heading in (
        "## Usar",
        "## Integrar",
        "## Entender y verificar",
        "## Mantener y contribuir",
        "## Proyecto y presentación",
    ):
        assert heading in docs_index

    assert PUBLIC_HUB_URL in _markdown_links("docs/README.md")
    assert "research/anam-moa-source-map.md" in docs_index
    assert not (ROOT / "ANAM_MOA_SOURCE_MAP.md").exists()
    assert (ROOT / "docs/research/anam-moa-source-map.md").is_file()


def test_repository_front_door_markdown_links_resolve_locally() -> None:
    """Keep README and docs-hub links valid after documentation moves."""
    for source in ("README.md", "README.en.md", "docs/README.md"):
        targets = _local_markdown_targets(source)
        assert targets, f"expected local documentation links in {source}"
        missing = [target for target in targets if not target.exists()]
        assert not missing, f"broken local Markdown links in {source}: {missing}"


def test_consumer_docs_use_vercel_as_the_public_http_front_door() -> None:
    """Keep consumer guidance aligned with the deployed Vercel/FastAPI hybrid surface."""
    quickstart = _read("docs/consumer-quickstart.md")
    external = _read("docs/external-consumption.md")

    assert PUBLIC_HUB_URL in _markdown_links("docs/consumer-quickstart.md")
    assert PUBLIC_HUB_URL in _markdown_links("docs/external-consumption.md")
    for document in (quickstart, external):
        assert "/v1/meta" in document
        assert "/readyz" in document
        assert "/docs" in document

    api_url_match = re.search(r'export ARANCEL_MX_API_URL="([^"]+)"', external)
    assert api_url_match is not None
    assert api_url_match.group(1) == PUBLIC_HUB_URL.rstrip("/")
    assert "Vercel" in external
    assert "Neon" in external
    assert "proxy" in external.lower()
    assert "el sitio no actúa como proxy" not in external.lower()


def test_public_docs_keep_readyz_on_the_operational_surface() -> None:
    """Prevent public docs from describing readiness as a FastAPI proxy route."""
    stale_fragments = (
        "Vercel: /v1/* restante + /docs + /readyz",
        "las demás rutas `/v1/*`, `/docs` y `/readyz`",
        "las demás rutas `/v1/*`, `/docs` y `/readyz` se presentan",
    )
    for path in (
        "docs/project-overview.md",
        "docs/consumer-quickstart.md",
        "docs/external-consumption.md",
        "docs/brand.md",
    ):
        text = _read(path)
        assert "/readyz" in text, path
        assert "operacional" in text.lower(), path
        assert not any(fragment in text for fragment in stale_fragments), path

    for path in ("docs/project-overview.md", "docs/external-consumption.md"):
        text = _read(path)
        assert "Vercel: /v1/meta + /v1/search + /readyz" in text
        assert "Vercel: /v1/* restante + /docs" in text


def test_public_brand_guide_is_discoverable_and_uses_current_schedule_language() -> None:
    """Expose the canonical brand guide and current weekly automation wording."""
    guide_path = ROOT / "docs/brand.md"
    assert guide_path.is_file()
    guide = guide_path.read_text(encoding="utf-8")
    docs_index = _read("docs/README.md")

    for phrase in (
        "# Marca y presentación de `arancel-mx`",
        "arancel-mx-logo.svg",
        "arancel-mx-mark.svg",
        "arancel-mx-social.svg",
        "arancel-mx-cover.svg",
        "#102A43",
        "#008A5B",
        "#CE1126",
        "Traceable. Auditable. Reproducible.",
    ):
        assert phrase in guide

    assert "[Marca y presentación](brand.md)" in docs_index
    assert "pipeline semanal" in docs_index.lower()
    assert "pipeline diario" not in docs_index.lower()


def test_public_site_keeps_original_landing_and_stable_brand_boundary() -> None:
    """Keep the generated landing intact while branding only the project-owned shell."""
    index = _read("website/index.html")

    for fragment in (
        "/assets/arancel-mx-mark.svg",
        "/assets/arancel-mx-logo.svg",
        "/assets/site-brand.css?v=",
        "/assets/site-bridge.js?v=",
    ):
        assert fragment in index

    assert 'class="arancel-brand-header"' in index
    assert "/assets/hub-search.css" not in index
    assert "/assets/hub-search.js" not in index
    assert "manus-analytics.com" not in index

    assert (ROOT / "website/assets/arancel-mx-logo.svg").is_file()
    assert (ROOT / "website/assets/arancel-mx-social.svg").is_file()


def test_brand_css_uses_stable_asset_selectors_not_generated_bundle_classes() -> None:
    """Keep brand CSS independent from generated or minified application classes."""
    styles = _read("website/assets/site-brand.css")
    assert "/assets/arancel-mx-mark.svg" in styles
    assert "/assets/arancel-mx-logo.svg" in styles
    assert ".arancel-brand-header" in styles
    assert "index-" not in styles


def test_integration_handoff_tracks_current_vercel_and_liveness_boundaries() -> None:
    """Keep the handoff synchronized with the current main architecture."""
    handoff = _read("docs/integration-handoff.md")
    lowered = handoff.lower()
    assert "operational" in lowered
    assert "neon" in lowered
    assert "proxy" in lowered
    assert "/v1/meta" in handoff
    assert "/readyz" in handoff
    assert "e861aed" in handoff
    assert "Vercel: /v1/meta + /v1/search + /readyz" in handoff
    assert "ARANCEL_MX_DATABASE_DATABASE_URL" in handoff
    assert "api/_vendor" in handoff
    assert "python3.13" in handoff
    assert "psycopg[binary]>=3.3.4" in handoff
    assert "requirements.txt" in handoff
    assert "EXTERNALLY_UNPROBEABLE_URLS" in handoff
    assert "site-bridge.js" in handoff
    assert ".release-window code" in handoff
    assert "installCommand" not in handoff
