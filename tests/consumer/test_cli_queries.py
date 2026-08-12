from __future__ import annotations

import json
from pathlib import Path

import pytest

from arancel_mx.cli import main
from arancel_mx.consumer.errors import InvalidCodeError
from arancel_mx.consumer.models import Ficha, HsSection, ProvenanceRecord, SearchResult, TariffRecord
import arancel_mx.consumer.cli as consumer_cli


def _record(code: str = "01012101", level: str = "fraccion8") -> TariffRecord:
    parent = {"hs2": None, "hs4": "01", "hs6": "0101", "fraccion8": "010121", "nico10": "01012101"}[level]
    return TariffRecord(
        code=code,
        level=level,
        description="Reproductores de raza pura",
        unit_name="Cbza" if level in {"fraccion8", "nico10"} else None,
        igi_text="10" if level in {"fraccion8", "nico10"} else None,
        igi_kind="ad_valorem" if level in {"fraccion8", "nico10"} else None,
        igi_value=10.0 if level in {"fraccion8", "nico10"} else None,
        ige_text="Ex." if level in {"fraccion8", "nico10"} else None,
        ige_kind="exento" if level in {"fraccion8", "nico10"} else None,
        ige_value=0.0 if level in {"fraccion8", "nico10"} else None,
        parent_code=parent,
        dataset_version="2026.08.11",
        schema_version="2",
        effective_from=None,
        effective_to=None,
        is_current=True,
    )


class FakeDataset:
    latest_calls: list[dict[str, object]] = []
    version_calls: list[tuple[str, dict[str, object]]] = []

    @classmethod
    def reset(cls) -> None:
        cls.latest_calls.clear()
        cls.version_calls.clear()

    @classmethod
    def latest(cls, **kwargs: object) -> "FakeDataset":
        cls.latest_calls.append(kwargs)
        return cls()

    @classmethod
    def version(cls, tag: str, **kwargs: object) -> "FakeDataset":
        cls.version_calls.append((tag, kwargs))
        return cls()

    def lookup(self, code: str) -> TariffRecord:
        if code == "bad":
            raise InvalidCodeError("invalid tariff code: 'bad'")
        return _record()

    def search(self, text: str, *, limit: int = 20) -> tuple[SearchResult, ...]:
        return (SearchResult(_record(), 355, "description"),)[:limit]

    def parent(self, code: str) -> TariffRecord | None:
        return _record("010121", "hs6")

    def children(self, code: str) -> tuple[TariffRecord, ...]:
        return (_record("01012101", "fraccion8"), _record("01012102", "fraccion8"))

    def provenance(self, code: str) -> tuple[ProvenanceRecord, ...]:
        return (
            ProvenanceRecord(
                source_document_id="source-1",
                role="base",
                is_primary=True,
                authority="SNICE",
                publication_venue="SNICE",
                title="LIGIE fixture",
                source_url="https://example.invalid/source",
                sha256="a" * 64,
                published_at=None,
                effective_from=None,
                effective_to=None,
            ),
        )

    def ficha(self, code: str) -> Ficha:
        record = _record()
        return Ficha(
            record=record,
            formatted_code="0101.21.01",
            section=HsSection("I", "Animales vivos y productos del reino animal", "01", "05"),
            hierarchy=(_record("01", "hs2"), record),
            children=(_record("0101210100", "nico10"),),
        )

    def chapters(self) -> tuple[TariffRecord, ...]:
        return (_record("01", "hs2"),)


@pytest.fixture(autouse=True)
def fake_dataset(monkeypatch: pytest.MonkeyPatch) -> None:
    FakeDataset.reset()
    monkeypatch.setattr(consumer_cli, "Dataset", FakeDataset)


def test_lookup_json_contract(capsys) -> None:
    assert main(["lookup", "01012101", "--format", "json"]) == 0
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert payload["code"] == "01012101"
    assert payload["level"] == "fraccion8"
    assert captured.err == ""


def test_lookup_invalid_code_returns_public_error(capsys) -> None:
    result = main(["lookup", "bad", "--format", "json"])
    captured = capsys.readouterr()
    assert result == 2
    assert captured.out == ""
    assert "invalid tariff code" in captured.err
    assert "Traceback" not in captured.err


def test_search_accepts_limit_and_format(capsys) -> None:
    assert main(["search", "raza pura", "--limit", "1", "--format", "json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert len(payload) == 1
    assert payload[0]["score"] == 355
    assert payload[0]["record"]["code"] == "01012101"


def test_parent_returns_one_record(capsys) -> None:
    assert main(["parent", "01012101", "--format", "json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["code"] == "010121"
    assert payload["level"] == "hs6"


def test_children_returns_deterministic_sequence(capsys) -> None:
    assert main(["children", "010121", "--format", "json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert [item["code"] for item in payload] == ["01012101", "01012102"]


def test_provenance_json_contract(capsys) -> None:
    assert main(["provenance", "01012101", "--format", "json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload[0]["source_document_id"] == "source-1"
    assert payload[0]["is_primary"] is True


def test_query_dataset_override_selects_requested_release(capsys) -> None:
    assert main([
        "lookup",
        "01012101",
        "--dataset",
        "data-2026.08.10",
        "--format",
        "json",
    ]) == 0
    capsys.readouterr()
    assert FakeDataset.latest_calls == []
    assert FakeDataset.version_calls == [("data-2026.08.10", {"offline": None})]


def test_query_offline_flag_never_calls_latest_without_offline(capsys) -> None:
    assert main(["lookup", "01012101", "--offline", "--format", "json"]) == 0
    capsys.readouterr()
    assert FakeDataset.latest_calls == [{"offline": True}]


def test_query_formats_csv_without_extra_blank_line(capsys) -> None:
    assert main(["lookup", "01012101", "--format", "csv"]) == 0
    output = capsys.readouterr().out
    assert output.startswith("code,level,description")
    assert not output.endswith("\n\n")


def test_empty_search_csv_keeps_search_schema(monkeypatch, capsys) -> None:
    monkeypatch.setattr(FakeDataset, "search", lambda self, text, limit=20: ())
    assert main(["search", "sin coincidencias", "--format", "csv"]) == 0
    output = capsys.readouterr().out
    assert output.startswith("score,match_kind,code,level,description")
    assert output.count("\n") == 1


def test_empty_children_csv_keeps_tariff_schema(monkeypatch, capsys) -> None:
    monkeypatch.setattr(FakeDataset, "children", lambda self, code: ())
    assert main(["children", "010121", "--format", "csv"]) == 0
    output = capsys.readouterr().out
    assert output.startswith("code,level,description")
    assert output.count("\n") == 1


def test_empty_provenance_csv_keeps_provenance_schema(monkeypatch, capsys) -> None:
    monkeypatch.setattr(FakeDataset, "provenance", lambda self, code: ())
    assert main(["provenance", "01012101", "--format", "csv"]) == 0
    output = capsys.readouterr().out
    assert output.startswith("source_document_id,role,is_primary,authority")
    assert output.count("\n") == 1


def test_ficha_json_contract(capsys) -> None:
    assert main(["ficha", "01012101", "--format", "json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["formatted_code"] == "0101.21.01"
    assert payload["record"]["code"] == "01012101"
    assert payload["section"]["roman"] == "I"
    assert payload["section"]["source"] == "hs_section_grouping"
    assert payload["hierarchy"][0]["code"] == "01"
    assert [child["code"] for child in payload["children"]] == ["0101210100"]


def test_ficha_table_uses_spanish_level_labels(capsys) -> None:
    assert main(["ficha", "01012101"]) == 0
    text = capsys.readouterr().out
    assert "Fracción" in text
    assert "NICO" in text
    assert "Hijos" in text
    assert "0101.21.01 00" in text
    assert "fraccion8" not in text
    assert "nico10" not in text


def test_chapters_json_contract(capsys) -> None:
    assert main(["chapters", "--format", "json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload[0]["code"] == "01"
    assert payload[0]["level"] == "hs2"


def test_empty_chapters_csv_keeps_tariff_schema(monkeypatch, capsys) -> None:
    monkeypatch.setattr(FakeDataset, "chapters", lambda self: ())
    assert main(["chapters", "--format", "csv"]) == 0
    output = capsys.readouterr().out
    assert output.startswith("code,level,description")
    assert output.count("\n") == 1
