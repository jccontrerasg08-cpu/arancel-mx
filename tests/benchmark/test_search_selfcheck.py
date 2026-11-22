from __future__ import annotations

import json
from collections import Counter
from datetime import date
from itertools import count
from pathlib import Path

import pytest

from arancel_mx.benchmark.search_selfcheck import SelfcheckRecord, run_selfcheck, sample_records
from arancel_mx.cli import build_parser, main
from arancel_mx.consumer.models import SearchResult, TariffRecord
from tests.consumer.conftest import create_consumer_duckdb


def _record(code: str, description: str) -> SelfcheckRecord:
    return SelfcheckRecord(code=code, formatted_code=f"{code[:4]}.{code[4:6]}.{code[6:]}", description=description)


def _result(code: str, description: str) -> SearchResult:
    record = TariffRecord(
        code=code, level="fraccion8" if len(code) == 8 else "nico10", description=description, unit_name=None,
        igi_text=None, igi_kind=None, igi_value=None, ige_text=None, ige_kind=None, ige_value=None,
        parent_code=None, dataset_version="x", schema_version="2", effective_from=date(2022, 12, 12),
        effective_to=None, is_current=True,
    )
    return SearchResult(record=record, score=1, match_kind="description")


RECORDS = [
    _record("01012101", "Reproductores de raza pura."),
    _record("01012999", "Los demás."),
    _record("01013099", "Los demás."),
    _record("85171301", "Teléfonos inteligentes."),
]


def _search_from(table: dict[str, list[SearchResult]]):
    def search(text: str, limit: int) -> list[SearchResult]:
        return table.get(text, [])[:limit]

    return search


def _perfect():
    table: dict[str, list[SearchResult]] = {}
    for record in RECORDS:
        table[record.code] = [_result(record.code, record.description)]
        table[record.formatted_code] = [_result(record.code, record.description)]
        table.setdefault(record.description, []).append(_result(record.code, record.description))
    return _search_from(table)


def test_sample_is_deterministic_evenly_spaced_and_ordered() -> None:
    records = [_record(f"{index:08d}", "x") for index in range(10, 0, -1)]
    assert [r.code for r in sample_records(records, 3)] == ["00000001", "00000004", "00000007"]
    assert sample_records(records, 3) == sample_records(list(reversed(records)), 3)
    assert len(sample_records(records, 50)) == 10
    with pytest.raises(ValueError):
        sample_records(records, 0)


def test_perfect_search_scores_every_distinctive_probe_and_skips_shared_descriptions() -> None:
    report = run_selfcheck(RECORDS, _perfect(), sample=4)
    assert report["exact_code"] == {"top1": 4, "rate": 1.0}
    assert report["dotted_code"] == {"top1": 4, "rate": 1.0}
    own = report["own_description"]
    assert own["evaluated"] == 2  # the two «Los demás.» fractions cannot be told apart by description
    assert own["non_distinctive_skipped"] == 2
    assert own["top1_rate"] == 1.0
    assert report["failures"] == []
    assert "not a classification benchmark" in str(report["scope"])


def test_misses_are_reported_with_their_rank_instead_of_hidden() -> None:
    table = {
        "01012101": [_result("01012999", "Los demás."), _result("01012101", "Reproductores de raza pura.")],
        "0101.21.01": [],
        "Reproductores de raza pura.": [_result("01012999", "otro")] * 3 + [_result("01012101", "Reproductores de raza pura.")],
    }
    report = run_selfcheck(RECORDS[:1], _search_from(table), sample=1, depth=10)
    assert report["exact_code"]["top1"] == 0
    assert report["own_description"]["top1"] == 0
    assert report["own_description"]["top5"] == 1
    assert [(f["probe"], f["rank"]) for f in report["failures"]] == [("exact_code", None), ("dotted_code", None), ("own_description", 4)]


def test_the_same_item_at_another_level_of_its_line_counts_as_found() -> None:
    table = {"Teléfonos inteligentes.": [_result("8517130100", "Teléfonos inteligentes.")]}
    report = run_selfcheck(RECORDS[3:], _search_from(table), sample=1)
    assert report["own_description"]["top1"] == 1
    unrelated = {"Teléfonos inteligentes.": [_result("8517139900", "Teléfonos inteligentes.")]}
    assert run_selfcheck(RECORDS[3:], _search_from(unrelated), sample=1)["own_description"]["not_found"] == 1


def test_latency_is_measured_with_the_given_clock() -> None:
    ticks = count(step=0.002)
    report = run_selfcheck(RECORDS, _perfect(), sample=4, clock=lambda: next(ticks))
    latency = report["latency_ms"]
    assert latency["searches"] == 10
    assert latency["p50"] == 2.0
    assert latency["max"] == 2.0


def test_description_counts_can_come_from_a_wider_population() -> None:
    counts = Counter({"Reproductores de raza pura.": 2})
    report = run_selfcheck(RECORDS[:1], _perfect(), sample=1, description_counts=counts)
    assert report["own_description"]["non_distinctive_skipped"] == 1


def test_cli_runs_against_a_local_dataset(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    namespace = build_parser().parse_args(["data", "search-selfcheck", "--sample", "5", "--depth", "3"])
    assert (namespace.consumer_action, namespace.sample, namespace.depth) == ("data_search_selfcheck", 5, 3)
    path = create_consumer_duckdb(tmp_path / "fixture.duckdb")
    assert main(["data", "search-selfcheck", "--dataset", str(path), "--sample", "5"]) == 0
    report = json.loads(capsys.readouterr().out)
    assert report["sample"]["records"] == 1
    assert report["exact_code"]["rate"] == 1.0
    assert report["dataset_version"] == "2026.08.11"
