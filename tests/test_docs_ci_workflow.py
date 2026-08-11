import json
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "docs-ci.yml"
BOOTSTRAP = ROOT / ".github" / "workflows" / "docs-bootstrap.yml"
LOCKFILE = ROOT / "website" / "package-lock.json"


def test_temporary_docs_bootstrap_is_removed():
    assert not BOOTSTRAP.exists()


def test_docs_ci_is_read_only_and_uses_committed_lockfile():
    assert WORKFLOW.is_file()
    assert LOCKFILE.is_file()

    lock = json.loads(LOCKFILE.read_text(encoding="utf-8"))
    assert lock["name"] == "arancel-mx-docs"
    assert lock["lockfileVersion"] == 3

    text = WORKFLOW.read_text(encoding="utf-8")
    assert "pull_request:" in text
    assert "permissions:\n  contents: read" in text

    required = (
        'node-version: "22"',
        "cache: npm",
        "cache-dependency-path: website/package-lock.json",
        "npm ci",
        "npm run typecheck",
        "npm run build",
        "npm run build -- --locale es",
        "npm run build -- --locale en",
    )
    assert [value for value in required if value not in text] == []

    forbidden = (
        "npm install --package-lock-only",
        "contents: write",
        "pages: write",
        "issues: write",
        "pull-requests: write",
        "id-token: write",
        "github.token",
        "GITHUB_TOKEN",
        "secrets.",
        "pull_request_target:",
        "git push",
        "deploy-pages",
        "configure-pages",
        "publish_release",
        "run_official_pipeline",
        "build_official_dataset",
    )
    assert [value for value in forbidden if value in text] == []


def test_docs_ci_external_actions_are_full_sha_pinned():
    text = WORKFLOW.read_text(encoding="utf-8")
    expected = (
        "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1",
        "actions/setup-node@820762786026740c76f36085b0efc47a31fe5020",
    )
    assert [value for value in expected if value not in text] == []
