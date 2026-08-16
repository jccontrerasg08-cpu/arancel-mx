from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

from tests.consumer.conftest import create_consumer_duckdb


ROOT = Path(__file__).resolve().parents[2]
CERTIFIER = ROOT / "scripts" / "certify_package_install.py"


def _clean_env() -> dict[str, str]:
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    env.pop("PYTHONHOME", None)
    env["PYTHONNOUSERSITE"] = "1"
    return env


def test_sdist_rebuilds_wheel_outside_checkout_and_rebuilt_wheel_passes_probe(
    tmp_path: Path,
) -> None:
    dist = tmp_path / "source dist"
    subprocess.run(
        [sys.executable, "-m", "build", "--sdist", "--outdir", str(dist)],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    sdist = next(dist.glob("arancel_mx-0.3.0.tar.gz"))

    rebuild_dir = tmp_path / "isolated rebuild ñ"
    rebuild_dir.mkdir()
    wheels = rebuild_dir / "wheels"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "pip",
            "wheel",
            "--disable-pip-version-check",
            "--no-deps",
            "--wheel-dir",
            str(wheels),
            str(sdist),
        ],
        cwd=rebuild_dir,
        env=_clean_env(),
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    rebuilt = next(wheels.glob("arancel_mx-0.3.0-py3-none-any.whl"))
    assert not rebuilt.resolve().is_relative_to(ROOT.resolve())

    dataset = create_consumer_duckdb(
        tmp_path / "fixture" / "arancel_mx.duckdb",
        dataset_version="2026.08.11",
        schema_version="2",
    )
    certified = subprocess.run(
        [
            sys.executable,
            str(CERTIFIER),
            str(rebuilt),
            "--expected-version",
            "0.3.0",
            "--dataset",
            str(dataset),
        ],
        cwd=rebuild_dir,
        env=_clean_env(),
        text=True,
        capture_output=True,
        check=False,
    )
    assert certified.returncode == 0, certified.stdout + certified.stderr
    assert '"status":"ok"' in certified.stdout
    assert '"lookup_code":"01012101"' in certified.stdout


def test_sdist_can_be_installed_directly_by_clean_certifier(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    subprocess.run(
        [sys.executable, "-m", "build", "--sdist", "--outdir", str(dist)],
        cwd=ROOT,
        check=True,
        text=True,
        capture_output=True,
    )
    sdist = next(dist.glob("arancel_mx-0.3.0.tar.gz"))
    completed = subprocess.run(
        [sys.executable, str(CERTIFIER), str(sdist), "--expected-version", "0.3.0"],
        cwd=tmp_path,
        env=_clean_env(),
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stdout + completed.stderr
    assert '"status":"ok"' in completed.stdout
