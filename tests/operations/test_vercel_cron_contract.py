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


def test_vercel_runtime_requirements_include_only_the_operational_driver_extra() -> None:
    requirements = (ROOT / "requirements.txt").read_text(encoding="utf-8")

    assert "-e .[operational]" in requirements
