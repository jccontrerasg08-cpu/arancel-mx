import re
from urllib.parse import unquote

import pytest

from scripts.data_alert import (
    ALERT_LABELS,
    DataAlert,
    close_recovered_alerts,
    upsert_alert,
)
from scripts.github_api import GitHubNotFound


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


class FakeClient:
    def __init__(self, issues=None, labels=None):
        self.issues = [dict(issue) for issue in (issues or [])]
        self.labels = set(labels or [])
        self.created_issues = []
        self.comments = []
        self.patches = []
        self.created_labels = []
        self.calls = []

    def request_json(self, method, path, **kwargs):
        self.calls.append((method, path, kwargs))
        if method == "GET" and path.startswith("/labels/"):
            label = unquote(path.removeprefix("/labels/"))
            if label not in self.labels:
                raise GitHubNotFound(404, "Not Found")
            return {"name": label}
        if method == "POST" and path == "/labels":
            label = kwargs["json"]["name"]
            self.labels.add(label)
            self.created_labels.append(label)
            return {"name": label}
        if method == "GET" and path == "/issues?state=open&labels=data-alert&per_page=100":
            return [issue for issue in self.issues if issue.get("state", "open") == "open"]
        if method == "POST" and path == "/issues":
            number = max([issue.get("number", 0) for issue in self.issues] + [0]) + 1
            issue = {
                "number": number,
                "state": "open",
                "title": kwargs["json"]["title"],
                "body": kwargs["json"]["body"],
                "labels": [{"name": value} for value in kwargs["json"]["labels"]],
            }
            self.issues.append(issue)
            self.created_issues.append(issue)
            return issue
        match = re.fullmatch(r"/issues/(\d+)/comments", path)
        if method == "POST" and match:
            number = int(match.group(1))
            body = kwargs["json"]["body"]
            self.comments.append((number, body))
            return {"id": len(self.comments), "body": body}
        match = re.fullmatch(r"/issues/(\d+)", path)
        if method == "PATCH" and match:
            number = int(match.group(1))
            self.patches.append((number, dict(kwargs["json"])))
            for issue in self.issues:
                if issue.get("number") == number:
                    issue.update(kwargs["json"])
                    return issue
            raise AssertionError(f"unknown issue {number}")
        raise AssertionError(f"unexpected request: {method} {path} {kwargs}")


def issue_for(item, number=1, *, valid_marker=True):
    body = item.body() if valid_marker else "User-created issue without automation marker"
    return {
        "number": number,
        "state": "open",
        "title": item.title,
        "body": body,
        "labels": [{"name": "data-alert"}],
    }


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


def test_upsert_creates_one_issue_with_all_alert_labels_when_no_match_exists():
    client = FakeClient()
    item = alert()

    issue_number = upsert_alert(client, item)

    assert issue_number == 1
    assert client.created_labels == list(ALERT_LABELS)
    assert len(client.created_issues) == 1
    created = client.created_issues[0]
    assert created["title"] == item.title
    assert item.marker in created["body"]
    assert [label["name"] for label in created["labels"]] == list(ALERT_LABELS)


def test_upsert_comments_on_existing_matching_issue_instead_of_creating_another():
    item = alert()
    client = FakeClient([issue_for(item, 7)], labels=ALERT_LABELS)

    issue_number = upsert_alert(client, alert(run_id="999", message="failure repeated"))

    assert issue_number == 7
    assert client.created_issues == []
    assert len(client.comments) == 1
    assert client.comments[0][0] == 7
    assert "failure repeated" in client.comments[0][1]
    assert "https://github.com/owner/repo/actions/runs/123" in client.comments[0][1]


def test_release_tag_collision_alert_stays_open_until_a_later_successful_run():
    item = alert(stage="publish", failure_category="release_tag_collision")
    client = FakeClient(labels=ALERT_LABELS)

    number = upsert_alert(client, item)

    assert number == 1
    assert client.issues[0]["state"] == "open"
    assert client.patches == []

    closed = close_recovered_alerts(
        client,
        "https://github.com/owner/repo/actions/runs/999",
        "deadbeef",
    )

    assert closed == (1,)
    assert client.issues[0]["state"] == "closed"
    assert client.patches == [(1, {"state": "closed"})]


def test_successful_no_change_recovery_closes_prior_source_access_alert():
    item = alert(failure_category="source_network", message="DOF was temporarily unavailable")
    client = FakeClient([issue_for(item, 7)], labels=ALERT_LABELS)

    closed = close_recovered_alerts(
        client,
        "https://github.com/owner/repo/actions/runs/1000",
        "feedface",
    )

    assert closed == (7,)
    assert client.issues[0]["state"] == "closed"
    assert client.comments == [
        (
            7,
            "Recovered. A later production run completed without a blocking data failure.\n\n"
            "- Run: https://github.com/owner/repo/actions/runs/1000\n"
            "- Commit: `feedface`",
        )
    ]


def test_upsert_fails_when_multiple_open_issues_share_the_same_marker():
    item = alert()
    client = FakeClient(
        [issue_for(item, 7), issue_for(item, 8)],
        labels=ALERT_LABELS,
    )

    with pytest.raises(ValueError, match="multiple open data alerts"):
        upsert_alert(client, item)

    assert client.created_issues == []
    assert client.comments == []


def test_recovery_comments_and_closes_every_valid_automation_alert():
    first = alert(failure_category="checksum")
    second = alert(stage="publish", failure_category="remote_asset_verification")
    client = FakeClient(
        [issue_for(first, 3), issue_for(second, 4)],
        labels=ALERT_LABELS,
    )

    closed = close_recovered_alerts(
        client,
        "https://github.com/owner/repo/actions/runs/999",
        "deadbeef",
    )

    assert closed == (3, 4)
    assert [number for number, _body in client.comments] == [3, 4]
    assert all("Recovered" in body for _number, body in client.comments)
    assert all("actions/runs/999" in body for _number, body in client.comments)
    assert client.patches == [(3, {"state": "closed"}), (4, {"state": "closed"})]


def test_recovery_never_closes_user_issue_without_valid_hidden_marker():
    item = alert()
    client = FakeClient(
        [issue_for(item, 3), issue_for(item, 99, valid_marker=False)],
        labels=ALERT_LABELS,
    )

    closed = close_recovered_alerts(
        client,
        "https://github.com/owner/repo/actions/runs/999",
        "deadbeef",
    )

    assert closed == (3,)
    assert client.patches == [(3, {"state": "closed"})]
    assert all(number != 99 for number, _body in client.comments)
