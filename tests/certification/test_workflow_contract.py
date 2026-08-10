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
    assert "issues: write" not in workflow
    assert "pull-requests: write" not in workflow
    assert "permissions: write-all" not in workflow
    assert "write-all" not in workflow
    assert "release-boundary:" in workflow
    assert "needs: offline" in workflow


def test_release_boundary_uses_builtin_token_and_always_runs_cleanup():
    workflow = _workflow()

    assert "GITHUB_TOKEN: ${{ github.token }}" in workflow
    assert "secrets." not in workflow
    assert "python scripts/certify_github_release.py" in workflow
    assert "--cleanup-only" in workflow
    assert "if: always()" in workflow
    assert "certification-" not in workflow
    assert "data-" not in workflow


def test_certification_workflow_uses_reviewed_dependency_install_and_pinned_actions():
    workflow = _workflow()

    assert workflow.count("python -m pip install pip==26.2.1") == 2
    assert (
        'python -m pip install -c requirements/production-build.txt -e ".[dev]"'
        in workflow
    )
    assert 'python -m pip install -c requirements/production-build.txt -e .' in workflow

    all_refs = _ANY_ACTION.findall(workflow)
    pinned_refs = _FULL_SHA_ACTION.findall(workflow)
    assert all_refs
    assert len(pinned_refs) == len(all_refs)
    assert all(re.fullmatch(r"[0-9a-f]{40}", ref) for ref in pinned_refs)


def test_offline_gate_runs_before_any_mutation_boundary():
    workflow = _workflow()

    offline_index = workflow.index("  offline:")
    release_index = workflow.index("  release-boundary:")
    assert offline_index < release_index
    assert "python -m pytest -q" in workflow[offline_index:release_index]
    assert "python -m build" in workflow[offline_index:release_index]
