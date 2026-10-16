from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_vercel_promotes_api_discovery_and_keeps_robots_outside_the_spa_rewrite() -> None:
    config = json.loads((ROOT / "vercel.json").read_text(encoding="utf-8"))
    rewrites = config["rewrites"]

    assert {"source": "/v1", "destination": "/api/operational?resource=api"} in rewrites
    assert "robots\\.txt$" in rewrites[-1]["source"]
    assert (ROOT / "website" / "robots.txt").read_text(encoding="utf-8") == "User-agent: *\nAllow: /\n"


def test_vercel_serves_the_static_data_api_from_github_pages() -> None:
    config = json.loads((ROOT / "vercel.json").read_text(encoding="utf-8"))
    rewrites = config["rewrites"]

    data = {
        "source": "/data/v1/:path*",
        "destination": "https://jccontrerasg08-cpu.github.io/arancel-mx/v1/:path*",
    }
    assert data in rewrites
    assert rewrites.index(data) < len(rewrites) - 1, "must precede the SPA catch-all"
    assert "data/" in rewrites[-1]["source"]


def test_vercel_v1_announces_its_deprecation_and_successor() -> None:
    config = json.loads((ROOT / "vercel.json").read_text(encoding="utf-8"))
    v1 = next(rule for rule in config["headers"] if rule["source"] == "/v1(.*)")
    headers = {item["key"]: item["value"] for item in v1["headers"]}

    assert headers["Deprecation"] == "@1792108800"
    assert headers["Sunset"] == "Sun, 31 Jan 2027 00:00:00 GMT"
    assert 'rel="successor-version"' in headers["Link"]
    assert "github.io/arancel-mx/v1/manifest.json" in headers["Link"]
