from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

from arancel_mx.cli import main


ROOT = Path(__file__).resolve().parents[2]

SEARCH_REPRODUCTORES_TABLE = """\
--- 1/1  010121  score=330  confidence=1.0  scorer=1 ---
0101.21  Subpartida  Reproductores de raza pura
"""


def test_cli_search_table_against_local_duckdb_matches_golden(
    consumer_duckdb: Path,
    capsys,
) -> None:
    assert main(
        ["search", "reproductores", "--limit", "1", "--dataset", str(consumer_duckdb)]
    ) == 0
    captured = capsys.readouterr()
    assert captured.err == ""
    assert captured.out == SEARCH_REPRODUCTORES_TABLE


def test_subprocess_cli_search_uses_this_checkout_src(
    consumer_duckdb: Path,
    tmp_path: Path,
) -> None:
    env = os.environ.copy()
    env.pop("PYTHONHOME", None)
    env["PYTHONPATH"] = str(ROOT / "src")
    env["PYTHONNOUSERSITE"] = "1"
    completed = subprocess.run(
        [
            sys.executable,
            "-m",
            "arancel_mx",
            "search",
            "reproductores",
            "--limit",
            "1",
            "--dataset",
            str(consumer_duckdb),
        ],
        cwd=tmp_path,
        env=env,
        text=True,
        capture_output=True,
        check=False,
    )
    assert completed.returncode == 0, completed.stderr
    assert completed.stderr == ""
    assert completed.stdout == SEARCH_REPRODUCTORES_TABLE
