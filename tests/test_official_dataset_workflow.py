from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "build-official-dataset.yml"


def test_official_dataset_workflow_is_read_only_and_pinned():
    workflow = WORKFLOW.read_text(encoding="utf-8")
    required = (
        "workflow_dispatch:",
        "schedule:",
        "17 11 * * 1",
        "contents: read",
        "timeout-minutes: 45",
        "actions/checkout@d23441a48e516b6c34aea4fa41551a30e30af803",
        "actions/setup-python@ece7cb06caefa5fff74198d8649806c4678c61a1",
        "actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a",
        'python-version: "3.11"',
        'python -m pip install -e ".[dev]"',
        "python -m pytest -q",
        "python scripts/build_official_dataset.py",
        "out/release/",
        "if-no-files-found: error",
        "retention-days: 30",
        'manifest["validation_status"] == "passed"',
        'int(manifest["row_count"]) > 0',
    )
    forbidden = (
        "contents: write",
        "secrets.",
        "git push",
        "gh release",
        "create-release",
        "softprops/action-gh-release",
    )

    assert [value for value in required if value not in workflow] == []
    assert [value for value in forbidden if value in workflow] == []
    assert workflow.index("python -m pytest -q") < workflow.index(
        "python scripts/build_official_dataset.py"
    )


def test_official_dataset_workflow_uploads_only_after_manifest_verification():
    workflow = WORKFLOW.read_text(encoding="utf-8")

    assert workflow.index('manifest["validation_status"] == "passed"') < workflow.index(
        "actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a"
    )
