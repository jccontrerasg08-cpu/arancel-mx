from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "official-data-pipeline.yml"
LEGACY_WORKFLOW = ROOT / ".github" / "workflows" / "build-official-dataset.yml"
ACTION_REF = re.compile(r"^\s*uses:\s*[^@\s]+@([0-9a-f]{40})(?:\s|$)", re.MULTILINE)
ANY_ACTION = re.compile(r"^\s*uses:\s*[^@\s]+@([^\s#]+)", re.MULTILINE)


def _workflow() -> str:
    assert WORKFLOW.is_file(), "official-data-pipeline.yml must replace the weekly workflow"
    return WORKFLOW.read_text(encoding="utf-8")


def _job_block(workflow: str, job: str, next_job: str | None = None) -> str:
    start = workflow.index(f"  {job}:")
    if next_job is None:
        return workflow[start:]
    end = workflow.index(f"  {next_job}:", start + 1)
    return workflow[start:end]


def test_autonomous_workflow_replaces_legacy_weekly_workflow():
    workflow = _workflow()

    assert not LEGACY_WORKFLOW.exists()
    assert "name: Official data pipeline" in workflow
    assert "workflow_dispatch:" in workflow
    assert "schedule:" in workflow
    assert 'cron: "17 11 * * *"' in workflow
    assert "group: arancel-mx-official-data-production" in workflow
    assert "cancel-in-progress: false" in workflow
    assert re.search(r"^permissions:\n\s+contents: read$", workflow, re.MULTILINE)
    assert "pull_request:" not in workflow
    assert "pull_request_target:" not in workflow


def test_all_external_actions_are_pinned_to_full_commit_shas():
    workflow = _workflow()
    all_refs = ANY_ACTION.findall(workflow)
    pinned_refs = ACTION_REF.findall(workflow)

    assert all_refs
    assert len(pinned_refs) == len(all_refs)
    assert all(re.fullmatch(r"[0-9a-f]{40}", ref) for ref in pinned_refs)


def test_build_job_is_read_only_constrained_tested_and_fail_closed():
    workflow = _workflow()
    build = _job_block(workflow, "build-and-verify", "publish")

    required = (
        "timeout-minutes:",
        "contents: read",
        'python-version: "3.11"',
        "python -m pip install pip==26.2.1",
        'python -m pip install -c requirements/production-build.txt -e ".[dev]"',
        "python -m pytest -q",
        "scripts/fetch_previous_release.py",
        "scripts/run_official_pipeline.py",
        "out/pipeline-result.json",
        "actions/upload-artifact@",
        "arancel-mx-${{ github.run_id }}-${{ github.run_attempt }}",
    )
    forbidden = ("contents: write", "issues: write", "secrets.")

    assert [value for value in required if value not in build] == []
    assert [value for value in forbidden if value in build] == []
    assert build.index("python -m pytest -q") < build.index(
        "scripts/fetch_previous_release.py"
    ) < build.index("scripts/run_official_pipeline.py")
    assert "status == 'built'" in build or "status == \"built\"" in build


def test_only_publisher_has_contents_write_and_it_requires_built_trusted_main():
    workflow = _workflow()
    publish = _job_block(workflow, "publish", "notify")

    assert workflow.count("contents: write") == 1
    assert "contents: write" in publish
    assert "issues: write" not in publish
    assert "needs: build-and-verify" in publish
    assert "needs.build-and-verify.outputs.status" in publish
    assert "built" in publish
    assert "github.ref == 'refs/heads/main'" in publish
    assert "actions/download-artifact@" in publish
    assert "arancel-mx-${{ github.run_id }}-${{ github.run_attempt }}" in publish
    assert "verify_publication_bundle" in publish
    assert "scripts/publish_release.py" in publish


def test_only_notifier_has_issues_write_and_runs_always():
    workflow = _workflow()
    notify = _job_block(workflow, "notify")

    assert workflow.count("issues: write") == 1
    assert "issues: write" in notify
    assert "contents: write" not in notify
    assert "needs: [build-and-verify, publish]" in notify or (
        "build-and-verify" in notify and "publish" in notify
    )
    assert "if: always()" in notify
    assert "scripts/data_alert.py" in notify
