from __future__ import annotations

import json
from pathlib import Path

import pytest

from arancel_mx.cli import main
from arancel_mx.consumer.config import ConsumerConfig
import arancel_mx.consumer.cli as consumer_cli


class FakeManager:
    instances: list["FakeManager"] = []
    result = ("downloaded", Path("/tmp/cache/data-2026.08.12/arancel_mx.duckdb"))
    fail_if_update_called = False

    def __init__(self, config) -> None:
        self.config = config
        self.update_calls = 0
        self.__class__.instances.append(self)

    @classmethod
    def reset(cls) -> None:
        cls.instances.clear()
        cls.result = ("downloaded", Path("/tmp/cache/data-2026.08.12/arancel_mx.duckdb"))
        cls.fail_if_update_called = False

    def update(self):
        self.update_calls += 1
        if self.fail_if_update_called:
            raise AssertionError("update called while offline")
        return self.result


@pytest.fixture(autouse=True)
def fake_manager(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    FakeManager.reset()
    monkeypatch.setattr(consumer_cli, "DatasetManager", FakeManager)
    monkeypatch.setattr(
        consumer_cli,
        "resolve_config",
        lambda **kwargs: ConsumerConfig(
            cache_dir=tmp_path / "cache",
            dataset=kwargs.get("dataset"),
            offline=bool(kwargs.get("offline", False)),
            timeout=30.0,
        ),
    )


def test_data_update_reports_downloaded_release(capsys) -> None:
    assert main(["data", "update", "--format", "json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "downloaded"
    assert payload["path"].endswith("arancel_mx.duckdb")
    assert FakeManager.instances[-1].update_calls == 1


def test_data_update_no_change_is_idempotent(capsys) -> None:
    FakeManager.result = (
        "no_change",
        Path("/tmp/cache/data-2026.08.11/arancel_mx.duckdb"),
    )
    assert main(["data", "update", "--format", "json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload == {
        "path": "/tmp/cache/data-2026.08.11/arancel_mx.duckdb",
        "status": "no_change",
    }


def test_data_update_rejects_dataset_pin(capsys) -> None:
    assert main([
        "data",
        "update",
        "--dataset",
        "data-2026.08.11",
        "--format",
        "json",
    ]) == 2
    captured = capsys.readouterr()
    assert "unrecognized arguments" in captured.err
    assert "--dataset" in captured.err
    assert FakeManager.instances == []


def test_data_update_offline_is_rejected_before_manager_update(capsys) -> None:
    FakeManager.fail_if_update_called = True
    assert main(["data", "update", "--offline", "--format", "json"]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "offline" in captured.err.lower()
    assert FakeManager.instances[-1].update_calls == 0
