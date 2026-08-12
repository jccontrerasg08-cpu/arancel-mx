from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

from tests.consumer.conftest import create_consumer_duckdb


ROOT = Path(__file__).resolve().parents[2]
SCRIPT = ROOT / "scripts" / "current_resolver_probe.py"


def _clean_env() -> dict[str, str]:
    env = os.environ.copy()
    env.pop("PYTHONPATH", None)
    env.pop("PYTHONHOME", None)
    env["PYTHONNOUSERSITE"] = "1"
    return env


def test_current_resolver_probe_records_normal_runtime_resolution(tmp_path: Path) -> None:
    dist = tmp_path / "dist"
    subprocess.run(
        [sys.executable, "-m", "build", "--wheel", "--outdir", str(dist)],
        cwd=ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    wheel = next(dist.glob("arancel_mx-0.2.0-*.whl"))
    dataset = create_consumer_duckdb(
        tmp_path / "fixture ñ" / "arancel_mx.duckdb",
        dataset_version="2026.08.11",
        schema_version="2",
    )

    completed = subprocess.run(
        [
            sys.executable,
            str(SCRIPT),
            str(wheel),
            "--expected-version",
            "0.2.0",
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
    report = json.loads(completed.stdout)
    assert report["status"] == "ok"
    assert report["resolved"]["arancel-mx"] == "0.2.0"
    for dependency in ("duckdb", "filelock", "platformdirs", "requests"):
        assert dependency in report["resolved"]
    for heavy in ("pandas", "openpyxl", "pymupdf", "xlrd"):
        assert heavy not in report["resolved"]
    assert report["probe"]["lookup_code"] == "01012101"


def test_current_resolver_probe_does_not_use_repository_constraints() -> None:
    source = SCRIPT.read_text(encoding="utf-8")
    assert "production-build.txt" not in source
    assert "requirements/" not in source
    assert "--constraint" not in source
    assert "' -c '" not in source
