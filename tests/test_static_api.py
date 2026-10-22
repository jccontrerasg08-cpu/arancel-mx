from __future__ import annotations

from datetime import datetime, timezone
import json
from pathlib import Path
import shutil
import subprocess
from urllib.parse import quote

import pytest

from arancel_mx.api.models import (
    FichaResponse,
    NationalNoteResponse,
    ProvenanceResponse,
    SearchResponse,
    SuggestResponse,
    TariffResponse,
)
from arancel_mx.consumer.dataset import Dataset
from arancel_mx.consumer.errors import RecordNotFoundError
from arancel_mx.static_api import StaticApi, build_static_api, verify_static_api
from tests.consumer.conftest import create_consumer_duckdb

CODES = ("01", "0101", "010121", "01012101", "0101210100")
QUERIES = (
    "caballos",
    "raza pura",
    "0101",
    "01012101",
    "animales vivos",
    "pura reproductores",
)


@pytest.fixture
def exported(tmp_path: Path) -> tuple[Dataset, StaticApi, dict]:
    duckdb_path = create_consumer_duckdb(tmp_path / "fixture.duckdb")
    manifest = build_static_api(
        duckdb_path,
        tmp_path / "static",
        dataset_tag="data-2026.08.11",
        release_verified=True,
        generated_at=datetime(2026, 8, 11, tzinfo=timezone.utc),
    )
    return Dataset.open(duckdb_path), StaticApi(tmp_path / "static"), manifest


def test_manifest_lists_every_file_with_matching_hashes(
    exported, tmp_path: Path
) -> None:
    _, _, manifest = exported
    root = tmp_path / "static"
    assert manifest["record_count"] == len(CODES)
    assert set(manifest["files"]) == {
        "chapters.json",
        "meta.json",
        "national-notes/01.json",
        "provenance/01.json",
        "records/01.json",
        "search-index.json",
        "sections.json",
    }
    assert verify_static_api(root) == []

    (root / "records/01.json").write_text("[]\n", encoding="utf-8")
    assert verify_static_api(root) == ["sha256 mismatch: records/01.json"]


def test_meta_identifies_the_release(exported, tmp_path: Path) -> None:
    meta = json.loads((tmp_path / "static" / "meta.json").read_text(encoding="utf-8"))
    assert meta["dataset_tag"] == "data-2026.08.11"
    assert meta["dataset_version"] == "2026.08.11"
    assert meta["read_only"] is True
    assert meta["static_format"] == "1"


@pytest.mark.parametrize("code", CODES)
def test_code_routes_match_the_dataset(exported, code: str) -> None:
    dataset, static, _ = exported
    assert static.lookup(code) == TariffResponse.from_record(dataset.lookup(code))
    assert static.ficha(code) == FichaResponse.from_ficha(dataset.ficha(code))
    assert static.children(code) == [
        TariffResponse.from_record(item) for item in dataset.children(code)
    ]
    expected_parent = dataset.parent(code)
    assert static.parent(code) == (
        None if expected_parent is None else TariffResponse.from_record(expected_parent)
    )
    assert static.provenance(code) == [
        ProvenanceResponse.from_record(item) for item in dataset.provenance(code)
    ]


@pytest.mark.parametrize("query", QUERIES)
def test_search_and_suggest_match_the_dataset(exported, query: str) -> None:
    dataset, static, _ = exported
    assert static.search(query, limit=20) == [
        SearchResponse.from_result(item) for item in dataset.search(query, limit=20)
    ]
    assert static.suggest(query, limit=5) == [
        SuggestResponse.from_hit(item) for item in dataset.suggest(query, limit=5)
    ]


def test_national_notes_and_chapters_match_the_dataset(exported) -> None:
    dataset, static, _ = exported
    assert static.national_notes("01") == [
        NationalNoteResponse.from_note(note) for note in dataset.national_notes("01")
    ]
    chapters = json.loads((static.root / "chapters.json").read_text(encoding="utf-8"))
    assert [TariffResponse.model_validate(item) for item in chapters] == [
        TariffResponse.from_record(item) for item in dataset.chapters()
    ]


def test_unknown_code_raises_like_the_dataset(exported) -> None:
    _, static, _ = exported
    with pytest.raises(RecordNotFoundError):
        static.lookup("9999")


def test_cli_builds_and_verifies(tmp_path: Path, capsys) -> None:
    from arancel_mx.cli import main

    duckdb_path = create_consumer_duckdb(tmp_path / "fixture.duckdb")
    out = tmp_path / "static"
    assert (
        main(
            [
                "static-api",
                "build",
                "--dataset",
                str(duckdb_path),
                "--out",
                str(out),
                "--tag",
                "data-2026.08.11",
            ]
        )
        == 0
    )
    assert json.loads(capsys.readouterr().out) == {
        "dataset_tag": "data-2026.08.11",
        "files": 7,
        "record_count": 5,
    }
    assert main(["static-api", "verify", "--root", str(out)]) == 0
    (out / "meta.json").write_text("{}\n", encoding="utf-8")
    assert main(["static-api", "verify", "--root", str(out)]) == 2
    assert "sha256 mismatch: meta.json" in capsys.readouterr().err


def _dump_case(value) -> object:
    if value is None:
        return None
    if isinstance(value, list):
        return [item.model_dump(mode="json") for item in value]
    return value.model_dump(mode="json")


@pytest.mark.skipif(shutil.which("node") is None, reason="node is not installed")
def test_browser_client_matches_python_reference(exported, tmp_path: Path) -> None:
    _, static, _ = exported
    cases: dict[str, object] = {
        "/v1/lookup/9999": {"error": 404},
        "/v1/lookup/12a": {"error": 422},
    }
    for code in CODES:
        cases[f"/v1/lookup/{code}"] = _dump_case(static.lookup(code))
        cases[f"/v1/ficha/{code}"] = _dump_case(static.ficha(code))
        cases[f"/v1/codes/{code}/parent"] = _dump_case(static.parent(code))
        cases[f"/v1/codes/{code}/children"] = _dump_case(static.children(code))
        cases[f"/v1/codes/{code}/provenance"] = _dump_case(static.provenance(code))
    for query in QUERIES:
        cases[f"/v1/search?q={quote(query)}&limit=20"] = _dump_case(
            static.search(query)
        )
        cases[f"/v1/suggest?q={quote(query)}&limit=5"] = _dump_case(
            static.suggest(query)
        )
    cases["/v1/chapters/01/national-notes"] = _dump_case(static.national_notes("01"))
    for name in ("meta", "sections", "chapters"):
        cases[f"/v1/{name}"] = json.loads(
            (static.root / f"{name}.json").read_text(encoding="utf-8")
        )
    cases_path = tmp_path / "cases.json"
    cases_path.write_text(json.dumps(cases, ensure_ascii=False), encoding="utf-8")

    result = subprocess.run(
        [
            "node",
            str(Path(__file__).parent / "frontend" / "static_api_parity.mjs"),
            str(static.root),
            str(cases_path),
        ],
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
