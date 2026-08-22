from __future__ import annotations

import json
from pathlib import Path
import re
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[1]


def test_vercel_deploys_the_standalone_public_site() -> None:
    config = json.loads((ROOT / "vercel.json").read_text(encoding="utf-8"))
    runtime_version = (ROOT / ".python-version").read_text(encoding="utf-8").strip()

    assert config["framework"] is None
    assert config["outputDirectory"] == "website"
    assert "installCommand" not in config
    assert config["buildCommand"].startswith(f"python{runtime_version} -m pip install ")
    assert config["rewrites"] == [
        {
            "source": "/healthz",
            "destination": "/api/operational?resource=health",
        },
        {
            "source": "/v1/meta",
            "destination": "/api/operational?resource=meta",
        },
        {
            "source": "/v1/search",
            "destination": "/api/operational?resource=search",
        },
        {
            "source": "/v1/suggest",
            "destination": "/api/operational?resource=suggest",
        },
        {
            "source": "/v1/ficha/:code",
            "destination": "/api/operational?resource=ficha&code=:code",
        },
        {
            "source": "/v1/lookup/:code",
            "destination": "/api/operational?resource=lookup&code=:code",
        },
        {
            "source": "/v1/sections",
            "destination": "/api/operational?resource=sections",
        },
        {
            "source": "/v1/chapters",
            "destination": "/api/operational?resource=chapters",
        },
        {
            "source": "/v1/codes/:code/parent",
            "destination": "/api/operational?resource=parent&code=:code",
        },
        {
            "source": "/v1/codes/:code/children",
            "destination": "/api/operational?resource=children&code=:code",
        },
        {
            "source": "/v1/codes/:code/provenance",
            "destination": "/api/operational?resource=provenance&code=:code",
        },
        {
            "source": "/v1/chapters/:chapter/national-notes",
            "destination": "/api/operational?resource=national-notes&chapter=:chapter",
        },
        {
            "source": "/readyz",
            "destination": "/api/operational?resource=ready",
        },
        {"source": "/trade", "destination": "/trade.html"},
        {"source": "/((?!assets/|api/|v1/|v1$|docs/|docs$|openapi\\.json$).*)", "destination": "/"},
    ]
    assert config["redirects"] == [
        {"source": "/docs", "destination": "/documentation", "permanent": True},
        {"source": "/docs/:path*", "destination": "/documentation", "permanent": True},
    ]
    assert "fastapicloud.dev" not in json.dumps(config)


def test_vercel_functions_bundle_the_src_layout_with_bounded_runtime() -> None:
    config = json.loads((ROOT / "vercel.json").read_text(encoding="utf-8"))

    assert config["functions"] == {
        "api/operational.py": {
            "includeFiles": "{api/_vendor/**,src/arancel_mx/**}",
            "maxDuration": 30,
        },
        "api/sync_operational.py": {
            "includeFiles": "{api/_vendor/**,src/arancel_mx/**}",
            "maxDuration": 60,
        },
    }


def test_vercel_cache_policy_only_marks_hashed_bundles_immutable() -> None:
    config = json.loads((ROOT / "vercel.json").read_text(encoding="utf-8"))

    cache_rules = [rule for rule in config["headers"] if rule["source"] != "/(.*)"]
    assert cache_rules == [
        {
            "source": "/assets/index-(.*)",
            "headers": [
                {
                    "key": "Cache-Control",
                    "value": "public, max-age=31536000, immutable",
                }
            ],
        },
        {
            "source": "/assets/((?!index-).*)",
            "headers": [
                {
                    "key": "Cache-Control",
                    "value": "public, max-age=0, must-revalidate",
                }
            ],
        },
    ]


def test_vercel_runtime_bootstrap_adds_the_src_layout_first() -> None:
    probe = subprocess.run(
        [
            sys.executable,
            "-S",
            "-c",
            (
                "from api._runtime import ensure_project_source; "
                "ensure_project_source(); "
                "from pathlib import Path; import sys; "
                "assert Path(sys.path[0]).resolve() == (Path.cwd() / 'src').resolve()"
            ),
        ],
        cwd=ROOT,
        capture_output=True,
        text=True,
        check=False,
    )

    assert probe.returncode == 0, probe.stderr


def test_public_site_serves_the_react_shell_with_canonical_brand_assets() -> None:
    index = (ROOT / "website" / "index.html").read_text(encoding="utf-8")
    logo = (ROOT / "website" / "assets" / "arancel-mx-logo.svg").read_text(encoding="utf-8")

    assert (ROOT / "website" / "assets" / "arancel-mx-mark.svg").is_file()
    assert (ROOT / "website" / "assets" / "arancel-mx-logo.svg").is_file()
    assert '<div id="root"></div>' in index
    match = re.search(r'/assets/(index-[a-f0-9]{12}\.js)', index)
    assert match is not None
    assert (ROOT / "website" / "assets" / match.group(1)).is_file()
    assert 'type="module"' in index

    assert "/assets/hub-search.css" not in index
    assert "/assets/hub-search.js" not in index
    assert "data-arancel-hub-search" not in index
    assert "/assets/site-brand.css" in index
    assert "/assets/site-bridge.js" in index
    assert "/assets/hub-interactions.js" in index
    assert "const legacyRoute" in index
    assert index.index("const legacyRoute") < index.index('type="module"')

    assert "manus-runtime" not in index
    assert "/__manus__/debug-collector.js" not in index
    assert "manus-analytics.com" not in index

    # The approved identity is dimensional rather than the previous flat
    # approximation, so keep gradient/shadow primitives in the vector master.
    assert "linearGradient" in logo
    assert "filter" in logo


def test_public_site_interactions_link_results_to_verified_record_data() -> None:
    interactions = (ROOT / "website" / "assets" / "hub-interactions.js").read_text(encoding="utf-8")

    assert "Inspect verified record" in interactions
    assert "/v1/lookup/" in interactions
    assert "/v1/codes/" in interactions
    assert "displayValue" in interactions
    assert "unit_name" in interactions
    assert "data-arancel-record-panel" in interactions


def test_public_site_does_not_declare_a_vercel_fastapi_entrypoint() -> None:
    project = (ROOT / "pyproject.toml").read_text(encoding="utf-8")

    assert "[tool.vercel]" not in project
    assert "[tool.fastapi]" in project


def test_public_site_bridge_keeps_current_release_and_route_aliases() -> None:
    bridge = (ROOT / "website" / "assets" / "site-bridge.js").read_text(encoding="utf-8")

    assert "fetch('/v1/meta'" in bridge
    assert "['/moa-guide', '/moa']" in bridge
    assert "['/product', '/app']" in bridge
    assert ".release-window code" in bridge
    assert r"data-\d{4}" in bridge
    assert "document.addEventListener('DOMContentLoaded'" in bridge
    assert "new MutationObserver(applyPublicSiteBridge)" not in bridge
    assert "window.setInterval" in bridge
    assert "attempts >= 12" in bridge
    assert "currentReleasePattern" not in bridge
    assert "node.nodeValue.replace(currentReleasePattern" not in bridge


def test_vercel_centralization_docs_match_the_promoted_retrieval_routes() -> None:
    """Keep documented ownership aligned with the Vercel rewrite contract."""

    centralization = (ROOT / "docs" / "vercel-centralization.md").read_text(encoding="utf-8")

    assert "| `ficha`, suggest, provenance, and national notes | Vercel operational function | Active Neon release |" in centralization
    assert "| `/documentation` | Local React documentation hub | Public repository documents and route limits |" in centralization
    assert "fastapicloud.dev" not in centralization
    assert "Temporary FastAPI compatibility route" not in centralization


def test_trade_desk_publishes_a_visual_source_atlas_with_accessible_flags() -> None:
    trade = (ROOT / "website" / "trade.html").read_text(encoding="utf-8")
    style = (ROOT / "website" / "assets" / "trade-desk.css").read_text(encoding="utf-8")

    assert 'data-testid="trade-visual-atlas"' in trade
    assert 'data-testid="trade-partner-flags"' in trade
    assert 'src="/assets/flags/mx.svg"' in trade
    assert 'src="/assets/flags/us.svg"' in trade
    assert 'src="/assets/flags/ca.svg"' in trade
    assert 'alt="Bandera de México"' in trade
    assert 'alt="Bandera de Estados Unidos"' in trade
    assert 'alt="Bandera de Canadá"' in trade
    assert 'visuals/trade-route-atlas.jpg' in style
    assert 'visuals/evidence-ledger.jpg' in trade

    for relative_path in (
        "assets/visuals/trade-route-atlas.jpg",
        "assets/visuals/evidence-ledger.jpg",
        "assets/flags/mx.svg",
        "assets/flags/us.svg",
        "assets/flags/ca.svg",
        "assets/flags/NOTICE",
    ):
        website_asset = ROOT / "website" / relative_path
        static_asset = ROOT / "src" / "arancel_mx" / "api" / "static" / "site" / relative_path
        assert website_asset.is_file()
        assert static_asset.is_file()
        assert website_asset.read_bytes() == static_asset.read_bytes()


def test_visual_atlas_docs_do_not_claim_unimplemented_flag_attributes() -> None:
    atlas = (ROOT / "docs" / "visual-atlas.md").read_text(encoding="utf-8")

    assert "`srcset`" not in atlas
    assert "`alt` específico por país, `src` explícito y dimensiones reservadas" in atlas


def test_vercel_applies_safe_defensive_headers_to_public_documents() -> None:
    config = json.loads((ROOT / "vercel.json").read_text(encoding="utf-8"))
    document_headers = next(rule["headers"] for rule in config["headers"] if rule["source"] == "/(.*)")
    values = {header["key"]: header["value"] for header in document_headers}

    assert values["X-Content-Type-Options"] == "nosniff"
    assert values["Referrer-Policy"] == "strict-origin-when-cross-origin"
    assert values["Permissions-Policy"] == "geolocation=(), microphone=(), camera=()"
    assert values["X-Frame-Options"] == "DENY"


def test_maintained_architecture_docs_describe_the_local_public_surface() -> None:
    for relative_path in (
        "docs/project-overview.md",
        "docs/integration-handoff.md",
        "docs/brand.md",
        "docs/consumer-quickstart.md",
    ):
        text = (ROOT / relative_path).read_text(encoding="utf-8")

        assert "/documentation" in text
        assert "runtime FastAPI" not in text
        assert "FastAPI reusable" not in text
        assert "fastapicloud.dev" not in text
