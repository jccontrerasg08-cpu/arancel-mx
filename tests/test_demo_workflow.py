from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "generate-demo.yml"
ACTION_REF = re.compile(r"^\s*uses:\s*[^@\s]+@([0-9a-f]{40})(?:\s|$)", re.MULTILINE)
ANY_ACTION = re.compile(r"^\s*uses:\s*[^@\s]+@([^\s#]+)", re.MULTILINE)


def _workflow() -> str:
    assert WORKFLOW.is_file()
    return WORKFLOW.read_text(encoding="utf-8")


def _top_level_permissions(workflow: str) -> dict[str, str]:
    """Return the workflow-level permissions mapping (the block before ``jobs:``)."""

    preamble = workflow.split("\njobs:", 1)[0]
    values: dict[str, str] = {}
    in_permissions = False
    for line in preamble.splitlines():
        if line.startswith("permissions:"):
            in_permissions = True
            inline = line.partition(":")[2].strip()
            if inline:
                scalar = inline.split("#", 1)[0].strip()
                if ":" in scalar:
                    key, _, value = scalar.partition(":")
                    values[key.strip()] = value.strip()
                elif scalar:
                    values["*"] = scalar
                in_permissions = False
            continue
        if not in_permissions:
            continue
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if line[:1] not in {" ", "\t"}:
            break
        stripped = line.split("#", 1)[0].strip()
        key, _, value = stripped.partition(":")
        if key and value:
            values[key.strip()] = value.strip()
    return values


def test_demo_workflow_is_manual_pr_based_and_least_privilege():
    workflow = _workflow()

    assert "workflow_dispatch:" in workflow
    assert "schedule:" not in workflow
    assert "pull_request:" not in workflow
    assert "pull_request_target:" not in workflow
    assert re.search(r"^\s+contents: write(?: #.*)?$", workflow, re.MULTILINE)
    assert re.search(r"^\s+pull-requests: write(?: #.*)?$", workflow, re.MULTILINE)
    top_level = _top_level_permissions(workflow)
    assert top_level.get("contents") == "read"
    assert "*" not in top_level
    assert all(value == "read" for value in top_level.values())
    assert not re.search(
        r"^[ \t]*permissions:[ \t]*write-all(?:[ \t]+#.*)?$",
        workflow,
        re.MULTILINE,
    )
    assert 'branch="automation/demo-${GITHUB_RUN_ID}"' in workflow
    assert 'git push origin "$branch"' in workflow
    assert "gh pr create" in workflow
    assert "--base main" in workflow
    assert 'GH_TOKEN: ${{ github.token }}' in workflow
    assert "secrets.GITHUB_TOKEN" not in workflow


def test_top_level_permissions_ignore_job_scoped_write() -> None:
    workflow = (
        "permissions:\n"
        "  contents: read\n"
        "jobs:\n"
        "  generate:\n"
        "    permissions:\n"
        "      contents: write\n"
        "      pull-requests: write\n"
    )
    assert _top_level_permissions(workflow) == {"contents": "read"}


def test_top_level_permissions_detect_write_all_scalar() -> None:
    workflow = (
        "name: demo\n"
        "permissions: write-all\n"
        "jobs:\n"
        "  generate:\n"
        "    permissions:\n"
        "      contents: write\n"
    )
    assert _top_level_permissions(workflow) == {"*": "write-all"}


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
