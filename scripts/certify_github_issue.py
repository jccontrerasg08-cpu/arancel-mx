"""Certify GitHub issue write permissions with one closed audit issue."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
from collections.abc import Mapping

from scripts.github_api import GitHubApi


_TITLE_PREFIX = "[CERTIFICATION ALERT]"
_COMMIT_PATTERN = re.compile(r"^[0-9a-fA-F]{40}$")


class CertificationIssueError(RuntimeError):
    """Fail-closed error for the temporary issue certification boundary."""


def certification_issue_title(run_id: str) -> str:
    """Return the isolated certification issue title for one GitHub run."""
    value = str(run_id).strip()
    if value.startswith("[DATA ALERT]"):
        raise ValueError("production data alert title is forbidden for certification")
    if not value.isdigit():
        raise ValueError("GitHub run id must contain digits only")
    return f"{_TITLE_PREFIX} {value}"


def _validate_repository(repository: str) -> str:
    value = str(repository).strip()
    parts = value.split("/")
    if len(parts) != 2 or not all(parts):
        raise ValueError("repository must use owner/name")
    return value


def _validate_commit_sha(commit_sha: str) -> str:
    value = str(commit_sha).strip()
    if not _COMMIT_PATTERN.fullmatch(value):
        raise ValueError("commit SHA must contain exactly 40 hexadecimal characters")
    return value.lower()


def _matching_issues(client: GitHubApi, title: str) -> list[Mapping[str, object]]:
    matches: list[Mapping[str, object]] = []
    page = 1
    while True:
        value = client.request_json(
            "GET",
            f"/issues?state=all&per_page=100&page={page}",
        )
        if not isinstance(value, list):
            raise CertificationIssueError("GitHub issues response must be a list")
        for issue in value:
            if not isinstance(issue, Mapping) or "pull_request" in issue:
                continue
            if issue.get("title") == title:
                matches.append(issue)
        if len(value) < 100:
            break
        page += 1
    return matches


def _issue_number(issue: Mapping[str, object]) -> int:
    number = issue.get("number")
    if not isinstance(number, int) or isinstance(number, bool) or number <= 0:
        raise CertificationIssueError("certification issue is missing a valid number")
    return number


def _body(repository: str, run_id: str, commit_sha: str) -> str:
    return "\n".join(
        [
            "# GitHub issue boundary certification",
            "",
            "certification only; not a production incident",
            "",
            f"- Repository: `{repository}`",
            f"- Run ID: `{run_id}`",
            f"- Commit: `{commit_sha}`",
            "",
            "This issue is created only to verify the isolated `issues: write` boundary.",
            "It must finish closed and is retained as an auditable certification trace.",
            "",
        ]
    )


def _verify_issue(
    client: GitHubApi,
    number: int,
    *,
    title: str,
    body: str,
    expected_state: str,
) -> Mapping[str, object]:
    issue = client.request_json("GET", f"/issues/{number}")
    if not isinstance(issue, Mapping) or "pull_request" in issue:
        raise CertificationIssueError("GitHub certification issue response is invalid")
    if issue.get("title") != title:
        raise CertificationIssueError("certification issue title mismatch")
    if issue.get("body") != body:
        raise CertificationIssueError("certification issue body mismatch")
    if issue.get("state") != expected_state:
        raise CertificationIssueError(
            "certification issue state mismatch: "
            f"actual={issue.get('state')!r} expected={expected_state!r}"
        )
    return issue


def _close_issue(client: GitHubApi, number: int) -> None:
    client.request_json(
        "PATCH",
        f"/issues/{number}",
        json={"state": "closed"},
    )


def certify_issue_boundary(
    client: GitHubApi,
    repository: str,
    run_id: str,
    commit_sha: str,
) -> dict[str, object]:
    """Create, verify, comment on, close, and re-verify one audit issue."""
    repository = _validate_repository(repository)
    title = certification_issue_title(run_id)
    commit_sha = _validate_commit_sha(commit_sha)
    body = _body(repository, str(run_id), commit_sha)

    if _matching_issues(client, title):
        raise CertificationIssueError(f"pre-existing certification issue blocks {title}")

    issue_number: int | None = None
    primary_error: Exception | None = None
    close_error: Exception | None = None

    try:
        created = client.request_json(
            "POST",
            "/issues",
            json={"title": title, "body": body},
        )
        if not isinstance(created, Mapping):
            raise CertificationIssueError("GitHub issue creation response must be an object")
        issue_number = _issue_number(created)
        _verify_issue(
            client,
            issue_number,
            title=title,
            body=body,
            expected_state="open",
        )
        client.request_json(
            "POST",
            f"/issues/{issue_number}/comments",
            json={
                "body": (
                    "Certification mutation verified. Closing this issue as the retained "
                    f"audit trace for run `{run_id}` and commit `{commit_sha}`."
                )
            },
        )
        _close_issue(client, issue_number)
        _verify_issue(
            client,
            issue_number,
            title=title,
            body=body,
            expected_state="closed",
        )
    except Exception as error:  # noqa: BLE001 - preserve primary mutation failure
        primary_error = error

    if primary_error is not None and issue_number is not None:
        try:
            current = client.request_json("GET", f"/issues/{issue_number}")
            if not isinstance(current, Mapping) or current.get("state") != "closed":
                _close_issue(client, issue_number)
        except Exception as error:  # noqa: BLE001 - retain cleanup failure context
            close_error = error

    if primary_error is not None:
        message = f"issue-boundary certification failed: {primary_error}"
        if close_error is not None:
            message += f"; close also failed: {close_error}"
        raise CertificationIssueError(message) from primary_error
    if issue_number is None:
        raise CertificationIssueError("issue-boundary certification ended without evidence")

    return {
        "status": "passed",
        "issue_number": issue_number,
        "state": "closed",
        "title": title,
    }


def _environment() -> tuple[str, str, str, str]:
    repository = os.getenv("GITHUB_REPOSITORY", "")
    token = os.getenv("GITHUB_TOKEN", "")
    run_id = os.getenv("GITHUB_RUN_ID", "")
    commit_sha = os.getenv("GITHUB_SHA", "")
    if not token:
        raise ValueError("GITHUB_TOKEN is required")
    _validate_repository(repository)
    certification_issue_title(run_id)
    _validate_commit_sha(commit_sha)
    return repository, token, run_id, commit_sha


def _parse_args(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    return parser.parse_args(argv)


def main(argv: list[str] | None = None) -> int:
    _parse_args(argv)
    repository, token, run_id, commit_sha = _environment()
    client = GitHubApi(repository, token)
    result = certify_issue_boundary(client, repository, run_id, commit_sha)
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return 0


if __name__ == "__main__":
    sys.exit(main())
