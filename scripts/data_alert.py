"""Deterministic formatting and lifecycle helpers for official-data alerts."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
import hashlib
import json
import os
from pathlib import Path
import re
from collections.abc import Mapping, Sequence
from urllib.parse import quote

from scripts.github_api import GitHubApi, GitHubApiError, GitHubNotFound


MAX_ALERT_MESSAGE = 800
ALERT_MARKER_PREFIX = "<!-- arancel-mx-data-alert-key:"
ALERT_MARKER_RE = re.compile(r"<!-- arancel-mx-data-alert-key:[0-9a-f]{64} -->")
ALERT_LABELS = ("data-alert", "automation", "release-blocked")
_LABEL_METADATA = {
    "data-alert": ("B60205", "Official data pipeline alert"),
    "automation": ("1D76DB", "Created or maintained by repository automation"),
    "release-blocked": ("D93F0B", "Publication is blocked pending recovery"),
}


def _clean(value: str, label: str) -> str:
    if not isinstance(value, str) or not value.strip():
        raise ValueError(f"{label} must be a non-blank string")
    return value.strip()


def _sanitize_message(value: str) -> str:
    text = " ".join(str(value).replace("\x00", " ").split())
    text = text.replace("<!--", "< !--").replace("-->", "-- >")
    if len(text) > MAX_ALERT_MESSAGE:
        text = text[: MAX_ALERT_MESSAGE - 3] + "..."
    return text or "failure reported without diagnostic text"


@dataclass(frozen=True)
class DataAlert:
    stage: str
    failure_category: str
    dataset_version: str
    message: str
    run_id: str
    run_attempt: str
    commit_sha: str
    run_url: str

    def __post_init__(self) -> None:
        for field in (
            "stage",
            "failure_category",
            "dataset_version",
            "run_id",
            "run_attempt",
            "commit_sha",
            "run_url",
        ):
            object.__setattr__(self, field, _clean(getattr(self, field), field))
        object.__setattr__(self, "message", _sanitize_message(self.message))

    @property
    def key(self) -> str:
        payload = f"{self.stage}\x00{self.failure_category}".encode("utf-8")
        return hashlib.sha256(payload).hexdigest()

    @property
    def title(self) -> str:
        return f"[DATA ALERT] {self.stage}: {self.failure_category}"

    @property
    def marker(self) -> str:
        return f"{ALERT_MARKER_PREFIX}{self.key} -->"

    def body(self) -> str:
        return "\n".join(
            [
                self.marker,
                "# Official data pipeline blocked",
                "",
                "Publication state: **BLOCKED**",
                f"Dataset candidate: `{self.dataset_version}`",
                f"Stage: `{self.stage}`",
                f"Failure category: `{self.failure_category}`",
                "",
                "## Diagnostic",
                self.message,
                "",
                "## Run provenance",
                f"- Run: {self.run_url}",
                f"- Run ID: `{self.run_id}`",
                f"- Attempt: `{self.run_attempt}`",
                f"- Commit: `{self.commit_sha}`",
                "",
                "The release remains blocked until a later successful production run recovers this alert.",
                "",
            ]
        )

    def recurrence_comment(self) -> str:
        return "\n".join(
            [
                "Failure repeated. Publication remains **BLOCKED**.",
                "",
                f"- Dataset candidate: `{self.dataset_version}`",
                f"- Run: {self.run_url}",
                f"- Attempt: `{self.run_attempt}`",
                f"- Commit: `{self.commit_sha}`",
                f"- Diagnostic: {self.message}",
            ]
        )


def ensure_alert_labels(client: GitHubApi) -> None:
    for label in ALERT_LABELS:
        try:
            client.request_json("GET", f"/labels/{quote(label, safe='')}")
            continue
        except GitHubNotFound:
            pass
        color, description = _LABEL_METADATA[label]
        try:
            client.request_json(
                "POST",
                "/labels",
                json={"name": label, "color": color, "description": description},
            )
        except GitHubApiError as error:
            if error.status_code != 422:
                raise
            # Another concurrent notifier may have created the static label.
            client.request_json("GET", f"/labels/{quote(label, safe='')}")


def _open_data_alert_issues(client: GitHubApi) -> list[Mapping[str, object]]:
    response = client.request_json(
        "GET", "/issues?state=open&labels=data-alert&per_page=100"
    )
    if not isinstance(response, list):
        raise ValueError("GitHub issues response must be a list")
    issues: list[Mapping[str, object]] = []
    for value in response:
        if not isinstance(value, Mapping) or "pull_request" in value:
            continue
        labels = value.get("labels")
        label_names = {
            str(label.get("name"))
            for label in labels
            if isinstance(labels, list) and isinstance(label, Mapping)
        } if isinstance(labels, list) else set()
        if "data-alert" in label_names:
            issues.append(value)
    return issues


def _issue_number(issue: Mapping[str, object]) -> int:
    number = issue.get("number")
    if not isinstance(number, int) or isinstance(number, bool) or number <= 0:
        raise ValueError("data alert issue is missing a valid number")
    return number


def upsert_alert(client: GitHubApi, alert: DataAlert) -> int:
    ensure_alert_labels(client)
    matching = [
        issue
        for issue in _open_data_alert_issues(client)
        if alert.marker in str(issue.get("body") or "")
    ]
    if len(matching) > 1:
        raise ValueError(f"multiple open data alerts share marker {alert.key}")
    if len(matching) == 1:
        number = _issue_number(matching[0])
        client.request_json(
            "POST",
            f"/issues/{number}/comments",
            json={"body": alert.recurrence_comment()},
        )
        return number

    created = client.request_json(
        "POST",
        "/issues",
        json={
            "title": alert.title,
            "body": alert.body(),
            "labels": list(ALERT_LABELS),
        },
    )
    if not isinstance(created, Mapping):
        raise ValueError("GitHub issue creation response must be an object")
    return _issue_number(created)


def close_recovered_alerts(
    client: GitHubApi, run_url: str, commit_sha: str
) -> tuple[int, ...]:
    run_url = _clean(run_url, "run_url")
    commit_sha = _clean(commit_sha, "commit_sha")
    closed: list[int] = []
    for issue in _open_data_alert_issues(client):
        body = str(issue.get("body") or "")
        if ALERT_MARKER_RE.search(body) is None:
            continue
        number = _issue_number(issue)
        client.request_json(
            "POST",
            f"/issues/{number}/comments",
            json={
                "body": (
                    "Recovered. A later production run completed without a blocking "
                    f"data failure.\n\n- Run: {run_url}\n- Commit: `{commit_sha}`"
                )
            },
        )
        client.request_json(
            "PATCH",
            f"/issues/{number}",
            json={"state": "closed"},
        )
        closed.append(number)
    return tuple(closed)


def _run_url_from_environment() -> str:
    explicit = os.getenv("GITHUB_RUN_URL")
    if explicit:
        return explicit
    server = os.getenv("GITHUB_SERVER_URL", "https://github.com").rstrip("/")
    repository = _clean(os.getenv("GITHUB_REPOSITORY", ""), "GITHUB_REPOSITORY")
    run_id = _clean(os.getenv("GITHUB_RUN_ID", ""), "GITHUB_RUN_ID")
    return f"{server}/{repository}/actions/runs/{run_id}"


def _client_from_environment() -> GitHubApi:
    return GitHubApi(
        _clean(os.getenv("GITHUB_REPOSITORY", ""), "GITHUB_REPOSITORY"),
        _clean(os.getenv("GITHUB_TOKEN", ""), "GITHUB_TOKEN"),
        api_url=os.getenv("GITHUB_API_URL", "https://api.github.com"),
    )


def _load_result(path: Path) -> dict[str, object]:
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("result JSON must contain an object")
    return value


def _alert_from_result(result: Mapping[str, object]) -> DataAlert:
    if result.get("status") != "failed":
        raise ValueError("failure mode requires a failed result JSON")
    return DataAlert(
        stage=str(result.get("stage") or "unknown"),
        failure_category=str(result.get("failure_category") or "unknown_error"),
        dataset_version=str(result.get("dataset_version") or "unknown"),
        message=str(result.get("message") or "failure reported without diagnostic text"),
        run_id=_clean(os.getenv("GITHUB_RUN_ID", ""), "GITHUB_RUN_ID"),
        run_attempt=_clean(os.getenv("GITHUB_RUN_ATTEMPT", ""), "GITHUB_RUN_ATTEMPT"),
        commit_sha=_clean(os.getenv("GITHUB_SHA", ""), "GITHUB_SHA"),
        run_url=_run_url_from_environment(),
    )


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    subparsers = parser.add_subparsers(dest="mode", required=True)
    failure = subparsers.add_parser("failure")
    failure.add_argument("--result", type=Path, default=Path("out/pipeline-result.json"))
    subparsers.add_parser("recovery")
    return parser


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    try:
        client = _client_from_environment()
        if args.mode == "failure":
            number = upsert_alert(client, _alert_from_result(_load_result(args.result)))
            print(json.dumps({"status": "upserted", "issue_number": number}, sort_keys=True))
        else:
            closed = close_recovered_alerts(
                client,
                _run_url_from_environment(),
                _clean(os.getenv("GITHUB_SHA", ""), "GITHUB_SHA"),
            )
            print(json.dumps({"status": "recovered", "closed": list(closed)}, sort_keys=True))
    except (ValueError, OSError, json.JSONDecodeError, GitHubApiError) as error:
        print(f"error: {error}")
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
