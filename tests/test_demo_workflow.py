from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "generate-demo.yml"
ACTION_REF = re.compile(r"^\s*uses:\s*[^@\s]+@([0-9a-f]{40})(?:\s|$)", re.MULTILINE)
ANY_ACTION = re.compile(r"^\s*uses:\s*[^@\s]+@([^\s#]+)", re.MULTILINE)


def _workflow() -> str:
    assert WORKFLOW.is_file()
    return WORKFLOW.read_text(encoding="utf-8")


def test_demo_workflow_is_manual_pr_based_and_least_privilege():
    workflow = _workflow()

    assert "workflow_dispatch:" in workflow
    assert "schedule:" not in workflow
    assert "pull_request:" not in workflow
    assert "pull_request_target:" not in workflow
    assert re.search(r"^\s+contents: write$", workflow, re.MULTILINE)
    assert re.search(r"^\s+pull-requests: write$", workflow, re.MULTILINE)
    assert 'branch="automation/demo-${GITHUB_RUN_ID}"' in workflow
    assert 'git push origin "$branch"' in workflow
    assert "gh pr create" in workflow
    assert "--base main" in workflow
    assert 'GH_TOKEN: ${{ github.token }}' in workflow
    assert "secrets.GITHUB_TOKEN" not in workflow


def test_demo_workflow_pins_actions_node_and_svg_term_cli():
    workflow = _workflow()
    refs = ANY_ACTION.findall(workflow)
    pinned = ACTION_REF.findall(workflow)

    assert refs
    assert len(refs) == len(pinned)
    assert "actions/checkout@" in workflow
    assert "actions/setup-node@" in workflow
    assert 'node-version: "22"' in workflow
    assert re.search(r"npm install -g svg-term-cli@\d+\.\d+\.\d+", workflow)


def test_demo_workflow_rejects_unsafe_install_and_masked_failures():
    workflow = _workflow()

    forbidden = (
        "actions/checkout@v4",
        "deb.nodesource.com",
        "curl -sL",
        "curl -fsSL",
        "npm install -g svg-term-cli\n",
        "|| true",
        "git push\n",
        "git push origin main",
    )
    assert [value for value in forbidden if value in workflow] == []
