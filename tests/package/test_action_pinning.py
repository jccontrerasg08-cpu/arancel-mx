from __future__ import annotations

from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = ROOT / ".github" / "workflows"
USES_RE = re.compile(r"(?m)^\s*-?\s*uses:\s*([^@\s]+)@([^\s#]+)")
FULL_SHA_RE = re.compile(r"^[0-9a-f]{40}$")
APPROVED_ACTIONS = {
    "actions/attest",
    "actions/checkout",
    "actions/download-artifact",
    "actions/setup-node",
    "actions/setup-python",
    "actions/upload-artifact",
}


def _action_refs() -> list[tuple[Path, str, str]]:
    refs: list[tuple[Path, str, str]] = []
    for workflow in sorted(WORKFLOWS.glob("*.y*ml")):
        text = workflow.read_text(encoding="utf-8")
        refs.extend((workflow, action, ref) for action, ref in USES_RE.findall(text))
    assert refs, "no external GitHub Actions were discovered"
    return refs


def test_every_third_party_action_is_pinned_to_full_sha() -> None:
    invalid = [
        (str(path.relative_to(ROOT)), action, ref)
        for path, action, ref in _action_refs()
        if not FULL_SHA_RE.fullmatch(ref)
    ]
    assert invalid == []


def test_only_approved_action_repositories_are_used() -> None:
    unexpected = sorted(
        {
            action
            for _, action, _ in _action_refs()
            if action not in APPROVED_ACTIONS
        }
    )
    assert unexpected == []


def test_workflows_do_not_use_floating_v_tags() -> None:
    floating = [
        (str(path.relative_to(ROOT)), action, ref)
        for path, action, ref in _action_refs()
        if re.fullmatch(r"v\d+(?:\.\d+){0,2}", ref)
    ]
    assert floating == []


def test_ci_contract_tests_do_not_hardcode_historical_action_shas() -> None:
    source = (ROOT / "tests" / "test_public_distribution.py").read_text(encoding="utf-8")
    historical = {
        "d23441a48e516b6c34aea4fa41551a30e30af803",
        "ece7cb06caefa5fff74198d8649806c4678c61a1",
    }
    assert [sha for sha in historical if sha in source] == []


def test_approved_action_identity_list_is_explicit_not_wildcarded() -> None:
    assert all("*" not in action for action in APPROVED_ACTIONS)
    assert all(action.count("/") == 1 for action in APPROVED_ACTIONS)
