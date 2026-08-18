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

    assert config["buildCommand"] == "python -m pip install --target api/_vendor 'psycopg[binary]>=3.3.4'"
    assert config["functions"] == {
        "api/operational.py": {"includeFiles": "api/_vendor/**"},
        "api/sync_operational.py": {"includeFiles": "api/_vendor/**"},
    }
    assert not (ROOT / "requirements.txt").exists()
    assert 'Path(__file__).with_name("_vendor")' in read_handler
    assert 'Path(__file__).with_name("_vendor")' in sync_handler
