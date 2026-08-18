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


def test_public_site_contains_its_logo_and_route_bridge() -> None:
    index = (ROOT / "website" / "index.html").read_text(encoding="utf-8")
    bridge = (ROOT / "website" / "assets" / "site-bridge.js").read_text(encoding="utf-8")

    assert (ROOT / "website" / "assets" / "arancel-mx-mark.svg").is_file()
    assert "/assets/arancel-mx-mark.svg" in index
    assert "/assets/site-bridge.js?v=" in index
    assert "/assets/hub-search.css" in index
    assert "/assets/hub-search.js" in index
    assert "id=\"root\"" in index
    assert "manus-runtime" not in index
    assert "/__manus__/debug-collector.js" not in index
    assert "consumer-quickstart.md" in bridge
    assert "fetch('/v1/meta'" in bridge
    assert "synchronizeDisplayedRelease" in bridge
    assert "updateDisplayedRelease" in bridge
    assert "let activeDatasetTag" in bridge

    search = (ROOT / "website" / "assets" / "hub-search.js").read_text(encoding="utf-8")
    styles = (ROOT / "website" / "assets" / "hub-search.css").read_text(encoding="utf-8")
    assert "fetch(\"/v1/meta\")" in search
    assert "release_published_at" in search
    assert "fetch(`/v1/search?q=${encodeURIComponent(query)}&limit=8`)" in search
    assert "Datos verificados" in search
    assert "Búsqueda arancelaria" in search
    assert "hub-search" in styles


def test_public_site_does_not_declare_a_vercel_fastapi_entrypoint() -> None:
    project = (ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert "[tool.vercel]" not in project
    assert "[tool.fastapi]" in project
