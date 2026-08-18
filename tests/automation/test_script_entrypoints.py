from pathlib import Path
import subprocess
import sys


ROOT = Path(__file__).resolve().parents[2]
WORKFLOW = ROOT / ".github" / "workflows" / "official-data-pipeline.yml"


def test_github_aware_scripts_are_importable_as_repo_modules():
    modules = (
        "scripts.fetch_previous_release",
        "scripts.publish_release",
        "scripts.promote_operational_release",
        "scripts.data_alert",
        "scripts.check_documented_urls",
        "scripts.validate_ligie_html_pages",
    )

    for module in modules:
        result = subprocess.run(
            [sys.executable, "-m", module, "--help"],
            cwd=ROOT,
            capture_output=True,
            text=True,
            check=False,
        )
        assert result.returncode == 0, (module, result.stdout, result.stderr)


def test_official_workflow_uses_module_entrypoints_for_internal_script_imports():
    workflow = WORKFLOW.read_text(encoding="utf-8")

    required = (
        "python -m scripts.fetch_previous_release",
        "python -m scripts.publish_release",
        "python -m scripts.data_alert",
    )
    forbidden = (
        "python scripts/fetch_previous_release.py",
        "python scripts/publish_release.py",
        "python scripts/promote_operational_release.py",
        "python scripts/data_alert.py",
    )

    assert [value for value in required if value not in workflow] == []
    assert [value for value in forbidden if value in workflow] == []
