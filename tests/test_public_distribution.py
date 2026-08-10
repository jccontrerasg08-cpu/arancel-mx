from __future__ import annotations

from pathlib import Path
import re
import subprocess


ROOT = Path(__file__).resolve().parents[1]


def test_private_and_generated_paths_are_not_distributed() -> None:
    private_paths = (
        ".env",
        "token.txt",
        "docs/superpowers",
        "PIPELINE.md",
        "integrar_recaudacion_anam.py",
        "data/banxico_sector1_scan.json",
        "data/banxico_sector1_scan_resumen.csv",
        "data/banxico_sector1_cuadros.json",
        "assets/world-countries-simplified.geojson",
    )
    generated_paths = (
        "data/raw/probe",
        "data/state/probe",
        "data/alerts/probe",
        "data/comex.duckdb",
        "data/embedded/probe",
        "data/releases/probe",
    )

    present = [path for path in private_paths if (ROOT / path).exists()]

    assert present == []
    for path in generated_paths:
        result = subprocess.run(
            ["git", "check-ignore", "--quiet", path],
            cwd=ROOT,
            check=False,
        )
        assert result.returncode == 0, path


def test_local_tooling_directories_are_ignored() -> None:
    local_paths = (
        ".venv/probe",
        ".worktrees/probe",
        ".codebase-memory/config.json",
        ".vscode/probe",
        ".public-export/probe",
    )

    for path in local_paths:
        result = subprocess.run(
            ["git", "check-ignore", "--quiet", path],
            cwd=ROOT,
            check=False,
        )
        assert result.returncode == 0, path


def test_only_tariff_source_package_is_distributed() -> None:
    python_roots = {
        path.relative_to(ROOT / "src").parts[0]
        for path in (ROOT / "src").rglob("*.py")
    }

    assert python_roots == {"arancel_mx"}


def test_legacy_product_paths_are_absent() -> None:
    legacy_paths = {
        "app.py",
        "banxico_directorio.py",
        "banxico_sie.py",
        "comex.py",
    }
    legacy_prefixes = ("assets/", "data/legal_corpus/", "src/comex/")
    tracked = subprocess.check_output(
        ["git", "ls-files"], cwd=ROOT, text=True
    ).splitlines()
    existing = [
        path
        for path in tracked
        if (path in legacy_paths or path.startswith(legacy_prefixes))
        and (ROOT / path).is_file()
    ]

    assert existing == []


def test_tracked_text_contains_no_credentials_or_private_absolute_paths() -> None:
    patterns = (
        re.compile(r"AKIA[0-9A-Z]{16}"),
        re.compile(r"gh[pousr]_[A-Za-z0-9]{36,}"),
        re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
        re.compile(r"[A-Za-z]:\\Users\\[^\\\s]+", re.IGNORECASE),
    )
    findings = []
    for relative in subprocess.check_output(
        ["git", "ls-files"], cwd=ROOT, text=True
    ).splitlines():
        path = ROOT / relative
        if not path.is_file():
            continue
        text = path.read_bytes().decode("utf-8", errors="ignore")
        for pattern in patterns:
            if pattern.search(text):
                findings.append((relative, pattern.pattern))

    assert findings == []


def test_open_source_governance_files_are_present() -> None:
    required = (
        "LICENSE",
        "NOTICE",
        "CONTRIBUTING.md",
        "SECURITY.md",
        "CODE_OF_CONDUCT.md",
        ".github/ISSUE_TEMPLATE/bug_report.yml",
        ".github/ISSUE_TEMPLATE/feature_request.yml",
        ".github/pull_request_template.md",
    )

    missing = [path for path in required if not (ROOT / path).is_file()]

    assert missing == []


def test_readme_describes_the_public_project() -> None:
    readme = " ".join(
        (ROOT / "README.md").read_text(encoding="utf-8").lower().split()
    )

    required_phrases = (
        "arancel-mx",
        "apache-2.0",
        ".env.example",
        "contributing.md",
        "security.md",
        "no constituye asesoría legal",
        "datos generados",
    )

    missing = [phrase for phrase in required_phrases if phrase not in readme]

    assert missing == []


def test_ci_workflow_is_read_only_and_pinned() -> None:
    workflow_path = ROOT / ".github" / "workflows" / "ci.yml"

    assert workflow_path.is_file()
    workflow = workflow_path.read_text(encoding="utf-8")

    required = (
        "pull_request:",
        "push:",
        "contents: read",
        "actions/checkout@d23441a48e516b6c34aea4fa41551a30e30af803",
        "actions/setup-python@ece7cb06caefa5fff74198d8649806c4678c61a1",
        'python-version: "3.12"',
        "python -m pytest -p no:cacheprovider -q",
        "python -m compileall -q src app.py comex.py run.py",
        "git diff --check",
    )
    forbidden = (
        "contents: write",
        "pull_request_target:",
        "secrets.",
        "git push",
    )

    assert [value for value in required if value not in workflow] == []
    assert [value for value in forbidden if value in workflow] == []
