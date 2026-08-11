from pathlib import Path


ROOT = Path(__file__).resolve().parents[2]
WORKFLOWS = ROOT / ".github" / "workflows"


def test_manual_production_certification_smoke_tests_wheel_and_sdist():
    workflow = (WORKFLOWS / "production-certification.yml").read_text(encoding="utf-8")

    assert "python scripts/certify_package_install.py dist/*.whl" in workflow
    assert "python scripts/certify_package_install.py dist/*.tar.gz" in workflow
    assert workflow.index("python -m build") < workflow.index("dist/*.whl")
    assert workflow.index("dist/*.whl") < workflow.index("dist/*.tar.gz")


def test_official_editable_installs_always_use_reviewed_constraints():
    names = (
        "ci.yml",
        "official-data-pipeline.yml",
        "production-certification.yml",
    )
    violations = []
    for name in names:
        text = (WORKFLOWS / name).read_text(encoding="utf-8")
        for line in text.splitlines():
            if "python -m pip install" in line and " -e " in line:
                if "-c requirements/production-build.txt" not in line:
                    violations.append((name, line.strip()))

    assert violations == []
