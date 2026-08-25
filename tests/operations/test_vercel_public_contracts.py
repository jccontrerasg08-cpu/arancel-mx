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
