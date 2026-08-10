from __future__ import annotations

import pytest

from scripts.certify_github_issue import (
    CertificationIssueError,
    certification_issue_title,
    certify_issue_boundary,
)


REPOSITORY = "owner/arancel-mx"
RUN_ID = "31440123456"
COMMIT_SHA = "a" * 40
TITLE = f"[CERTIFICATION ALERT] {RUN_ID}"


class FakeGitHub:
    def __init__(self, *, existing_issue=False):
        self.existing_issue = existing_issue
        self.issue = None
        self.comments = []
        self.events = []
        self.mutations = []

    def request_json(self, method, path, **kwargs):
        if method == "GET" and path.startswith("/issues?state=all&per_page=100&page="):
            page = int(path.rsplit("=", 1)[1])
            if page != 1:
                return []
            issues = []
            if self.existing_issue:
                issues.append(
                    {
                        "number": 5,
                        "title": TITLE,
                        "state": "closed",
                        "body": "older certification trace",
                    }
                )
            if self.issue is not None:
                issues.append(dict(self.issue))
            return issues
        if method == "POST" and path == "/issues":
            payload = kwargs["json"]
            self.events.append("create_issue")
            self.mutations.append((method, path, payload))
            self.issue = {
                "number": 10,
                "title": payload["title"],
                "body": payload["body"],
                "state": "open",
            }
            return dict(self.issue)
        if method == "GET" and path == "/issues/10":
            self.events.append("fetch_issue")
            assert self.issue is not None
            return dict(self.issue)
        if method == "POST" and path == "/issues/10/comments":
            payload = kwargs["json"]
            self.events.append("comment_issue")
            self.mutations.append((method, path, payload))
            self.comments.append(payload["body"])
            return {"id": 100, "body": payload["body"]}
        if method == "PATCH" and path == "/issues/10":
            payload = kwargs["json"]
            self.events.append("close_issue")
            self.mutations.append((method, path, payload))
            assert self.issue is not None
            assert payload == {"state": "closed"}
            self.issue["state"] = "closed"
            return dict(self.issue)
        raise AssertionError(f"unexpected request: {method} {path} {kwargs}")


def test_certification_issue_title_isolated_from_production_alert_namespace():
    assert certification_issue_title(RUN_ID) == TITLE
    with pytest.raises(ValueError, match="run id"):
        certification_issue_title("not-a-run")
    with pytest.raises(ValueError, match="production data alert"):
        certification_issue_title("[DATA ALERT] parser")


def test_issue_boundary_creates_verifies_comments_closes_and_refetches():
    client = FakeGitHub()

    result = certify_issue_boundary(client, REPOSITORY, RUN_ID, COMMIT_SHA)

    assert result == {
        "status": "passed",
        "issue_number": 10,
        "state": "closed",
        "title": TITLE,
    }
    assert client.events == [
        "create_issue",
        "fetch_issue",
        "comment_issue",
        "close_issue",
        "fetch_issue",
    ]
    assert client.issue is not None
    assert client.issue["state"] == "closed"
    assert client.issue["title"] == TITLE
    assert RUN_ID in client.issue["body"]
    assert COMMIT_SHA in client.issue["body"]
    assert "certification only; not a production incident" in client.issue["body"]
    assert len(client.comments) == 1
    assert "Certification mutation verified" in client.comments[0]
    assert all("[DATA ALERT]" not in str(value) for value in client.mutations)


def test_preexisting_exact_certification_issue_blocks_before_mutation():
    client = FakeGitHub(existing_issue=True)

    with pytest.raises(CertificationIssueError, match="pre-existing"):
        certify_issue_boundary(client, REPOSITORY, RUN_ID, COMMIT_SHA)

    assert client.mutations == []


class CommentFailureGitHub(FakeGitHub):
    def request_json(self, method, path, **kwargs):
        if method == "POST" and path == "/issues/10/comments":
            self.events.append("comment_issue_failed")
            raise RuntimeError("simulated comment failure")
        return super().request_json(method, path, **kwargs)


def test_failure_after_creation_still_closes_certification_issue():
    client = CommentFailureGitHub()

    with pytest.raises(CertificationIssueError, match="simulated comment failure"):
        certify_issue_boundary(client, REPOSITORY, RUN_ID, COMMIT_SHA)

    assert client.issue is not None
    assert client.issue["state"] == "closed"
    assert "close_issue" in client.events


class CommentAndCloseFailureGitHub(CommentFailureGitHub):
    def request_json(self, method, path, **kwargs):
        if method == "PATCH" and path == "/issues/10":
            self.events.append("close_issue_failed")
            raise RuntimeError("simulated close failure")
        return super().request_json(method, path, **kwargs)


def test_failure_preserves_primary_and_close_failure_context():
    client = CommentAndCloseFailureGitHub()

    with pytest.raises(CertificationIssueError) as raised:
        certify_issue_boundary(client, REPOSITORY, RUN_ID, COMMIT_SHA)

    message = str(raised.value)
    assert "simulated comment failure" in message
    assert "close also failed" in message
    assert "simulated close failure" in message
