from __future__ import annotations

import json
from pathlib import Path

import pytest

from arancel_mx.cli import main
from arancel_mx.consumer.config import ConsumerConfig
from arancel_mx.consumer.errors import DatasetUnavailableError
import arancel_mx.consumer.cli as consumer_cli


class FakeManager:
    instances: list["FakeManager"] = []
    existing = False
    missing_path = False

    def __init__(self, config) -> None:
        self.config = config
        self.ensure_calls: list[str | None] = []
        self.selected_path_calls: list[str | None] = []
        self.path = Path(config.cache_dir) / "data-2026.08.11" / "arancel_mx.duckdb"
        self.__class__.instances.append(self)

    @classmethod
    def reset(cls) -> None:
        cls.instances.clear()
        cls.existing = False
        cls.missing_path = False

    def ensure(self, tag: str | None = None) -> Path:
        self.ensure_calls.append(tag)
        return self.path

    def selected_path(self, tag: str | None = None) -> Path:
        self.selected_path_calls.append(tag)
        if self.missing_path:
            raise DatasetUnavailableError("dataset is not verified in local cache")
        return self.path


@pytest.fixture(autouse=True)
def fake_manager(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    FakeManager.reset()
    monkeypatch.setattr(consumer_cli, "DatasetManager", FakeManager, raising=False)
    monkeypatch.setattr(
        consumer_cli,
        "resolve_config",
        lambda **kwargs: ConsumerConfig(
            cache_dir=tmp_path / "cache ñ",
            dataset=kwargs.get("dataset"),
            offline=bool(kwargs.get("offline", False)),
            timeout=30.0,
        ),
        raising=False,
    )


def test_data_download_returns_verified_path(capsys) -> None:
    assert main(["data", "download", "--format", "json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "verified"
    assert payload["path"].endswith("arancel_mx.duckdb")
    assert FakeManager.instances[-1].ensure_calls == [None]


def test_data_download_existing_verified_cache_is_idempotent(capsys) -> None:
    FakeManager.existing = True
    assert main(["data", "download", "--format", "json"]) == 0
    first = json.loads(capsys.readouterr().out)
    assert main(["data", "download", "--format", "json"]) == 0
    second = json.loads(capsys.readouterr().out)
    assert first["path"] == second["path"]
    assert first["status"] == second["status"] == "verified"


def test_data_download_dataset_option_pins_version(capsys) -> None:
    assert main([
        "data",
        "download",
        "--dataset",
        "data-2026.08.10",
        "--format",
        "json",
    ]) == 0
    capsys.readouterr()
    manager = FakeManager.instances[-1]
    assert manager.config.dataset == "data-2026.08.10"
    assert manager.ensure_calls == ["data-2026.08.10"]


def test_data_path_stdout_contains_only_path(capsys) -> None:
    assert main(["data", "path"]) == 0
    captured = capsys.readouterr()
    manager = FakeManager.instances[-1]
    assert captured.out == f"{manager.path}\n"
    assert captured.err == ""
    assert manager.selected_path_calls == [None]


def test_data_path_missing_cache_fails_without_noise_on_stdout(capsys) -> None:
    FakeManager.missing_path = True
    assert main(["data", "path"]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "not verified" in captured.err
    assert "Traceback" not in captured.err
