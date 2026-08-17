"""Public repository activity snapshot with an optional authenticated GitHub refresh."""

from __future__ import annotations

import time
from typing import Any

import requests

from arancel_mx.api.models import (
    RepositoryActivityResponse,
    RepositoryPipelineResponse,
    RepositoryReleaseResponse,
    RepositorySnapshotResponse,
)


_REPOSITORY = "jccontrerasg08-cpu/arancel-mx"
_CACHE_SECONDS = 30 * 60
_cached: tuple[float, RepositorySnapshotResponse] | None = None
_FALLBACK = RepositorySnapshotResponse(
    stars=0,
    observedAt="2026-08-17T07:16:00Z",
    releases=[
        RepositoryReleaseResponse(tag="data-2026.08.16", publishedAt="2026-08-16T11:42:20Z", url=f"https://github.com/{_REPOSITORY}/releases/tag/data-2026.08.16"),
        RepositoryReleaseResponse(tag="data-2026.08.15", publishedAt="2026-08-15T11:42:20Z", url=f"https://github.com/{_REPOSITORY}/releases/tag/data-2026.08.15"),
    ],
    recentPulls=[RepositoryActivityResponse(number=120, title="feat: promote verified SNICE corpus sources", url=f"https://github.com/{_REPOSITORY}/pull/120", updatedAt="2026-08-17T06:00:00Z")],
    recentIssues=[RepositoryActivityResponse(number=110, title="data: reconcile current LIGIE fractions with upstream NICO lag", url=f"https://github.com/{_REPOSITORY}/issues/110", updatedAt="2026-08-17T05:00:00Z")],
    pipeline=RepositoryPipelineResponse(status="completed", conclusion="success", url=f"https://github.com/{_REPOSITORY}/actions"),
    source="snapshot",
)


def _github_json(path: str, token: str) -> Any:
    response = requests.get(
        f"https://api.github.com/repos/{_REPOSITORY}{path}",
        headers={"Accept": "application/vnd.github+json", "Authorization": f"Bearer {token}", "User-Agent": "arancel-mx"},
        timeout=10,
    )
    response.raise_for_status()
    return response.json()


def repository_snapshot(token: str | None) -> RepositorySnapshotResponse:
    """Return cached GitHub metadata or a documented no-network fallback."""

    global _cached
    if not token:
        return _FALLBACK
    if _cached is not None and _cached[0] > time.monotonic():
        return _cached[1]
    try:
        repo, releases, pulls, issues, runs = (
            _github_json("", token),
            _github_json("/releases?per_page=5", token),
            _github_json("/pulls?state=all&sort=updated&direction=desc&per_page=4", token),
            _github_json("/issues?state=open&sort=updated&direction=desc&per_page=8", token),
            _github_json("/actions/runs?per_page=1", token),
        )
        workflow_runs = runs.get("workflow_runs", [])
        first_run = workflow_runs[0] if workflow_runs else None
        snapshot = RepositorySnapshotResponse(
            stars=repo["stargazers_count"],
            observedAt=time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
            releases=[RepositoryReleaseResponse(tag=item["tag_name"], publishedAt=item["published_at"], url=item["html_url"]) for item in releases if item.get("published_at")],
            recentPulls=[RepositoryActivityResponse(number=item["number"], title=item["title"], url=item["html_url"], updatedAt=item["updated_at"]) for item in pulls],
            recentIssues=[RepositoryActivityResponse(number=item["number"], title=item["title"], url=item["html_url"], updatedAt=item["updated_at"]) for item in issues if not item.get("pull_request")][:4],
            pipeline=RepositoryPipelineResponse(status=first_run["status"], conclusion=first_run.get("conclusion"), url=first_run["html_url"]) if first_run else _FALLBACK.pipeline,
            source="live",
        )
    except (KeyError, TypeError, requests.RequestException, ValueError):
        snapshot = _FALLBACK
    _cached = (time.monotonic() + _CACHE_SECONDS, snapshot)
    return snapshot
