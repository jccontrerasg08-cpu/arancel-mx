from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
WORKFLOW = ROOT / ".github" / "workflows" / "docs-bootstrap.yml"


def test_docs_bootstrap_is_pull_request_only_and_read_only():
    text = WORKFLOW.read_text(encoding="utf-8")

    assert "pull_request:" in text
    assert "workflow_dispatch:" not in text
    assert "push:" not in text
    assert "schedule:" not in text
    assert "permissions:\n  contents: read" in text

    forbidden = (
        "contents: write",
        "pages: write",
        "issues: write",
        "pull-requests: write",
        "id-token: write",
        "secrets.",
        "github.token",
        "GITHUB_TOKEN",
        "pull_request_target:",
    )
    assert [value for value in forbidden if value in text] == []


def test_docs_bootstrap_generates_then_proves_lockfile_on_github_runner():
    text = WORKFLOW.read_text(encoding="utf-8")
    required = (
        'node-version: "22"',
        "npm install --package-lock-only --ignore-scripts",
        "npm ci",
        "npm run typecheck",
        "npm run build",
        "npm run build -- --locale es",
        "npm run build -- --locale en",
        "path: website/package-lock.json",
        "retention-days: 3",
    )
    assert [value for value in required if value not in text] == []

    assert text.index("npm install --package-lock-only --ignore-scripts") < text.index("npm ci")
    assert text.index("npm ci") < text.index("npm run typecheck")
    assert text.index("npm run typecheck") < text.index("npm run build")


def test_docs_bootstrap_cannot_touch_tariff_pipeline_or_publish_releases():
    text = WORKFLOW.read_text(encoding="utf-8")
    forbidden = (
        "official-data-pipeline",
        "run_official_pipeline",
        "build_official_dataset",
        "publish_release",
        "gh release",
        "git push",
        "deploy-pages",
        "configure-pages",
    )
    assert [value for value in forbidden if value in text] == []


def test_docs_bootstrap_external_actions_are_full_sha_pinned():
    text = WORKFLOW.read_text(encoding="utf-8")
    expected = (
        "actions/checkout@3d3c42e5aac5ba805825da76410c181273ba90b1",
        "actions/setup-node@820762786026740c76f36085b0efc47a31fe5020",
        "actions/upload-artifact@043fb46d1a93c77aae656e7c1c64a875d1fc6a0a",
    )
    assert [value for value in expected if value not in text] == []
