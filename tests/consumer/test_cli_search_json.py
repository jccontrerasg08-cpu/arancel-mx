from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

from arancel_mx.cli import main


ROOT = Path(__file__).resolve().parents[2]

SEARCH_REPRODUCTORES_JSON = """\
[{"confidence":1.0,"match_kind":"description","record":{"code":"010121","dataset_version":"2026.08.11","description":"Reproductores de raza pura","effective_from":"2026-04-20","effective_to":null,"fraccion8":null,"hs2":"01","hs4":"0101","hs6":"010121","ige_kind":null,"ige_text":null,"ige_value":null,"igi_kind":null,"igi_text":null,"igi_value":null,"is_current":true,"level":"hs6","ligie_version":"LIGIE-2022","nico10":null,"nico2":null,"parent_code":"0101","schema_version":"2","unit_name":null,"validity_basis":"legal"},"score":330,"scorer_version":"1"}]
"""


def test_cli_search_json_against_local_duckdb_matches_golden(
    consumer_duckdb: Path,
    capsys,
) -> None:
    assert main(
        [
            "search",
            "reproductores",
            "--limit",
            "1",
            "--format",
            "json",
            "--dataset",
            str(consumer_duckdb),
        ]
    ) == 0
    captured = capsys.readouterr()
    assert captured.err == ""
    assert captured.out == SEARCH_REPRODUCTORES_JSON
    first = json.loads(captured.out)[0]
    assert first["record"]["code"]
    assert first["scorer_version"] == "1"
    assert first["match_kind"] == "description"
    assert 0 <= first["confidence"] <= 1


def test_subprocess_cli_search_json_uses_this_checkout_src(
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
            "--format",
            "json",
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
    assert completed.stdout == SEARCH_REPRODUCTORES_JSON
