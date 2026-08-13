"""Cross-workflow hardening contract, enforced on parsed YAML rather than text.

The other workflow tests assert product behaviour (which job may publish, which
job may alert). This module asserts the structural guarantees that make those
behaviours trustworthy, so a future edit cannot reintroduce a class of weakness
that GitHub Actions makes easy: unpinned actions, workflow-wide write tokens,
credentials left on disk, expression interpolation inside shell scripts, or
unbounded jobs.
"""

from __future__ import annotations

from collections.abc import Iterator
from pathlib import Path
import re

import pytest
import yaml


ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"
# Only the manually dispatched documentation workflow pushes with git, so it is the
# single place where the checkout credential may stay in .git/config.
CHECKOUTS_KEEPING_CREDENTIALS = frozenset({"generate-demo.yml"})
MAX_TIMEOUT_MINUTES = 60
_HOSTED_RUNNERS = frozenset({"ubuntu-latest", "windows-latest", "macos-latest"})
_PINNED_USES = re.compile(r"^[^@\s]+@[0-9a-f]{40}$")
_INTERPOLATION = re.compile(r"\$\{\{")


def _workflow_paths() -> list[Path]:
    return sorted((*WORKFLOWS.glob("*.yml"), *WORKFLOWS.glob("*.yaml")))


def _load(path: Path) -> dict[str, object]:
    document = yaml.safe_load(path.read_text(encoding="utf-8"))
    assert isinstance(document, dict), path.name
    return document


def _triggers(document: dict[str, object]) -> dict[str, object]:
    # PyYAML resolves the bare `on:` key to the boolean True under YAML 1.1.
    triggers = document.get("on", document.get(True))
    assert isinstance(triggers, dict), "workflow triggers must be an explicit mapping"
    return triggers


def _jobs(document: dict[str, object]) -> dict[str, dict[str, object]]:
    jobs = document.get("jobs")
    assert isinstance(jobs, dict) and jobs
    for job in jobs.values():
        assert isinstance(job, dict)
    return jobs  # type: ignore[return-value]


def _steps(job: dict[str, object]) -> list[dict[str, object]]:
    steps = job.get("steps") or []
    assert isinstance(steps, list)
    return [step for step in steps if isinstance(step, dict)]


def _all_steps() -> Iterator[tuple[str, str, dict[str, object]]]:
    for path in _workflow_paths():
        for name, job in _jobs(_load(path)).items():
            for step in _steps(job):
                yield path.name, name, step


@pytest.fixture(scope="module")
def workflows() -> dict[str, dict[str, object]]:
    paths = _workflow_paths()
    assert paths
    return {path.name: _load(path) for path in paths}


def test_every_workflow_parses_and_declares_bounded_triggers(workflows):
    for name, document in workflows.items():
        triggers = _triggers(document)
        assert "pull_request_target" not in triggers, name
        if "pull_request" in triggers:
            assert name == "ci.yml", f"{name} must not build from untrusted pull requests"


def test_no_workflow_grants_write_permissions_outside_a_job(workflows):
    for name, document in workflows.items():
        permissions = document.get("permissions")
        assert isinstance(permissions, dict), f"{name} must declare default permissions"
        granted = {scope for scope, level in permissions.items() if level == "write"}
        assert granted == set(), f"{name} grants {sorted(granted)} to every job"


def test_every_job_is_least_privilege_bounded_and_hosted_by_github(workflows):
    for name, document in workflows.items():
        for job_name, job in _jobs(document).items():
            label = f"{name}:{job_name}"
            assert isinstance(job.get("permissions"), dict), f"{label} inherits permissions"
            timeout = job.get("timeout-minutes")
            assert isinstance(timeout, int), f"{label} has no timeout"
            assert 0 < timeout <= MAX_TIMEOUT_MINUTES, label
            runs_on = job.get("runs-on")
            if isinstance(runs_on, str) and "matrix.os" in runs_on:
                matrix = job.get("strategy")
                assert isinstance(matrix, dict), label
                oss = (matrix.get("matrix") or {}).get("os")
                assert isinstance(oss, list) and oss, label
                assert set(oss) <= _HOSTED_RUNNERS, label
            else:
                assert runs_on == "ubuntu-latest", label


def test_every_workflow_serializes_concurrent_runs(workflows):
    for name, document in workflows.items():
        concurrency = document.get("concurrency")
        assert isinstance(concurrency, dict), f"{name} must declare a concurrency group"
        assert str(concurrency.get("group") or "").strip(), name
        assert "cancel-in-progress" in concurrency, name


def test_every_action_is_pinned_to_a_commit_sha_with_a_readable_version_comment():
    for path in _workflow_paths():
        text = path.read_text(encoding="utf-8")
        for job_name, job in _jobs(_load(path)).items():
            for step in _steps(job):
                uses = step.get("uses")
                if uses is None:
                    continue
                label = f"{path.name}:{job_name}"
                assert _PINNED_USES.fullmatch(str(uses)), f"{label} uses {uses}"
                assert f"uses: {uses} # v" in text, (
                    f"{label} pins {uses} without a readable version comment"
                )


def test_checkout_credentials_are_an_explicit_and_justified_decision():
    for name, job, step in _all_steps():
        uses = str(step.get("uses") or "")
        if not uses.startswith("actions/checkout@"):
            continue
        options = step.get("with")
        assert isinstance(options, dict), f"{name}:{job} checkout has no options"
        assert "persist-credentials" in options, (
            f"{name}:{job} must state persist-credentials explicitly"
        )
        if options["persist-credentials"] is not False:
            assert name in CHECKOUTS_KEEPING_CREDENTIALS, (
                f"{name}:{job} keeps the checkout credential without justification"
            )


def test_no_shell_script_interpolates_workflow_expressions():
    for name, job, step in _all_steps():
        script = step.get("run")
        if script is None:
            continue
        assert not _INTERPOLATION.search(str(script)), (
            f"{name}:{job} interpolates an expression into a shell script; "
            "pass the value through env: instead"
        )


def test_piped_shell_scripts_opt_into_pipefail():
    for name, job, step in _all_steps():
        script = str(step.get("run") or "")
        if "|" not in script:
            continue
        assert step.get("shell") == "bash", f"{name}:{job} pipes without shell: bash"
        assert "set -euo pipefail" in script, f"{name}:{job} pipes without pipefail"


def test_workflow_outputs_are_only_written_through_the_reviewed_boundary():
    for path in _workflow_paths():
        text = path.read_text(encoding="utf-8")
        assert "GITHUB_OUTPUT" not in text, (
            f"{path.name} writes step outputs inline; use scripts.workflow_diagnostics "
            "so the values stay validated and single-line"
        )
