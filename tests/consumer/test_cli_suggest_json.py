from __future__ import annotations

import json
import os
from pathlib import Path
import subprocess
import sys

from arancel_mx.cli import main


ROOT = Path(__file__).resolve().parents[2]

SUGGEST_REPRODUCTORES_JSON = """\
[{"disclaimer":"This is not a classification. Retrieve-only matches from the official dataset. WCO is not LIGIE/NICO authority.","ficha":{"children":[{"code":"0101210100","dataset_version":"2026.08.11","description":"Reproductores de raza pura","effective_from":"2026-04-20","effective_to":null,"fraccion8":"01012101","hs2":"01","hs4":"0101","hs6":"010121","ige_kind":"exento","ige_text":"Ex.","ige_value":0.0,"igi_kind":"ad_valorem","igi_text":"10","igi_value":10.0,"is_current":true,"level":"nico10","ligie_version":"LIGIE-2022","nico10":"0101210100","nico2":"00","parent_code":"01012101","schema_version":"2","unit_name":"Cbza","validity_basis":"legal"}],"formatted_code":"0101.21.01","hierarchy":[{"code":"01","dataset_version":"2026.08.11","description":"Animales vivos","effective_from":"2026-04-20","effective_to":null,"fraccion8":null,"hs2":"01","hs4":null,"hs6":null,"ige_kind":null,"ige_text":null,"ige_value":null,"igi_kind":null,"igi_text":null,"igi_value":null,"is_current":true,"level":"hs2","ligie_version":"LIGIE-2022","nico10":null,"nico2":null,"parent_code":null,"schema_version":"2","unit_name":null,"validity_basis":"legal"},{"code":"0101","dataset_version":"2026.08.11","description":"Caballos, asnos, mulos y burdéganos, vivos","effective_from":"2026-04-20","effective_to":null,"fraccion8":null,"hs2":"01","hs4":"0101","hs6":null,"ige_kind":null,"ige_text":null,"ige_value":null,"igi_kind":null,"igi_text":null,"igi_value":null,"is_current":true,"level":"hs4","ligie_version":"LIGIE-2022","nico10":null,"nico2":null,"parent_code":"01","schema_version":"2","unit_name":null,"validity_basis":"legal"},{"code":"010121","dataset_version":"2026.08.11","description":"Reproductores de raza pura","effective_from":"2026-04-20","effective_to":null,"fraccion8":null,"hs2":"01","hs4":"0101","hs6":"010121","ige_kind":null,"ige_text":null,"ige_value":null,"igi_kind":null,"igi_text":null,"igi_value":null,"is_current":true,"level":"hs6","ligie_version":"LIGIE-2022","nico10":null,"nico2":null,"parent_code":"0101","schema_version":"2","unit_name":null,"validity_basis":"legal"},{"code":"01012101","dataset_version":"2026.08.11","description":"Reproductores de raza pura","effective_from":"2026-04-20","effective_to":null,"fraccion8":"01012101","hs2":"01","hs4":"0101","hs6":"010121","ige_kind":"exento","ige_text":"Ex.","ige_value":0.0,"igi_kind":"ad_valorem","igi_text":"10","igi_value":10.0,"is_current":true,"level":"fraccion8","ligie_version":"LIGIE-2022","nico10":null,"nico2":null,"parent_code":"010121","schema_version":"2","unit_name":"Cbza","validity_basis":"legal"}],"record":{"code":"01012101","dataset_version":"2026.08.11","description":"Reproductores de raza pura","effective_from":"2026-04-20","effective_to":null,"fraccion8":"01012101","hs2":"01","hs4":"0101","hs6":"010121","ige_kind":"exento","ige_text":"Ex.","ige_value":0.0,"igi_kind":"ad_valorem","igi_text":"10","igi_value":10.0,"is_current":true,"level":"fraccion8","ligie_version":"LIGIE-2022","nico10":null,"nico2":null,"parent_code":"010121","schema_version":"2","unit_name":"Cbza","validity_basis":"legal"},"section":{"chapter_from":"01","chapter_to":"05","name":"Animales vivos y productos del reino animal","roman":"I","source":"hs_section_grouping"}},"national_notes":[],"search":{"confidence":1.0,"match_kind":"description","record":{"code":"01012101","dataset_version":"2026.08.11","description":"Reproductores de raza pura","effective_from":"2026-04-20","effective_to":null,"fraccion8":"01012101","hs2":"01","hs4":"0101","hs6":"010121","ige_kind":"exento","ige_text":"Ex.","ige_value":0.0,"igi_kind":"ad_valorem","igi_text":"10","igi_value":10.0,"is_current":true,"level":"fraccion8","ligie_version":"LIGIE-2022","nico10":null,"nico2":null,"parent_code":"010121","schema_version":"2","unit_name":"Cbza","validity_basis":"legal"},"score":330,"scorer_version":"1"}}]
"""


def test_cli_suggest_json_against_local_duckdb_matches_golden(
    consumer_duckdb: Path,
    capsys,
) -> None:
    assert main(
        [
            "suggest",
            "reproductores",
            "--format",
            "json",
            "--dataset",
            str(consumer_duckdb),
        ]
    ) == 0
    captured = capsys.readouterr()
    assert captured.err == ""
    assert captured.out == SUGGEST_REPRODUCTORES_JSON
    hit = json.loads(captured.out)[0]
    assert "not a classification" in hit["disclaimer"]
    assert hit["search"]["record"]["code"] == "01012101"
    assert hit["ficha"]["formatted_code"] == "0101.21.01"
    assert hit["national_notes"] == []
    assert hit["search"]["scorer_version"] == "1"


def test_subprocess_cli_suggest_json_uses_this_checkout_src(
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
    assert completed.stdout == SUGGEST_REPRODUCTORES_JSON
