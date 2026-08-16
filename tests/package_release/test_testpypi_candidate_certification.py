from __future__ import annotations

from pathlib import Path
import subprocess

from scripts import certify_testpypi_candidate as certifier


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "publish-python-package.yml"
HELPER = ROOT / "scripts" / "certify_testpypi_candidate.py"


def test_candidate_install_retries_until_this_runner_can_resolve_the_version() -> None:
    calls: list[list[str]] = []
    waits: list[float] = []

    def run(command: list[str], *, check: bool) -> None:
        calls.append(command)
        if len(calls) == 1:
            raise subprocess.CalledProcessError(1, command)

    certifier.install_candidate_with_retry(
        expected_version="0.3.2",
        attempts=3,
        delay_seconds=2.0,
        run=run,
        sleep=waits.append,
    )

    assert waits == [2.0]
    assert len(calls) == 2
    assert calls[0][-1] == "arancel-mx==0.3.2"
    assert "--no-deps" in calls[0]
    assert "--no-cache-dir" in calls[0]
    assert "https://test.pypi.org/simple/" in calls[0]


def test_candidate_install_raises_after_bounded_attempts() -> None:
    calls: list[list[str]] = []
    waits: list[float] = []

    def always_fail(command: list[str], *, check: bool) -> None:
        calls.append(command)
        raise subprocess.CalledProcessError(1, command)

    try:
        certifier.install_candidate_with_retry(
            expected_version="0.3.2",
            attempts=2,
            delay_seconds=1.0,
            run=always_fail,
            sleep=waits.append,
        )
    except subprocess.CalledProcessError:
        pass
    else:
        raise AssertionError("candidate installation must fail after the bounded retry budget")

    assert len(calls) == 2
    assert waits == [1.0]


def test_workflow_retries_the_candidate_from_each_matrix_runner() -> None:
    workflow = WORKFLOW.read_text(encoding="utf-8")
    matrix_job = workflow.split("  external-certification-matrix:\n", 1)[1].split(
        "  publish-pypi:\n", 1
    )[0]

    assert "wait-for-testpypi-index:" not in workflow
    assert "needs: [validate-tag, publish-testpypi]" in matrix_job
    assert "actions/checkout@" in matrix_job
    assert "persist-credentials: false" in matrix_job
    assert "path: certification-helper" in matrix_job
    assert "sparse-checkout: |" in matrix_job
    assert "scripts/certify_testpypi_candidate.py" in matrix_job
    assert 'python "$GITHUB_WORKSPACE/certification-helper/scripts/certify_testpypi_candidate.py"' in matrix_job
    assert "--attempts 40" in matrix_job
    assert "--delay-seconds 15" in matrix_job
    helper = HELPER.read_text(encoding="utf-8")
    assert "--no-cache-dir" in helper
    assert "https://test.pypi.org/simple/" in helper
    assert "https://pypi.org/simple/" in helper
