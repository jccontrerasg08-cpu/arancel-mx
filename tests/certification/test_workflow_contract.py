from __future__ import annotations

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "production-certification.yml"
_FULL_SHA_ACTION = re.compile(
    r"^\s*uses:\s*[^@\s]+@([0-9a-f]{40})(?:\s|#|$)",
    re.MULTILINE,
)
_ANY_ACTION = re.compile(r"^\s*uses:\s*[^@\s]+@([^\s#]+)", re.MULTILINE)


def _workflow() -> str:
    return WORKFLOW.read_text(encoding="utf-8")


def test_production_certification_is_manual_only_and_default_read_only():
    workflow = _workflow()

    assert "workflow_dispatch:" in workflow
    assert "pull_request:" not in workflow
    assert "push:" not in workflow
    assert "schedule:" not in workflow
    assert re.search(r"(?m)^permissions:\n\s+contents: read\s*$", workflow)


def test_release_boundary_is_the_only_contents_write_job():
    workflow = _workflow()

    assert workflow.count("contents: write") == 1
    assert "pull-requests: write" not in workflow
    assert "permissions: write-all" not in workflow
    assert "write-all" not in workflow
    assert "release-boundary:" in workflow
    assert "needs: offline" in workflow


def test_issue_boundary_is_the_only_issues_write_job_and_isolated_from_data_alerts():
    workflow = _workflow()

    assert workflow.count("issues: write") == 1
    assert "issue-boundary:" in workflow
    issue_index = workflow.index("  issue-boundary:")
    issue_job = workflow[issue_index:]
    assert "needs: offline" in issue_job
    assert "contents: read" in issue_job
    assert "issues: write" in issue_job
    assert "contents: write" not in issue_job
    assert "python -m scripts.certify_github_issue" in issue_job
    assert "python scripts/certify_github_issue.py" not in issue_job
    assert "scripts/data_alert.py" not in workflow
    assert "[DATA ALERT]" not in workflow


def test_mutation_boundaries_use_builtin_token_and_module_entrypoints():
    workflow = _workflow()

    assert workflow.count("GITHUB_TOKEN: ${{ github.token }}") == 3
    assert "secrets." not in workflow
    assert "python -m scripts.certify_github_release" in workflow
    assert "python -m scripts.certify_github_issue" in workflow
    assert "python scripts/certify_github_release.py" not in workflow
    assert "python scripts/certify_github_issue.py" not in workflow
    assert "--cleanup-only" in workflow
    assert "if: always()" in workflow
    assert "certification-" not in workflow
    assert "data-" not in workflow


def test_certification_workflow_uses_reviewed_dependency_install_and_pinned_actions():
    workflow = _workflow()

    assert workflow.count("python -m pip install pip==26.2.1") == 3
    assert (
        'python -m pip install -c requirements/production-build.txt -e ".[dev]"'
        in workflow
    )
    assert workflow.count('python -m pip install -c requirements/production-build.txt -e .') == 2

    all_refs = _ANY_ACTION.findall(workflow)
    pinned_refs = _FULL_SHA_ACTION.findall(workflow)
    assert all_refs
    assert len(pinned_refs) == len(all_refs)
    assert all(re.fullmatch(r"[0-9a-f]{40}", ref) for ref in pinned_refs)


def test_offline_gate_runs_before_every_mutation_boundary():
    workflow = _workflow()

    offline_index = workflow.index("  offline:")
    release_index = workflow.index("  release-boundary:")
    issue_index = workflow.index("  issue-boundary:")
    assert offline_index < release_index
    assert offline_index < issue_index
    assert "python -m pytest -q" in workflow[offline_index:release_index]
    assert "python -m build" in workflow[offline_index:release_index]
