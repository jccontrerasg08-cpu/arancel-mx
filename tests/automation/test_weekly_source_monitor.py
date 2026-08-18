from __future__ import annotations

from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "official-data-pipeline.yml"


def test_official_source_review_runs_weekly_and_retains_manual_dispatch() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert "workflow_dispatch:" in workflow
    assert '- cron: "17 11 * * 1"' in workflow
    assert '- cron: "17 11 * * *"' not in workflow
