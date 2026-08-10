from __future__ import annotations

from pathlib import Path
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


def test_environment_example_contains_placeholders_only() -> None:
    values = {}
    for raw_line in (ROOT / ".env.example").read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        values[key] = value

    assert values["BANXICO_TOKEN"] == "PASTE_YOUR_BANXICO_TOKEN_HERE"
    assert values["GROQ_API_KEY"] == "PASTE_YOUR_GROQ_API_KEY_HERE"


def test_uncertain_country_geojson_is_not_referenced() -> None:
    javascript = (ROOT / "assets" / "maplibre_dashboard.js").read_text(
        encoding="utf-8"
    )

    assert "world-countries-simplified.geojson" not in javascript


def test_open_source_governance_files_are_present() -> None:
    required = (
        "LICENSE",
        "NOTICE",
        "CONTRIBUTING.md",
        "SECURITY.md",
        "CODE_OF_CONDUCT.md",
        "THIRD_PARTY_LICENSES/MapLibre-GL-JS.txt",
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
