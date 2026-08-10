from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
PR_TEMPLATE = ROOT / ".github" / "pull_request_template.md"
SETTINGS = ROOT / "docs" / "operations" / "github-settings.md"


def test_pr_template_covers_production_sensitive_changes():
    template = PR_TEMPLATE.read_text(encoding="utf-8")
    required = (
        "- [ ] Si modifiqué Actions, mantuve permisos mínimos y acciones fijadas por SHA.",
        "- [ ] Si modifiqué fuentes/reconciliación, agregué fixtures o pruebas offline del fallo esperado.",
        "- [ ] Si modifiqué el contrato de release, actualicé esquema/manifiesto/documentación.",
        "- [ ] Si cambié dependencias del build oficial, actualicé `requirements/production-build.txt` en el mismo PR.",
    )

    assert [value for value in required if value not in template] == []


def test_github_settings_runbook_is_exact_and_actionable():
    assert SETTINGS.is_file()
    runbook = SETTINGS.read_text(encoding="utf-8")
    required = (
        "Settings → Actions → General",
        "Read repository contents and packages permissions",
        "Allow GitHub Actions to create and approve pull requests",
        "Settings → General → Releases",
        "Enable release immutability",
        "Settings → Rules → Rulesets",
        "Enforcement: Active",
        "Target: `main`",
        "Require a pull request before merging",
        "CI / test",
        "Require branches to be up to date before merging",
        "Require conversation resolution before merging",
        "Block force pushes",
        "Block deletions",
        "Require linear history",
        "Settings → General → Pull Requests",
        "Squash merging: ON",
        "Merge commits: OFF",
        "Rebase merging: OFF",
        "Automatically delete head branches: ON",
        "Always suggest updating pull request branches: ON",
        "Settings → Advanced Security",
        "Dependabot alerts: ON",
        "Dependabot security updates: ON",
        "Secret scanning: ON where available",
        "Push protection: ON where available",
        "Code scanning/default setup: ON where available",
        "Private vulnerability reporting: ON",
        "## Verification checklist",
    )

    assert [value for value in required if value not in runbook] == []


def test_both_readmes_link_github_settings_runbook():
    for name in ("README.md", "README.en.md"):
        text = (ROOT / name).read_text(encoding="utf-8")
        assert "docs/operations/github-settings.md" in text
