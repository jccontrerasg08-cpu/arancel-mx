"""Structural contract for the package publication workflow.

These assertions verify the security-relevant shape of the publish workflow so a
future edit cannot quietly weaken it: tag-only triggers, no production bypass,
Trusted Publishing without stored secrets, OIDC scoped only to publisher jobs,
and no GitHub Release creation for package tags.
"""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "publish-python-package.yml"
PUBLISH_JOBS = {"publish-testpypi", "publish-pypi"}


@pytest.fixture(scope="module")
def workflow_text() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


@pytest.fixture(scope="module")
def workflow(workflow_text: str) -> dict:
    document = yaml.safe_load(workflow_text)
    assert isinstance(document, dict)
    return document


def _triggers(workflow: dict) -> dict:
    return workflow.get("on", workflow.get(True))


def test_workflow_exists() -> None:
    assert WORKFLOW.is_file()


def test_trigger_is_package_tags_only(workflow: dict) -> None:
    triggers = _triggers(workflow)
    assert set(triggers) == {"push"}
    assert triggers["push"] == {"tags": ["pkg-v*"]}


def test_no_production_bypass_triggers(workflow: dict) -> None:
    triggers = _triggers(workflow)
    assert "workflow_dispatch" not in triggers
    assert "pull_request" not in triggers
    assert "pull_request_target" not in triggers


def test_default_permissions_are_read_only(workflow: dict) -> None:
    assert workflow["permissions"] == {"contents": "read"}


def test_only_publisher_jobs_request_oidc(workflow: dict) -> None:
    for name, job in workflow["jobs"].items():
        permissions = job.get("permissions", {})
        has_oidc = permissions.get("id-token") == "write"
        assert has_oidc == (name in PUBLISH_JOBS), name


def test_publisher_jobs_use_gated_environments(workflow: dict) -> None:
    jobs = workflow["jobs"]
    assert jobs["publish-testpypi"]["environment"]["name"] == "testpypi"
    assert jobs["publish-pypi"]["environment"]["name"] == "pypi"


def test_production_publish_is_final_release_only(workflow: dict) -> None:
    condition = workflow["jobs"]["publish-pypi"].get("if", "")
    assert "production_eligible" in condition
    assert "'true'" in condition


def test_no_stored_upload_secrets(workflow_text: str) -> None:
    lowered = workflow_text.lower()
    assert "secrets." not in workflow_text
    assert "password:" not in lowered
    assert "twine upload" not in lowered


def test_uses_trusted_publisher_action(workflow_text: str) -> None:
    assert "pypa/gh-action-pypi-publish@" in workflow_text


def test_workflow_never_creates_a_github_release(workflow_text: str) -> None:
    lowered = workflow_text.lower()
    for forbidden in ("gh release create", "softprops/action-gh-release", "actions/create-release"):
        assert forbidden not in lowered


def test_build_happens_once_and_is_reused(workflow: dict) -> None:
    jobs = workflow["jobs"]
    build_steps = " ".join(
        str(step.get("run", "")) for step in jobs["build-once"]["steps"]
    )
    assert "python -m build" in build_steps
    # Publisher jobs must consume the uploaded artifact, never rebuild it.
    for name in PUBLISH_JOBS:
        job_steps = jobs[name]["steps"]
        assert any(
            str(step.get("uses", "")).startswith("actions/download-artifact@")
            for step in job_steps
        ), name
        assert all("python -m build" not in str(step.get("run", "")) for step in job_steps)
