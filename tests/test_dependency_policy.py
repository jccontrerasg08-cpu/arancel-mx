from __future__ import annotations

from pathlib import Path
import re
import tomllib


ROOT = Path(__file__).resolve().parents[1]
CONSTRAINTS = ROOT / "requirements" / "production-build.txt"
PYPROJECT = ROOT / "pyproject.toml"
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
