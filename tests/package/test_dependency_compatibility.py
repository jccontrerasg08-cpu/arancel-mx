from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

from packaging.requirements import Requirement
from packaging.version import Version
import tomllib

from tests.consumer.conftest import create_consumer_duckdb


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "dependency_compatibility_probe.py"
EXPECTED_FLOORS = {
    "duckdb": "1.1.0",
    "filelock": "3.16.0",
    "requests": "2.32.0",
}


def _clean_env() -> dict[str, str]:
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    env.pop("PYTHONHOME", None)
    env["PYTHONNOUSERSITE"] = "1"
    return env


def _build_wheel(tmp_path: Path) -> Path:
    dist = tmp_path / "dist"
    subprocess.run(
        [sys.executable, "-m", "build", "--wheel", "--outdir", str(dist)],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    return next(dist.glob("arancel_mx-0.2.1-*.whl"))


def _dataset(tmp_path: Path) -> Path:
    return create_consumer_duckdb(
        tmp_path / "fixture ñ" / "arancel_mx.duckdb",
        dataset_version="2026.08.11",
        schema_version="2",
    )


def _run_probe(tmp_path: Path, *, mode: str) -> dict[str, object]:
    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            str(_build_wheel(tmp_path)),
            "--mode",
            mode,
            "--expected-version",
            "0.2.1",
            "--dataset",
            str(_dataset(tmp_path)),
        ],
        cwd=tmp_path,
        env=_clean_env(),
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    return json.loads(completed.stdout)


def test_declared_runtime_minima_match_certified_floor_configuration() -> None:
    project = tomllib.loads(Path("pyproject.toml").read_text(encoding="utf-8"))["project"]
    declared: dict[str, Version] = {}
    for raw in project["dependencies"]:
        requirement = Requirement(raw)
        lower_bounds = [
            Version(spec.version)
            for spec in requirement.specifier
            if spec.operator in {">=", "=="}
        ]
        assert len(lower_bounds) == 1, raw
        declared[requirement.name.lower()] = lower_bounds[0]
    assert declared == {name: Version(version) for name, version in EXPECTED_FLOORS.items()}


def test_minimum_runtime_dependency_set_installs_and_queries(tmp_path: Path) -> None:
    report = _run_probe(tmp_path, mode="floor")
    assert report["status"] == "ok"
    assert report["mode"] == "floor"
    assert report["pip_check"] == "ok"
    for name, version in EXPECTED_FLOORS.items():
        assert Version(report["resolved"][name]) == Version(version)
    assert report["probe"]["lookup_code"] == "01012101"


def test_latest_allowed_runtime_dependency_set_installs_and_queries(tmp_path: Path) -> None:
    report = _run_probe(tmp_path, mode="latest")
    assert report["status"] == "ok"
    assert report["mode"] == "latest"
    assert report["pip_check"] == "ok"
    for name, floor in EXPECTED_FLOORS.items():
        assert name in report["resolved"]
        assert Version(report["resolved"][name]) >= Version(floor)
    assert report["probe"]["lookup_code"] == "01012101"


def test_dependency_probe_has_no_repository_runtime_constraints() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    assert "production-build.txt" not in source
    assert "requirements/" not in source
    assert "--constraint" not in source
