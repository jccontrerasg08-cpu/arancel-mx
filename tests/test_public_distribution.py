from __future__ import annotations

from pathlib import Path
import re
import subprocess


ROOT = Path(__file__).resolve().parents[1]


def _tracked_files() -> list[str]:
    return subprocess.check_output(
        ["git", "ls-files"], cwd=ROOT, text=True
    ).splitlines()


def test_private_paths_are_not_distributed() -> None:
    private_paths = (
        ".env",
        "token.txt",
        "docs/superpowers",
        "PIPELINE.md",
        "integrar_recaudacion_anam.py",
    )

    assert [path for path in private_paths if (ROOT / path).exists()] == []


def test_generated_and_local_paths_are_ignored() -> None:
    ignored_paths = (
        ".venv/probe",
        ".pytest_cache/probe",
        ".worktrees/probe",
        ".codebase-memory/config.json",
        ".vscode/probe",
        ".public-export/probe",
        "__pycache__/probe.pyc",
        "data/raw/probe.xlsx",
        "data/state/probe.sqlite",
        "data/alerts/probe.json",
        "data/embedded/probe.duckdb",
        "data/releases/probe.json",
        "dist/arancel_mx.whl",
        "build/probe",
        "src/arancel_mx.egg-info/PKG-INFO",
        "local.duckdb",
        ".env.local",
    )

    for path in ignored_paths:
        result = subprocess.run(
            ["git", "check-ignore", "--quiet", path], cwd=ROOT, check=False
        )
        assert result.returncode == 0, path


def test_only_tariff_source_package_is_distributed() -> None:
    python_roots = {
        path.relative_to(ROOT / "src").parts[0]
        for path in (ROOT / "src").rglob("*.py")
    }

    assert python_roots == {"arancel_mx"}


def test_legacy_product_paths_are_absent() -> None:
    legacy_files = {"app.py", "banxico_directorio.py", "banxico_sie.py", "comex.py"}
    legacy_prefixes = ("assets/", "data/legal_corpus/", "src/comex/")
    existing = [
        path
        for path in _tracked_files()
        if (path in legacy_files or path.startswith(legacy_prefixes))
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
    for relative in _tracked_files():
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

    assert [path for path in required if not (ROOT / path).is_file()] == []


def test_official_dataset_build_entrypoints_are_public() -> None:
    required = (
        "scripts/build_official_dataset.py",
        ".github/workflows/build-official-dataset.yml",
    )

    assert [path for path in required if not (ROOT / path).is_file()] == []


def test_readme_describes_the_focused_public_project() -> None:
    readme = " ".join((ROOT / "README.md").read_text(encoding="utf-8").lower().split())
    required = (
        "arancel-mx",
        "apache-2.0",
        "python -m arancel_mx",
        "contributing.md",
        "security.md",
        "no constituye asesoría legal",
        "fuentes oficiales",
        "## alcance",
        "## instalación",
        "## uso desde python",
        "## estructura del repositorio",
        "## pruebas",
    )

    assert [phrase for phrase in required if phrase not in readme] == []


def test_readme_preserves_existing_public_information() -> None:
    readme = (ROOT / "README.md").read_text(encoding="utf-8").lower()
    required = (
        "docs/demo.gif",
        "docs/dof_timeline.png",
        "docs/dof_timeline2.png",
        "docs/nico_flow.png",
        "src/arancel_mx/sources/source_registry.json",
        "docs/",
        "tests/",
        "license",
        "notice",
        "propuestas nico",
        "capture manifests y hashes",
        "https://www.diputados.gob.mx/leyesbiblio/ref/ligie_2022.htm",
        "https://www.snice.gob.mx/cs/avi/snice/ligie.info22.html",
        "https://www.snice.gob.mx/cs/avi/snice/ligie.nico2022.html",
        "https://www.snice.gob.mx/cs/avi/snice/ligie.notasnac22.html",
        "https://www.snice.gob.mx/cs/avi/snice/ligie.indicaranc22.html",
        "https://www.dof.gob.mx/nota_detalle.php?codigo=5656249&fecha=27/06/2022",
        "python -m arancel_mx --help",
        "python -m arancel_mx build --database data/arancel.duckdb --output-dir out/release",
        "python -m arancel_mx update --state-path data/update_state/ligie.json --report-path out/update.json",
        "python -m arancel_mx reconcile --ledger-json ledger.json --dof-json dof.json --snice-json snice.json",
        "python -m arancel_mx release --release-dir out/release --source-dir data/raw/release --latest-dir out/latest",
        "python -m pytest -q",
        "python -m build",
        "diputados",
        "snice",
        "diario oficial de la federación",
        "comunidad de código abierto",
    )

    assert [value for value in required if value not in readme] == []


def test_readmes_document_verified_official_dataset_build() -> None:
    spanish = (ROOT / "README.md").read_text(encoding="utf-8").lower()
    english = (ROOT / "README.en.md").read_text(encoding="utf-8").lower()
    release_process = (ROOT / "docs" / "release-process.md").read_text(encoding="utf-8").lower()
    required = (
        "scripts/build_official_dataset.py",
        ".github/workflows/build-official-dataset.yml",
        "build official dataset",
        "arancel_mx.duckdb",
        "arancel_mx.csv",
        "arancel_mx.json",
        "manifest.json",
        "sha256sums",
        "official-sources.tar.gz",
    )

    for document in (spanish, english, release_process):
        assert [value for value in required if value not in document] == []
    assert "construcción end-to-end de dataset oficial" in spanish
    assert "end-to-end official dataset build" in english
    assert "manual" in release_process


def test_bilingual_readmes_stay_linked() -> None:
    spanish = (ROOT / "README.md").read_text(encoding="utf-8").lower()
    english_path = ROOT / "README.en.md"
    assert english_path.is_file()
    english = english_path.read_text(encoding="utf-8").lower()

    assert "readme.en.md" in spanish
    assert "readme.md" in english
    assert "english" in spanish
    assert "español" in english


def test_focused_documentation_exists_and_has_no_legacy_instructions() -> None:
    required = (
        "docs/data-model.md",
        "docs/sources.md",
        "docs/release-process.md",
    )
    assert [path for path in required if not (ROOT / path).is_file()] == []

    documentation = "\n".join(
        path.read_text(encoding="utf-8").lower()
        for path in (ROOT / "docs").glob("*.md")
    ) + (ROOT / "README.md").read_text(encoding="utf-8").lower()
    forbidden = ("banxico", "maplibre", "python app.py", "docker compose", "dashboard")
    assert [value for value in forbidden if value in documentation] == []


def test_ci_workflow_builds_package_without_secrets_or_network_updates() -> None:
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    required = (
        "pull_request:",
        "push:",
        "contents: read",
        "actions/checkout@d23441a48e516b6c34aea4fa41551a30e30af803",
        "actions/setup-python@ece7cb06caefa5fff74198d8649806c4678c61a1",
        'python-version: "3.11"',
        "python -m pip install --upgrade pip",
        'python -m pip install -e ".[dev]"',
        "python -m pytest -q",
        "python -m build",
        "git diff --check",
    )
    forbidden = (
        "contents: write",
        "pull_request_target:",
        "secrets.",
        "git push",
        "python -m arancel_mx update",
    )

    assert [value for value in required if value not in workflow] == []
    assert [value for value in forbidden if value in workflow] == []
