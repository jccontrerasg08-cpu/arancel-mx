from __future__ import annotations

import os
from pathlib import Path
import subprocess
import sys

from arancel_mx.cli import main
from arancel_mx.consumer.wco_support import chapter_pdf_url


ROOT = Path(__file__).resolve().parents[2]
WCO_01 = chapter_pdf_url("01")

SUGGEST_REPRODUCTORES_TABLE = f"""\
This is not a classification. Retrieve-only matches from the official dataset. WCO is not LIGIE/NICO authority.
--- 1/1  01012101  score=330  confidence=1.0  scorer=1 ---
Código      0101.21.01
Nivel       Fracción
Sección     I  Animales vivos y productos del reino animal
Capítulo    01  Animales vivos
Partida     01.01  Caballos, asnos, mulos y burdéganos, vivos
Subpartida  0101.21  Reproductores de raza pura
Fracción    0101.21.01  Reproductores de raza pura
UM          Cbza
IGI         10
IGE         Ex.
Hijos       1
NICO        0101.21.01 00  Reproductores de raza pura
Notas nacionales  (none)
WCO support  {WCO_01}
"""


def test_cli_suggest_table_against_local_duckdb_matches_golden(
    consumer_duckdb: Path,
    capsys,
) -> None:
    assert main(["suggest", "reproductores", "--dataset", str(consumer_duckdb)]) == 0
    captured = capsys.readouterr()
    assert captured.err == ""
    assert captured.out == SUGGEST_REPRODUCTORES_TABLE


def test_cli_suggest_missing_local_duckdb_fails_closed(tmp_path: Path, capsys) -> None:
    missing = tmp_path / "missing.duckdb"
    assert main(["suggest", "reproductores", "--dataset", str(missing)]) == 2
    err = capsys.readouterr().err
    assert "error:" in err
    assert "invalid data release tag" not in err


def test_subprocess_cli_suggest_uses_this_checkout_src(
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
            "suggest",
            "reproductores",
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
    assert completed.stdout == SUGGEST_REPRODUCTORES_TABLE
