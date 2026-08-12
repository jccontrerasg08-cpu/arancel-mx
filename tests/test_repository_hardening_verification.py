from __future__ import annotations

from pathlib import Path
import re
import subprocess


ROOT = Path(__file__).resolve().parents[1]
WORKFLOWS = ROOT / ".github" / "workflows"
_FULL_SHA_ACTION = re.compile(r"^\s*uses:\s*[^@\s]+@([0-9a-f]{40})(?:\s|#|$)", re.MULTILINE)
_ANY_ACTION = re.compile(r"^\s*uses:\s*[^@\s]+@([^\s#]+)", re.MULTILINE)
_REMOTE_SHELL_PIPE = re.compile(
    r"(?:curl|wget)[^\n|]*\|[^\n]*(?:bash|sh)(?:\s|$)", re.IGNORECASE
)


def _workflow_texts() -> dict[str, str]:
    return {
        path.name: path.read_text(encoding="utf-8")
        for path in sorted((*WORKFLOWS.glob("*.yml"), *WORKFLOWS.glob("*.yaml")))
    }


def _job_start(workflow: str, job: str) -> int:
    match = re.search(rf"^  {re.escape(job)}:$", workflow, re.MULTILINE)
    assert match is not None, job
    return match.start()


def _tracked_files() -> list[str]:
    return subprocess.check_output(
        ["git", "ls-files"], cwd=ROOT, text=True
    ).splitlines()


def test_every_external_action_ref_is_an_immutable_commit_sha():
    workflows = _workflow_texts()
    assert workflows

    for name, text in workflows.items():
        all_refs = _ANY_ACTION.findall(text)
        pinned_refs = _FULL_SHA_ACTION.findall(text)
        assert len(pinned_refs) == len(all_refs), (name, all_refs)
        assert all(re.fullmatch(r"[0-9a-f]{40}", ref) for ref in pinned_refs), name


def test_workflows_contain_no_high_risk_shortcuts():
    forbidden_literals = (
        "pull_request_target:",
        "permissions: write-all",
        "write-all",
        "|| true",
        "secrets.",
        "actions/checkout@v",
        "actions/setup-python@v",
        "actions/setup-node@v",
        "actions/upload-artifact@v",
        "actions/download-artifact@v",
    )

    for name, text in _workflow_texts().items():
        assert [value for value in forbidden_literals if value in text] == [], name
        assert _REMOTE_SHELL_PIPE.search(text) is None, name


def test_official_python_jobs_share_the_reviewed_constraints_file():
    ci = (WORKFLOWS / "ci.yml").read_text(encoding="utf-8")
    production = (WORKFLOWS / "official-data-pipeline.yml").read_text(encoding="utf-8")
    development = 'python -m pip install -c requirements/production-build.txt -e ".[dev]"'

    assert development in ci
    assert "python -m pip install pip==26.2.1" in ci
    assert production.count("python -m pip install pip==26.2.1") == 3
    assert "python -m pip install --upgrade" not in production


def test_only_the_read_only_build_job_installs_development_tooling():
    production = (WORKFLOWS / "official-data-pipeline.yml").read_text(encoding="utf-8")
    development = 'python -m pip install -c requirements/production-build.txt -e ".[dev]"'
    runtime = "python -m pip install -c requirements/production-build.txt -e ."
    build_block = production[
        _job_start(production, "build-and-verify") : _job_start(production, "publish")
    ]

    assert development in build_block
    assert production.count(development) == 1
    assert production.count(f"{runtime}\n") == 2


def test_generated_official_data_and_local_secrets_are_not_tracked():
    tracked = _tracked_files()
    forbidden_exact = {".env", "token.txt"}
    forbidden_prefixes = (
        "data/raw/",
        "data/embedded/",
        "data/releases/",
        "data/state/",
        "out/",
        "dist/",
        "build/",
    )
    forbidden_suffixes = (".duckdb", ".sqlite", ".sqlite3")

    violations = [
        path
        for path in tracked
        if path in forbidden_exact
        or path.startswith(forbidden_prefixes)
        or path.endswith(forbidden_suffixes)
    ]
    assert violations == []


def test_production_write_permissions_remain_job_scoped():
    production = (WORKFLOWS / "official-data-pipeline.yml").read_text(encoding="utf-8")
    ci = (WORKFLOWS / "ci.yml").read_text(encoding="utf-8")

    assert production.count("contents: write") == 1
    assert production.count("issues: write") == 1
    assert "pull-requests: write" not in production
    assert "contents: write" not in ci
    assert "issues: write" not in ci
    assert "pull-requests: write" not in ci
