from __future__ import annotations

from pathlib import Path
import re
import tomllib


ROOT = Path(__file__).resolve().parents[1]
CONSTRAINTS = ROOT / "requirements" / "production-build.txt"
PYPROJECT = ROOT / "pyproject.toml"
DEPENDABOT = ROOT / ".github" / "dependabot.yml"
_EXACT = re.compile(r"^([A-Za-z0-9_.-]+)==([^=<>!~\s]+)$")


def _normalized(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def _constraint_rows() -> list[tuple[str, str]]:
    rows: list[tuple[str, str]] = []
    for raw in CONSTRAINTS.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        match = _EXACT.fullmatch(line)
        assert match is not None, f"production dependency is not exact: {line}"
        rows.append((_normalized(match.group(1)), match.group(2)))
    return rows


def _direct_dependency_names() -> set[str]:
    payload = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    project = payload["project"]
    specs = list(project["dependencies"]) + list(project["optional-dependencies"]["dev"])
    return {
        _normalized(re.split(r"[<>=!~;\s\[]", spec, maxsplit=1)[0])
        for spec in specs
    }


def test_production_constraints_exist_and_are_exact_without_duplicates():
    assert CONSTRAINTS.is_file()
    rows = _constraint_rows()
    names = [name for name, _version in rows]

    assert rows
    assert len(names) == len(set(names))


def test_every_direct_runtime_and_dev_dependency_has_exact_constraint():
    constrained = {name for name, _version in _constraint_rows()}

    assert _direct_dependency_names() <= constrained


def test_official_python_toolchain_is_exactly_pinned():
    payload = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    assert payload["build-system"]["requires"] == ["setuptools==83.0.0"]

    constrained = dict(_constraint_rows())
    assert constrained["pip"] == "26.2.1"
    assert constrained["setuptools"] == "83.0.0"


def test_ci_uses_exact_pip_and_constraints_file():
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")

    assert "python -m pip install pip==26.2.1" in workflow
    assert 'python -m pip install -c requirements/production-build.txt -e ".[dev]"' in workflow
    assert "python -m pip install --upgrade pip" not in workflow


def test_ci_probes_declared_duckdb_floor_in_isolated_environment():
    workflow = (ROOT / ".github" / "workflows" / "ci.yml").read_text(encoding="utf-8")
    payload = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))

    assert "duckdb>=1.1" in payload["project"]["dependencies"]
    assert "python -m venv /tmp/arancel-duckdb-1.1.0" in workflow
    assert "/tmp/arancel-duckdb-1.1.0/bin/python -m pip install duckdb==1.1.0" in workflow
    assert "/tmp/arancel-duckdb-1.1.0/bin/python scripts/check_duckdb_compat.py" in workflow


def test_dependabot_updates_python_and_actions_weekly_without_credentials():
    assert DEPENDABOT.is_file()
    config = DEPENDABOT.read_text(encoding="utf-8")

    assert re.search(r"^version:\s*2\s*$", config, re.MULTILINE)
    assert config.count('package-ecosystem: "pip"') == 1
    assert config.count('package-ecosystem: "github-actions"') == 1
    assert config.count('directory: "/"') == 2
    assert config.count("interval: weekly") == 2
    assert config.count("day: monday") == 2
    assert config.count("open-pull-requests-limit: 5") == 2
    assert "dependencies" in config
    assert "python" in config
    assert "github-actions" in config

    lowered = config.lower()
    forbidden = (
        "registries:",
        "username:",
        "password:",
        "token:",
        "secrets.",
        "${{ secrets",
    )
    assert [value for value in forbidden if value in lowered] == []
