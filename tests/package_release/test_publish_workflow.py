"""Structural contract for the package publication workflow.

These assertions verify the security-relevant shape of the publish workflow so a
future edit cannot quietly weaken it: tag-only triggers, no production bypass,
Trusted Publishing without stored secrets, OIDC scoped only to publisher jobs,
and no GitHub Release creation for package tags.
"""

from __future__ import annotations

from pathlib import Path
import re

import pytest

ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "publish-python-package.yml"
PUBLISH_JOBS = {"publish-testpypi", "publish-pypi"}
_TOP_LEVEL = re.compile(r"^[a-zA-Z_][\w-]*:", re.MULTILINE)
_JOB_KEY = re.compile(r"^  ([\w-]+):$", re.MULTILINE)


@pytest.fixture(scope="module")
def workflow_text() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def _block_after(text: str, header: str) -> str:
    match = re.search(rf"^{re.escape(header)}\n", text, re.MULTILINE)
    assert match is not None, header
    start = match.end()
    nxt = _TOP_LEVEL.search(text, start)
    return text[start : nxt.start() if nxt else len(text)]


def _job_blocks(text: str) -> dict[str, str]:
    jobs_match = re.search(r"^jobs:\n", text, re.MULTILINE)
    assert jobs_match is not None
    jobs_text = text[jobs_match.end() :]
    keys = list(_JOB_KEY.finditer(jobs_text))
    assert keys
    blocks: dict[str, str] = {}
    for i, match in enumerate(keys):
        end = keys[i + 1].start() if i + 1 < len(keys) else len(jobs_text)
        blocks[match.group(1)] = jobs_text[match.start() : end]
    return blocks


def test_workflow_exists() -> None:
    assert WORKFLOW.is_file()


def test_trigger_is_package_tags_only(workflow_text: str) -> None:
    assert re.search(
        r'^on:\n  push:\n    tags:\n      - "pkg-v\*"\n',
        workflow_text,
        re.MULTILINE,
    )
    triggers = _block_after(workflow_text, "on:")
    assert "workflow_dispatch:" not in triggers
    assert "pull_request:" not in triggers
    assert "pull_request_target:" not in triggers


def test_default_permissions_are_read_only(workflow_text: str) -> None:
    assert re.search(r"^permissions:\n  contents: read\s*$", workflow_text, re.MULTILINE)


def test_only_publisher_jobs_request_oidc(workflow_text: str) -> None:
    for name, block in _job_blocks(workflow_text).items():
        has_oidc = "id-token: write" in block
        assert has_oidc == (name in PUBLISH_JOBS), name


def test_publisher_jobs_use_gated_environments(workflow_text: str) -> None:
    jobs = _job_blocks(workflow_text)
    for job, environment in (
        ("publish-testpypi", "testpypi"),
        ("publish-pypi", "pypi"),
    ):
        assert re.search(
            rf"^    environment:[ \t]*\n"
            rf"(?:(?: {{6,}}\S.*)?\n)*?"
            rf"^      name:[ \t]*{environment}[ \t]*$",
            jobs[job],
            re.MULTILINE,
        ), job


def test_production_publish_is_final_release_only(workflow_text: str) -> None:
    block = _job_blocks(workflow_text)["publish-pypi"]
    assert re.search(
        r"^    if:[ \t]*needs\.validate-tag\.outputs\.production_eligible"
        r"[ \t]*==[ \t]*['\"]true['\"][ \t]*$",
        block,
        re.MULTILINE,
    )


def test_tag_must_point_at_protected_main_tip(workflow_text: str) -> None:
    block = _job_blocks(workflow_text)["validate-tag"]
    assert "TAG_SHA: ${{ github.sha }}" in block
    assert "git fetch --no-tags --depth 1 origin main" in block
    assert 'main_sha="$(git rev-parse FETCH_HEAD)"' in block
    assert 'if [ "$TAG_SHA" != "$main_sha" ]; then' in block
    assert "exit 1" in block


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


def test_external_certification_resolves_dependencies_from_pypi_only(
    workflow_text: str,
) -> None:
    matrix_job = _job_blocks(workflow_text)["external-certification-matrix"]
    helper = (ROOT / "scripts" / "certify_testpypi_candidate.py").read_text(
        encoding="utf-8"
    )

    assert 'python "$GITHUB_WORKSPACE/certification-helper/scripts/certify_testpypi_candidate.py"' in matrix_job
    assert "--no-deps" in helper
    assert "--no-cache-dir" in helper
    assert "https://test.pypi.org/simple/" in helper
    assert "https://pypi.org/simple/" in helper
    assert "--extra-index-url" not in helper
    assert "metadata.requires(\"arancel-mx\")" in helper
    assert '"pip", "check"' in helper


def test_external_certification_retries_from_each_runner_instead_of_a_global_wait(
    workflow_text: str,
) -> None:
    jobs = _job_blocks(workflow_text)
    matrix_job = jobs["external-certification-matrix"]

    assert "wait-for-testpypi-index" not in jobs
    assert "needs: [validate-tag, publish-testpypi]" in matrix_job
    assert "--attempts 40" in matrix_job
    assert "--delay-seconds 15" in matrix_job


def test_production_publish_requires_the_os_python_matrix(workflow_text: str) -> None:
    jobs = _job_blocks(workflow_text)
    matrix_job = jobs["external-certification-matrix"]
    assert "needs: [validate-tag, publish-testpypi]" in matrix_job
    assert "runs-on: ${{ matrix.os }}" in matrix_job
    assert "os: [ubuntu-latest, windows-latest, macos-latest]" in matrix_job
    assert 'python-version: ["3.11", "3.12", "3.13"]' in matrix_job
    pypi = jobs["publish-pypi"]
    assert (
        "needs: [validate-tag, build-once, publish-testpypi, external-certification-matrix]"
        in pypi
    )
    assert "actions/checkout@" in matrix_job
    assert "persist-credentials: false" in matrix_job
    assert "path: certification-helper" in matrix_job
    assert "sparse-checkout: |" in matrix_job
    assert "scripts/certify_testpypi_candidate.py" in matrix_job
    assert "arancel-mx doctor" not in matrix_job
    assert "${EXPECTED_VERSION}" not in matrix_job
    assert "os.environ['EXPECTED_VERSION']" in matrix_job
    build = jobs["build-once"]
    assert "python -m build" in build
    assert "EXPECTED_VERSION: ${{ needs.validate-tag.outputs.version }}" in build
    assert 'test -f "dist/arancel_mx-${EXPECTED_VERSION}.tar.gz"' in build
    for name in PUBLISH_JOBS:
        job = jobs[name]
        assert "actions/download-artifact@" in job
        assert "python -m build" not in job
