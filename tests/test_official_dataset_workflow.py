from pathlib import Path
import re


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "official-data-pipeline.yml"
LEGACY_WORKFLOW = ROOT / ".github" / "workflows" / "build-official-dataset.yml"
ACTION_REF = re.compile(r"^\s*uses:\s*[^@\s]+@([0-9a-f]{40})(?:\s|$)", re.MULTILINE)
ANY_ACTION = re.compile(r"^\s*uses:\s*[^@\s]+@([^\s#]+)", re.MULTILINE)
ATTEST_ACTION = "actions/attest@1e69f48acb82d1966a394da916b4c1698aa569d6"
PUBLIC_ATTESTATION_PATHS = (
    "out/release/arancel_mx.duckdb",
    "out/release/arancel_mx.csv",
    "out/release/arancel_mx.json",
    "out/release/manifest.json",
    "out/release/SHA256SUMS",
    "out/release/official-sources.tar.gz",
)
PUBLIC_ATTESTATION_NAMES = tuple(path.rsplit("/", 1)[-1] for path in PUBLIC_ATTESTATION_PATHS)


def _workflow() -> str:
    assert WORKFLOW.is_file(), "official-data-pipeline.yml must replace the weekly workflow"
    return WORKFLOW.read_text(encoding="utf-8")


def _job_start(workflow: str, job: str) -> int:
    # Anchor on the job key itself; `publish` is also the name of a workflow input.
    match = re.search(rf"^  {re.escape(job)}:$", workflow, re.MULTILINE)
    assert match is not None, job
    return match.start()


def _job_block(workflow: str, job: str, next_job: str | None = None) -> str:
    start = _job_start(workflow, job)
    if next_job is None:
        return workflow[start:]
    return workflow[start : _job_start(workflow, next_job)]


def test_autonomous_workflow_replaces_legacy_weekly_workflow():
    workflow = _workflow()

    assert not LEGACY_WORKFLOW.exists()
    assert "name: Official data pipeline" in workflow
    assert "workflow_dispatch:" in workflow
    assert "schedule:" in workflow
    assert 'cron: "17 11 * * *"' in workflow
    assert "'arancel-mx-official-data-production'" in workflow
    assert "cancel-in-progress: false" in workflow
    assert re.search(r"^permissions:\n\s+contents: read$", workflow, re.MULTILINE)
    assert "pull_request:" not in workflow
    assert "pull_request_target:" not in workflow
    assert "[hs]" not in workflow
    assert "OPENAI_API_KEY" not in workflow
    assert "dspy" not in workflow


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
        "python -m scripts.fetch_previous_release",
        "scripts/run_official_pipeline.py",
        "out/pipeline-result.json",
        "actions/upload-artifact@",
        "name: ${{ steps.pipeline_result.outputs.artifact_name }}",
    )
    forbidden = ("contents: write", "issues: write", "secrets.", "[hs]", "OPENAI")

    assert [value for value in required if value not in build] == []
    assert [value for value in forbidden if value in build] == []
    assert build.index("python -m pytest -q") < build.index(
        "python -m scripts.fetch_previous_release"
    ) < build.index("scripts/run_official_pipeline.py")
    assert "status == 'built'" in build or "status == \"built\"" in build


def test_only_publisher_has_contents_write_and_it_requires_built_trusted_main():
    workflow = _workflow()
    publish = _job_block(workflow, "publish", "notify")

    assert workflow.count("contents: write") == 1
    assert "contents: write" in publish
    assert "issues: write" not in publish
    assert "needs: build-and-verify" in publish
    assert "needs.build-and-verify.result == 'success'" in publish
    assert "needs.build-and-verify.outputs.status == 'built'" in publish
    assert "github.ref == 'refs/heads/main'" in publish
    assert "actions/download-artifact@" in publish
    assert "name: ${{ needs.build-and-verify.outputs.artifact_name }}" in publish
    assert "certify_bundle" in publish
    assert "python -m scripts.publish_release" in publish


def test_artifact_name_survives_a_publish_only_rerun():
    workflow = _workflow()
    build = _job_block(workflow, "build-and-verify", "publish")
    publish = _job_block(workflow, "publish", "notify")

    # github.run_attempt increments on a re-run, and re-running only the failed
    # publisher does not re-upload from the already successful build, so neither end
    # of the handoff may derive the artifact name from the attempt number.
    assert "artifact_name: ${{ steps.pipeline_result.outputs.artifact_name }}" in build
    assert "name: ${{ steps.pipeline_result.outputs.artifact_name }}" in build
    assert "name: ${{ needs.build-and-verify.outputs.artifact_name }}" in publish
    assert "github.run_attempt" not in publish


def test_a_cancelled_production_job_still_raises_an_alert():
    notify = _job_block(_workflow(), "notify")

    assert "needs.build-and-verify.result == 'cancelled'" in notify
    assert "needs.publish.result == 'cancelled'" in notify


def test_dry_runs_cannot_displace_a_queued_production_run():
    workflow = _workflow()
    concurrency = workflow[workflow.index("concurrency:") : workflow.index("jobs:")]

    assert "'arancel-mx-official-data-production'" in concurrency
    assert "arancel-mx-official-data-dry-run-{0}" in concurrency
    assert "github.event_name == 'schedule' || inputs.publish == true" in concurrency
    assert "cancel-in-progress: false" in concurrency


def test_publisher_is_only_attestation_signer_and_uses_pinned_first_party_action():
    workflow = _workflow()
    build = _job_block(workflow, "build-and-verify", "publish")
    publish = _job_block(workflow, "publish", "notify")
    notify = _job_block(workflow, "notify")

    assert workflow.count("attestations: write") == 1
    assert workflow.count("id-token: write") == 1
    assert "attestations: write" in publish
    assert "id-token: write" in publish
    assert "contents: write" in publish
    assert "attestations: write" not in build
    assert "id-token: write" not in build
    assert "attestations: write" not in notify
    assert "id-token: write" not in notify
    assert "artifact-metadata: write" not in workflow

    assert publish.count(ATTEST_ACTION) == 1
    assert "actions/attest@v4" not in workflow


def test_attestation_subjects_are_exactly_the_six_public_release_files():
    workflow = _workflow()
    publish = _job_block(workflow, "publish", "notify")

    match = re.search(
        r"subject-path:\s*\|\n(?P<body>(?:\s+out/release/[^\n]+\n){6})",
        publish,
    )
    assert match is not None
    subjects = tuple(line.strip() for line in match.group("body").splitlines())
    assert subjects == PUBLIC_ATTESTATION_PATHS
    assert "out/release/*" not in publish
    assert "out/release/**" not in publish


def test_attestation_is_verified_before_existing_release_publisher():
    workflow = _workflow()
    publish = _job_block(workflow, "publish", "notify")

    assert "Generate build provenance attestation" in publish
    assert "Verify build provenance attestation" in publish
    assert "gh attestation verify" in publish
    assert "--repo jccontrerasg08-cpu/arancel-mx" in publish
    assert (
        "--signer-workflow "
        "jccontrerasg08-cpu/arancel-mx/.github/workflows/official-data-pipeline.yml"
    ) in publish
    assert "GH_TOKEN: ${{ github.token }}" in publish

    array_match = re.search(
        r"assets=\(\n(?P<body>(?:\s+\"[^\"]+\"\n){6})\s+\)",
        publish,
    )
    assert array_match is not None
    verified_names = tuple(
        line.strip().strip('"') for line in array_match.group("body").splitlines()
    )
    assert verified_names == PUBLIC_ATTESTATION_NAMES

    assert publish.index("Independently certify publication bundle") < publish.index(
        "Generate build provenance attestation"
    ) < publish.index("Verify build provenance attestation") < publish.index(
        "Publish immutable verified release"
    )


def test_publisher_uses_structured_result_file_instead_of_console_redirection():
    workflow = _workflow()
    publish = _job_block(workflow, "publish", "notify")

    assert "--result-path out/publisher-result.json" in publish
    assert "> out/publisher-result.json" not in publish
    assert "2>&1" not in publish
    assert "id: publisher" in publish
    assert "continue-on-error: true" in publish
    assert "id: publisher_result" in publish
    assert "if: always()" in publish


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
    assert "python -m scripts.data_alert" in notify


def test_no_change_with_skipped_publisher_is_explicitly_healthy_recovery():
    workflow = _workflow()
    notify = _job_block(workflow, "notify")

    assert "needs.build-and-verify.outputs.status == 'no_change'" in notify
    assert "needs.publish.result == 'skipped'" in notify
    assert "needs.publish.result == 'success'" in notify
    assert "python -m scripts.data_alert recovery" in notify


def test_failed_build_can_never_satisfy_publisher_condition():
    workflow = _workflow()
    publish = _job_block(workflow, "publish", "notify")

    assert "needs.build-and-verify.result == 'success'" in publish
    assert "needs.build-and-verify.outputs.status == 'built'" in publish
    assert publish.index("needs.build-and-verify.result == 'success'") < publish.index(
        "needs.build-and-verify.outputs.status == 'built'"
    )


def test_manual_publish_false_is_a_non_mutating_dry_run():
    workflow = _workflow()
    publish = _job_block(workflow, "publish", "notify")
    build = _job_block(workflow, "build-and-verify", "publish")
    notify = _job_block(workflow, "notify")

    assert "type: boolean" in workflow
    assert "default: false" in workflow
    assert "github.event_name == 'schedule' || inputs.publish == true" in publish
    assert "Generate build provenance attestation" not in build
    assert "inputs.publish != true" in notify
    assert "Dry run complete; GitHub issue mutation is disabled." in notify
