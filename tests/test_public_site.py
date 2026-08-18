from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]


def test_vercel_deploys_the_standalone_public_site() -> None:
    config = json.loads((ROOT / "vercel.json").read_text(encoding="utf-8"))

    assert config["framework"] is None
    assert config["outputDirectory"] == "website"
    assert config["rewrites"] == [{"source": "/(.*)", "destination": "/"}]


def test_public_site_contains_its_logo_and_route_bridge() -> None:
    index = (ROOT / "website" / "index.html").read_text(encoding="utf-8")
    bridge = (ROOT / "website" / "assets" / "site-bridge.js").read_text(encoding="utf-8")

    assert (ROOT / "website" / "assets" / "arancel-mx-mark.svg").is_file()
    assert "/assets/arancel-mx-mark.svg" in index
    assert "/assets/site-bridge.js" in index
    assert "consumer-quickstart.md" in bridge


def test_public_site_does_not_declare_a_vercel_fastapi_entrypoint() -> None:
    project = (ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert "[tool.vercel]" not in project
    assert "[tool.fastapi]" in project
