from __future__ import annotations

import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]


def test_vercel_declares_a_weekly_private_operational_sync_cron() -> None:
    config = json.loads((ROOT / "vercel.json").read_text(encoding="utf-8"))
    handler = (ROOT / "api" / "sync_operational.py").read_text(encoding="utf-8")

    assert config["crons"] == [{"path": "/api/sync_operational", "schedule": "30 12 * * 1"}]
    assert "operational_database_url" in handler
    assert 'os.environ.get("CRON_SECRET")' in handler
    assert "synchronize_latest_release" in handler
    assert "HTTPStatus.UNAUTHORIZED" in handler


def test_vercel_bundles_the_operational_driver_only_for_operational_functions() -> None:
    config = json.loads((ROOT / "vercel.json").read_text(encoding="utf-8"))
    read_handler = (ROOT / "api" / "operational.py").read_text(encoding="utf-8")
    sync_handler = (ROOT / "api" / "sync_operational.py").read_text(encoding="utf-8")

    assert config["buildCommand"] == "python3.13 -m pip install --target api/_vendor 'psycopg[binary]>=3.3.4'"
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
    assert not (ROOT / "requirements.txt").exists()
    assert 'Path(__file__).with_name("_vendor")' in read_handler
    assert 'Path(__file__).with_name("_vendor")' in sync_handler


def test_vercel_routes_retrieval_and_evidence_to_the_active_release_function() -> None:
    config = json.loads((ROOT / "vercel.json").read_text(encoding="utf-8"))
    rewrites = {item["source"]: item["destination"] for item in config["rewrites"]}

    assert rewrites["/v1/search"] == "/api/operational?resource=search"
    assert rewrites["/v1/suggest"] == "/api/operational?resource=suggest"
    assert rewrites["/v1/ficha/:code"] == "/api/operational?resource=ficha&code=:code"
    assert rewrites["/v1/lookup/:code"] == "/api/operational?resource=lookup&code=:code"
    assert rewrites["/v1/sections"] == "/api/operational?resource=sections"
    assert rewrites["/v1/chapters"] == "/api/operational?resource=chapters"
    assert rewrites["/v1/repository"] == "/api/operational?resource=repository"
    assert rewrites["/v1/codes/:code/parent"] == "/api/operational?resource=parent&code=:code"
    assert rewrites["/v1/codes/:code/children"] == "/api/operational?resource=children&code=:code"
    assert rewrites["/v1/codes/:code/provenance"] == "/api/operational?resource=provenance&code=:code"
    assert rewrites["/v1/chapters/:chapter/national-notes"] == "/api/operational?resource=national-notes&chapter=:chapter"
    assert "/v1/:path*" not in rewrites
    assert config["redirects"] == [
        {"source": "/docs", "destination": "/documentation", "permanent": True},
        {"source": "/docs/:path*", "destination": "/documentation", "permanent": True},
    ]
