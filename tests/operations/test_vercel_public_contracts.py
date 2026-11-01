from __future__ import annotations

import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_vercel_promotes_api_discovery_and_keeps_robots_outside_the_spa_rewrite() -> None:
    config = json.loads((ROOT / "vercel.json").read_text(encoding="utf-8"))
    rewrites = config["rewrites"]

    assert {"source": "/v1", "destination": "/api/operational?resource=api"} in rewrites
    assert not re.fullmatch(rewrites[-1]["source"], "/robots.txt"), "robots.txt must stay outside the SPA rewrite"
    assert (ROOT / "src" / "arancel_mx" / "api" / "static" / "site" / "robots.txt").read_text(encoding="utf-8") == "User-agent: *\nAllow: /\n"


def test_vercel_serves_the_static_data_api_from_github_pages() -> None:
    config = json.loads((ROOT / "vercel.json").read_text(encoding="utf-8"))
    rewrites = config["rewrites"]

    data = {
        "source": "/data/v1/:path*",
        "destination": "https://jccontrerasg08-cpu.github.io/arancel-mx/v1/:path*",
    }
    assert data in rewrites
    assert rewrites.index(data) < len(rewrites) - 1, "must precede the SPA catch-all"
    assert re.fullmatch(rewrites[-1]["source"], "/data"), "the figures page is a SPA route"
    assert not re.fullmatch(rewrites[-1]["source"], "/data/v1/meta.json")


def test_vercel_v1_announces_its_deprecation_and_successor() -> None:
    config = json.loads((ROOT / "vercel.json").read_text(encoding="utf-8"))
    v1 = next(rule for rule in config["headers"] if rule["source"] == "/v1(.*)")
    headers = {item["key"]: item["value"] for item in v1["headers"]}

    assert headers["Deprecation"] == "@1792108800"
    assert headers["Sunset"] == "Sun, 31 Jan 2027 00:00:00 GMT"
    assert 'rel="successor-version"' in headers["Link"]
    assert "github.io/arancel-mx/v1/manifest.json" in headers["Link"]


def test_vercel_serves_a_real_404_for_paths_that_are_not_site_routes() -> None:
    config = json.loads((ROOT / "vercel.json").read_text(encoding="utf-8"))
    spa = re.compile(config["rewrites"][-1]["source"])
    app_source = (ROOT / "src" / "arancel_mx" / "api" / "app.py").read_text(encoding="utf-8")
    pages = re.findall(r'^    "(/[^"]*)",$', app_source.split("_MARKETING_PAGES = (", 1)[1].split(")", 1)[0], re.MULTILINE)

    assert "/documentation" in pages
    for page in (page for page in pages if page != "/"):
        assert spa.fullmatch(page), f"{page} is a public route and must reach the SPA"
    for path in ("/app", "/app/record/8517", "/app/chapter/85", "/changes/tarifa15", "/product"):
        assert spa.fullmatch(path), f"{path} is a client route and must reach the SPA"
    for path in ("/no-such-page", "/wp-admin", "/app2", "/records/extra", "/assets/missing.js", "/robots.txt"):
        assert not spa.fullmatch(path), f"{path} must answer 404"
    not_found = ROOT / "src" / "arancel_mx" / "api" / "static" / "site" / "404.html"
    assert 'name="robots" content="noindex"' in not_found.read_text(encoding="utf-8")
