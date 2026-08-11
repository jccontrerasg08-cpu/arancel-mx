from __future__ import annotations

from pathlib import Path
import re
import tomllib


ROOT = Path(__file__).resolve().parents[1]
PYPROJECT = ROOT / "pyproject.toml"
CONSTRAINTS = ROOT / "requirements" / "production-build.txt"
_EXACT = re.compile(r"^[A-Za-z0-9_.-]+==[^=<>!~\s]+$")


def test_public_runtime_dependencies_remain_compatibility_ranges():
    payload = tomllib.loads(PYPROJECT.read_text(encoding="utf-8"))
    dependencies = payload["project"]["dependencies"]

    assert dependencies
    assert all("==" not in dependency for dependency in dependencies)
    assert any(dependency.startswith("duckdb>=") for dependency in dependencies)
    assert any(dependency.startswith("pandas>=") for dependency in dependencies)
    assert any(dependency.startswith("requests>=") for dependency in dependencies)


def test_production_environment_remains_exactly_pinned():
    rows = [
        line.strip()
        for line in CONSTRAINTS.read_text(encoding="utf-8").splitlines()
        if line.strip() and not line.lstrip().startswith("#")
    ]

    assert rows
    assert all(_EXACT.fullmatch(row) for row in rows)


def test_dependency_policy_has_distinct_consumer_and_production_contracts():
    docs = (ROOT / "docs" / "reproducibility.md").read_text(encoding="utf-8").lower()
    assert "consumer compatibility -> ranges" in docs
    assert "production reproducibility -> exact pins" in docs
