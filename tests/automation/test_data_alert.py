import re

from scripts.data_alert import DataAlert


def alert(**overrides):
    values = {
        "stage": "build",
        "failure_category": "legal_reconciliation",
        "dataset_version": "2026.08.10",
        "message": "legal reconciliation failed\nmissing DOF evidence",
        "run_id": "123",
        "run_attempt": "2",
        "commit_sha": "abc123def456",
        "run_url": "https://github.com/owner/repo/actions/runs/123",
    }
    values.update(overrides)
    return DataAlert(**values)


def test_same_stage_and_category_get_same_key_across_runs():
    first = alert(run_id="123", message="first failure")
    second = alert(run_id="999", run_attempt="7", message="different details")

    assert first.key == second.key
    assert re.fullmatch(r"[0-9a-f]{64}", first.key)


def test_different_failure_categories_get_different_keys():
    first = alert(failure_category="legal_reconciliation")
    second = alert(failure_category="checksum")

    assert first.key != second.key


def test_title_is_stable_and_specific():
    item = alert()

    assert item.title == "[DATA ALERT] build: legal_reconciliation"


def test_body_contains_marker_run_commit_candidate_and_blocked_state():
    item = alert()

    body = item.body()

    assert f"<!-- arancel-mx-data-alert-key:{item.key} -->" in body
    assert "https://github.com/owner/repo/actions/runs/123" in body
    assert "abc123def456" in body
    assert "2026.08.10" in body
    assert "BLOCKED" in body
    assert "legal reconciliation failed missing DOF evidence" in body
    assert "\nmissing DOF evidence" not in body


def test_body_caps_excessive_message_but_preserves_run_link():
    item = alert(message="x" * 10000)

    body = item.body()

    assert len(body) < 3000
    assert "https://github.com/owner/repo/actions/runs/123" in body
    assert "x" * 1000 not in body
    assert "..." in body
