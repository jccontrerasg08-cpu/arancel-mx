from __future__ import annotations

from pathlib import Path
import re
import tomllib


ROOT = Path(__file__).resolve().parents[2]
PYPROJECT = ROOT / "pyproject.toml"
CONSTRAINTS = ROOT / "requirements" / "production-build.txt"
CI = ROOT / ".github" / "workflows" / "ci.yml"

QUALITY_TOOLS = ("ruff", "mypy", "pytest-cov")
_EXACT = re.compile(r"^([A-Za-z0-9_.-]+)==([^=<>!~\s]+)$")
_JOB_HEADER = re.compile(r"(?m)^  ([A-Za-z0-9_-]+):$")


def _normalized(name: str) -> str:
    return re.sub(r"[-_.]+", "-", name).lower()


def _payload() -> dict[str, object]:
    return tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))


def _dev_dependency_names() -> set[str]:
    project = _payload()["project"]
    specs = project["optional-dependencies"]["dev"]
    return {
        _normalized(re.split(r"[<>=!~;\s\[]", spec, maxsplit=1)[0])
        for spec in specs
    }


def _constraint_pins() -> dict[str, str]:
    pins: dict[str, str] = {}
    for raw in CONSTRAINTS.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        match = _EXACT.fullmatch(line)
        assert match is not None, f"production dependency is not exact: {line}"
        pins[_normalized(match.group(1))] = match.group(2)
    return pins


def _ci_test_job() -> str:
    workflow = CI.read_text(encoding="utf-8")
    header = re.search(r"(?m)^  test:$", workflow)
    assert header is not None, "CI workflow must keep the required job named test"
    start = header.start()
    following = [
        match.start()
        for match in _JOB_HEADER.finditer(workflow[header.end() :])
    ]
    end = header.end() + following[0] if following else len(workflow)
    return workflow[start:end]


def test_quality_tools_are_declared_in_the_dev_extra() -> None:
    dev = _dev_dependency_names()
    missing = [name for name in QUALITY_TOOLS if _normalized(name) not in dev]
    assert missing == []


def test_quality_tools_have_exact_production_pins() -> None:
    pins = _constraint_pins()
    missing = [name for name in QUALITY_TOOLS if _normalized(name) not in pins]
    assert missing == []


def test_ci_test_job_runs_ruff_mypy_and_pytest_coverage_after_install() -> None:
    job = _ci_test_job()
    install = 'python -m pip install -c requirements/production-build.txt -e ".[dev]"'
    ruff = "python -m ruff check src tests scripts"
    mypy = (
        "python -m mypy src/arancel_mx/consumer src/arancel_mx/api "
        "src/arancel_mx/__init__.py"
    )
    pytest_cov = "python -m pytest -q --cov=arancel_mx --cov-report=term-missing"

    assert install in job
    assert ruff in job
    assert mypy in job
    assert pytest_cov in job
    assert "python -m pytest" in job
    assert job.index(install) < job.index(ruff) < job.index(mypy) < job.index(pytest_cov)


def test_ci_test_job_keeps_stable_check_run_name_and_python_311() -> None:
    workflow = CI.read_text(encoding="utf-8")
    job = _ci_test_job()

    assert re.search(r"(?m)^  test:$", workflow)
    assert "strategy:" not in job
    assert "matrix:" not in job
    assert 'python-version: "3.11"' in job
    assert "ruff format" not in job


def test_ruff_enables_a_small_rule_set() -> None:
    tool = _payload()["tool"]
    ruff = tool["ruff"]
    lint = ruff.get("lint", ruff)
    select = set(lint.get("select", ruff.get("select", [])))
    assert {"E9", "F63", "F7", "F82"} <= select


def test_mypy_targets_the_public_consumer_api() -> None:
    mypy = _payload()["tool"]["mypy"]
    assert mypy.get("ignore_missing_imports") is True
    assert mypy.get("python_version") == "3.11"


def test_coverage_floor_is_conservative() -> None:
    coverage = _payload()["tool"]["coverage"]
    report = coverage.get("report", coverage)
    floor = report.get("fail_under")
    assert isinstance(floor, (int, float))
    assert floor >= 50
