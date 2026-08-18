from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_vercel_deploys_the_standalone_public_site() -> None:
    config = json.loads((ROOT / "vercel.json").read_text(encoding="utf-8"))

    assert config["framework"] is None
    assert config["outputDirectory"] == "website"
    assert "installCommand" not in config
    assert config["rewrites"] == [
        {
            "source": "/v1/meta",
            "destination": "/api/operational?resource=meta",
        },
        {
            "source": "/v1/search",
            "destination": "/api/operational?resource=search",
        },
        {
            "source": "/v1/:path*",
            "destination": "https://arancel-mx.fastapicloud.dev/v1/:path*",
        },
        {
            "source": "/openapi.json",
            "destination": "https://arancel-mx.fastapicloud.dev/openapi.json",
        },
        {
            "source": "/docs/:path*",
            "destination": "https://arancel-mx.fastapicloud.dev/docs/:path*",
        },
        {
            "source": "/docs",
            "destination": "https://arancel-mx.fastapicloud.dev/docs",
        },
        {
            "source": "/readyz",
            "destination": "/api/operational?resource=ready",
        },
        {"source": "/(.*)", "destination": "/"},
    ]


def test_public_site_preserves_the_original_landing_with_canonical_branding() -> None:
    index = (ROOT / "website" / "index.html").read_text(encoding="utf-8")
    bridge = (ROOT / "website" / "assets" / "site-bridge.js").read_text(encoding="utf-8")
    styles = (ROOT / "website" / "assets" / "site-brand.css").read_text(encoding="utf-8")
    logo = (ROOT / "website" / "assets" / "arancel-mx-logo.svg").read_text(encoding="utf-8")

    assert (ROOT / "website" / "assets" / "arancel-mx-mark.svg").is_file()
    assert (ROOT / "website" / "assets" / "arancel-mx-logo.svg").is_file()
    assert "/assets/arancel-mx-mark.svg" in index
    assert "/assets/arancel-mx-logo.svg" in index
    assert 'class="arancel-brand-header"' in index
    assert 'id="root"' in index

    # The original application owns the landing layout. Do not prepend a second
    # search application in front of it; /v1/search remains available as an API.
    assert "/assets/hub-search.css" not in index
    assert "/assets/hub-search.js" not in index
    assert "data-arancel-hub-search" not in index

    # Keep the public shell project-owned and free from the former generator's
    # runtime/analytics scripts.
    assert "manus-runtime" not in index
    assert "/__manus__/debug-collector.js" not in index
    assert "manus-analytics.com" not in index

    assert "/assets/site-bridge.js?v=" in index
    assert "consumer-quickstart.md" in bridge
    assert "fetch('/v1/meta'" in bridge
    assert "synchronizeDisplayedRelease" in bridge
    assert "updateDisplayedRelease" in bridge
    assert "let activeDatasetTag" in bridge
    assert "querySelectorAll('.release-window code')" in bridge

    assert ".arancel-brand-header" in styles
    assert "/assets/arancel-mx-logo.svg" in styles
    assert "index-" not in styles

    # The approved identity is dimensional rather than the previous flat
    # approximation, so keep gradient/shadow primitives in the vector master.
    assert "linearGradient" in logo
    assert "filter" in logo


def test_public_site_does_not_declare_a_vercel_fastapi_entrypoint() -> None:
    project = (ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert "[tool.vercel]" not in project
    assert "[tool.fastapi]" in project
