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
    "src/arancel_mx/api/static/site/assets/arancel-mx-mark.svg",
    "src/arancel_mx/api/static/site/assets/arancel-mx-logo.svg",
    "src/arancel_mx/api/static/site/assets/arancel-mx-social.svg",
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


def test_consumer_docs_use_the_static_data_api_as_the_public_http_front_door() -> None:
    """Keep consumer guidance aligned with decision 0002: Pages data behind the Vercel hub."""
    quickstart = _read("docs/consumer-quickstart.md")
    external = _read("docs/external-consumption.md")

    assert PUBLIC_HUB_URL in _markdown_links("docs/consumer-quickstart.md")
    assert PUBLIC_HUB_URL in _markdown_links("docs/external-consumption.md")
    for document in (quickstart, external):
        assert "/data/v1/meta.json" in document
        assert "/data/v1/records/85.json" in document
        assert "/documentation" in document
        assert "uvicorn arancel_mx.api.app:app" in document
        assert "operations/v1-sunset.md" in document

    api_url_match = re.search(r'export ARANCEL_MX_API_URL="([^"]+)"', external)
    assert api_url_match is not None
    assert api_url_match.group(1) == PUBLIC_HUB_URL.rstrip("/")
    assert "GitHub Pages" in external
    assert "el sitio no actúa como proxy" in external.lower()


def test_public_docs_describe_only_the_current_serving_architecture() -> None:
    """Deprecated serving layers belong in the sunset runbook, not in the overview docs."""
    for path in (
        "docs/project-overview.md",
        "docs/consumer-quickstart.md",
        "docs/brand.md",
        "README.md",
        "README.en.md",
        "docs/README.md",
    ):
        text = _read(path)
        assert "Neon" not in text, path
        assert "capa operacional" not in text.lower(), path
        assert "/data/v1" in text, path

    overview = _read("docs/project-overview.md")
    assert "GitHub Pages" in overview
    assert "runtime FastAPI" not in overview


def test_public_brand_guide_is_discoverable_and_uses_current_schedule_language() -> None:
    """Expose the canonical brand guide and current daily automation wording."""
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
    assert "pipeline diario" in docs_index.lower()
    assert "pipeline semanal" not in docs_index.lower()


def test_vercel_static_output_serves_the_react_public_shell() -> None:
    """Keep Vercel's published static output aligned with the React public shell."""
    index = _read("src/arancel_mx/api/static/site/index.html")

    for fragment in (
        '<div id="root"></div>',
        "/assets/index-",
        'type="module"',
    ):
        assert fragment in index

    assert "/assets/hub-search.css" not in index
    assert "/assets/hub-search.js" not in index
    assert "manus-analytics.com" not in index

    assert (ROOT / "src/arancel_mx/api/static/site/assets/arancel-mx-logo.svg").is_file()
    assert (ROOT / "src/arancel_mx/api/static/site/assets/arancel-mx-social.svg").is_file()


def test_brand_css_uses_stable_asset_selectors_not_generated_bundle_classes() -> None:
    """Keep brand CSS independent from generated or minified application classes."""
    styles = _read("src/arancel_mx/api/static/site/assets/site-brand.css")
    assert "/assets/arancel-mx-mark.svg" in styles
    assert "/assets/arancel-mx-logo.svg" in styles
    assert ".arancel-brand-header" in styles
    assert "index-" not in styles


def test_v1_sunset_runbook_tracks_the_remaining_vercel_runtime() -> None:
    """Keep the deprecated runtime documented until it is removed."""
    runbook = _read("docs/operations/v1-sunset.md")
    for fragment in (
        "Neon",
        "/v1/meta",
        "/readyz",
        "Vercel: metadatos, búsqueda, ficha y evidencia activa",
        "ARANCEL_MX_DATABASE_DATABASE_URL",
        "api/_vendor",
        "api/_runtime.py",
        "python3.13",
        "requirements/vercel.txt",
        "--require-hashes",
        "requirements.txt",
        "maxDuration",
    ):
        assert fragment in runbook, fragment
    assert "installCommand" not in runbook


def test_architecture_doc_records_frontend_cache_and_bridge_boundaries() -> None:
    """Keep the stable-asset and bridge contracts in the canonical architecture doc."""
    architecture = _read("docs/architecture.md")
    for fragment in ("site-bridge.js", ".release-window code", "must-revalidate", "immutable", "gh-pages"):
        assert fragment in architecture, fragment
