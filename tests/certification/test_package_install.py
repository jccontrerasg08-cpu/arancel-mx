from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

import pytest

from scripts import certify_package_install as certifier
from scripts.certify_package_install import smoke_commands
from tests.consumer.conftest import create_consumer_duckdb


ROOT = Path(__file__).resolve().parents[2]
CERTIFIER = ROOT / "scripts" / "certify_package_install.py"


def _clean_env() -> dict[str, str]:
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    env.pop("PYTHONHOME", None)
    env["PYTHONNOUSERSITE"] = "1"
    return env


def test_dataset_requires_expected_version() -> None:
    # A dataset probe without an expected version would only check file existence,
    # so certification could pass without ever querying the dataset.
    with pytest.raises(SystemExit):
        certifier._parse_args(
            ["dist/arancel_mx-0.3.3-py3-none-any.whl", "--dataset", "local.duckdb"]
        )


def test_smoke_commands_cover_installed_package_surfaces(tmp_path: Path) -> None:
    commands = smoke_commands(
        Path("dist/arancel_mx-0.3.3-py3-none-any.whl"),
        tmp_path / "venv",
    )
    rendered = [" ".join(command) for command in commands]

    assert any("-m pip check" in item for item in rendered)
    assert any("import arancel_mx" in item for item in rendered)
    assert any("-m arancel_mx --help" in item for item in rendered)
    assert any("arancel-mx" in item and "--help" in item for item in rendered)
    assert any("importlib.resources" in item and "source_registry.json" in item for item in rendered)
    assert any("pandas" in item and "openpyxl" in item and "find_spec" in item for item in rendered)


def test_clean_wheel_install_runs_probe_with_local_dataset(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    subprocess.run(
        [sys.executable, "-m", "build", "--wheel", "--outdir", str(dist)],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    wheel = next(dist.glob("arancel_mx-0.3.3-*.whl"))
    dataset = create_consumer_duckdb(
        tmp_path / "fixture ñ" / "arancel_mx.duckdb",
        dataset_version="2026.08.11",
        schema_version="2",
    )

    completed = subprocess.run(
        [
            sys.executable,
            str(CERTIFIER),
            str(wheel),
            "--expected-version",
            "0.3.3",
            "--dataset",
            str(dataset),
        ],
        cwd=tmp_path,
        env=_clean_env(),
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert '"status":"ok"' in completed.stdout
    assert '"lookup_code":"01012101"' in completed.stdout
    assert '"suggest_code":"01012101"' in completed.stdout
    assert '"suggest_scorer_version":"1"' in completed.stdout
