from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys
import venv


ROOT = Path(__file__).resolve().parents[2]
PROBE = ROOT / "scripts" / "package_consumer_probe.py"


def _clean_env() -> dict[str, str]:
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    env.pop("PYTHONHOME", None)
    env["PYTHONNOUSERSITE"] = "1"
    return env


def _venv_python(path: Path) -> Path:
    return path / ("Scripts/python.exe" if os.name == "nt" else "bin/python")


def test_probe_rejects_import_from_forbidden_checkout_root(tmp_path: Path) -> None:
    env = _clean_env()
    env["PYTHONPATH"] = str(ROOT / "src")
    completed = subprocess.run(
        [
            sys.executable,
            str(PROBE),
            "--expected-version",
            "0.2.1",
            "--forbid-root",
            str(ROOT),
        ],
        cwd=tmp_path,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 2, completed.stdout + completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["status"] == "error"
    assert payload["check"] == "import_origin"
    assert "checkout" in payload["message"].lower()
    assert str(ROOT / "src" / "arancel_mx") in payload["import_origin"]


def test_probe_rejects_editable_src_layout(tmp_path: Path) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            str(PROBE),
            "--expected-version",
            "0.2.1",
            "--forbid-src-layout",
        ],
        cwd=tmp_path,
        env=_clean_env(),
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 2, completed.stdout + completed.stderr
    payload = json.loads(completed.stdout)
    assert payload["status"] == "error"
    assert payload["check"] == "import_origin"
    assert payload["import_origin"].replace("\\", "/").endswith("src/arancel_mx/__init__.py")


def test_probe_reports_version_mismatch_explicitly(tmp_path: Path) -> None:
    completed = subprocess.run(
        [
            sys.executable,
            str(PROBE),
            "--expected-version",
            "99.99.99",
        ],
        cwd=tmp_path,
        env=_clean_env(),
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 2
    payload = json.loads(completed.stdout)
    assert payload["status"] == "error"
    assert payload["check"] == "version"
    assert payload["expected_version"] == "99.99.99"
    assert payload["actual_version"] == "0.2.1"


def test_probe_succeeds_from_fresh_working_directory_with_wheel_install(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    subprocess.run(
        [sys.executable, "-m", "build", "--wheel", "--outdir", str(dist)],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    wheel = next(dist.glob("arancel_mx-0.2.1-*.whl"))

    environment = tmp_path / "venv"
    venv.EnvBuilder(with_pip=True, clear=True).create(environment)
    python = _venv_python(environment)
    subprocess.run(
        [str(python), "-m", "pip", "install", "--disable-pip-version-check", str(wheel)],
        cwd=tmp_path,
        env=_clean_env(),
        check=True,
        capture_output=True,
        text=True,
    )

    external = tmp_path / "external consumer ñ"
    external.mkdir()
    completed = subprocess.run(
        [
            str(python),
            str(PROBE),
            "--expected-version",
            "0.2.1",
            "--forbid-root",
            str(ROOT),
        ],
        cwd=external,
        env=_clean_env(),
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr + completed.stdout
    payload = json.loads(completed.stdout)
    assert payload["status"] == "ok"
    assert payload["version"] == "0.2.1"
    assert payload["import_origin"]
    assert not Path(payload["import_origin"]).resolve().is_relative_to(ROOT.resolve())


def test_probe_opens_local_dataset_and_runs_suggest(tmp_path: Path) -> None:
    from tests.consumer.conftest import create_consumer_duckdb

    dataset = create_consumer_duckdb(tmp_path / "arancel_mx.duckdb")
    env = _clean_env()
    env["PYTHONPATH"] = str(ROOT / "src")
    completed = subprocess.run(
        [
            sys.executable,
            str(PROBE),
            "--expected-version",
            "0.2.1",
            "--dataset",
            str(dataset),
        ],
        cwd=tmp_path,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr + completed.stdout
    payload = json.loads(completed.stdout)
    assert payload["status"] == "ok"
    assert payload["lookup_code"] == "01012101"
    assert payload["suggest_count"] == 1
    assert payload["suggest_code"] == "01012101"
    assert payload["suggest_scorer_version"] == "1"
