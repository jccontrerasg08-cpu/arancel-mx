from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "published-bundle-canary.yml"
ACTION_REF = re.compile(r"^\s*uses:\s*[^@\s]+@([0-9a-f]{40})(?:\s|$)", re.MULTILINE)
ANY_ACTION = re.compile(r"^\s*uses:\s*[^@\s]+@([^\s#]+)", re.MULTILINE)


def _workflow() -> str:
    assert WORKFLOW.is_file()
    return WORKFLOW.read_text(encoding="utf-8")


def test_canary_is_read_only_scheduled_and_does_not_publish() -> None:
    workflow = _workflow()

    assert "name: Published bundle canary" in workflow
    assert "workflow_dispatch:" in workflow
    assert "schedule:" in workflow
    assert 'cron: "47 12 * * *"' in workflow
    assert "pull_request:" not in workflow
    assert "pull_request_target:" not in workflow
    assert "verify-published-bundle:" in workflow
    assert re.search(r"(?m)^  test:$", workflow) is None
    assert "github.ref == 'refs/heads/main'" in workflow
    assert "persist-credentials: false" in workflow
    assert "contents: write" not in workflow
    assert "issues: write" not in workflow
    assert "attestations: write" not in workflow
    assert "id-token: write" not in workflow
    assert "pull-requests: write" not in workflow
    assert "arancel-mx-published-bundle-canary" in workflow
    assert "cancel-in-progress: false" in workflow


def test_canary_installs_runtime_package_without_classifier_or_dev_extras() -> None:
    workflow = _workflow()

    assert "python -m pip install pip==26.2.1" in workflow
    assert "python -m pip install -c requirements/production-build.txt -e ." in workflow
    assert ".[dev]" not in workflow
    assert "[hs]" not in workflow
    assert "OPENAI" not in workflow
    assert "dspy" not in workflow
    assert "arancel-mx data download" in workflow
    assert "arancel-mx data verify --bundle" in workflow
    assert workflow.index("python -m pip install -c requirements/production-build.txt -e .") < workflow.index(
        "arancel-mx data download"
    ) < workflow.index("arancel-mx data verify --bundle")


def test_canary_actions_are_pinned_to_full_commit_shas() -> None:
    workflow = _workflow()
    all_refs = ANY_ACTION.findall(workflow)
    pinned_refs = ACTION_REF.findall(workflow)

    assert all_refs
    assert len(pinned_refs) == len(all_refs)
    assert all(re.fullmatch(r"[0-9a-f]{40}", ref) for ref in pinned_refs)
