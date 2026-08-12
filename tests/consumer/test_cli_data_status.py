from __future__ import annotations

import json
from pathlib import Path

import pytest

from arancel_mx.cli import main
from arancel_mx.consumer.config import ConsumerConfig
import arancel_mx.consumer.cli as consumer_cli


class FakeManager:
    instances: list["FakeManager"] = []
    local = ("data-2026.08.10", "data-2026.08.11")
    remote = ("data-2026.08.12", "data-2026.08.11", "data-2026.08.10")
    fail_if_remote_called = False

    def __init__(self, config) -> None:
        self.config = config
        self.local_calls = 0
        self.remote_calls = 0
        self.__class__.instances.append(self)

    @classmethod
    def reset(cls) -> None:
        cls.instances.clear()
        cls.local = ("data-2026.08.10", "data-2026.08.11")
        cls.remote = ("data-2026.08.12", "data-2026.08.11", "data-2026.08.10")
        cls.fail_if_remote_called = False

    def list_local(self) -> tuple[str, ...]:
        self.local_calls += 1
        return self.local

    def list_remote(self) -> tuple[str, ...]:
        self.remote_calls += 1
        if self.fail_if_remote_called:
            raise AssertionError("remote listing called in offline mode")
        return self.remote


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


def test_data_status_reports_local_remote_and_update_available(capsys) -> None:
    assert main(["data", "status", "--format", "json"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload == {
        "local_latest": "data-2026.08.11",
        "local_versions": ["data-2026.08.10", "data-2026.08.11"],
        "offline": False,
        "remote_latest": "data-2026.08.12",
        "selected": "data-2026.08.11",
        "update_available": True,
    }
    manager = FakeManager.instances[-1]
    assert manager.local_calls == 1
    assert manager.remote_calls == 1


def test_data_status_explicit_dataset_is_selected(capsys) -> None:
    assert main([
        "data",
        "status",
        "--dataset",
        "data-2026.08.10",
        "--format",
        "json",
    ]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["selected"] == "data-2026.08.10"
    assert payload["local_latest"] == "data-2026.08.11"


def test_data_status_offline_never_lists_remote(capsys) -> None:
    FakeManager.fail_if_remote_called = True
    assert main(["data", "status", "--offline", "--format", "json"]) == 0
    payload = json.loads(capsys.readouterr().out)

    assert payload["offline"] is True
    assert payload["remote_latest"] is None
    assert payload["update_available"] is False
    assert FakeManager.instances[-1].remote_calls == 0


def test_data_status_without_local_cache_is_explicit(capsys) -> None:
    FakeManager.local = ()
    assert main(["data", "status", "--format", "json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["local_latest"] is None
    assert payload["selected"] is None
    assert payload["remote_latest"] == "data-2026.08.12"
    assert payload["update_available"] is True


def test_data_list_local_is_deterministic(capsys) -> None:
    assert main(["data", "list", "--format", "json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload == [
        {"dataset": "data-2026.08.10", "scope": "local"},
        {"dataset": "data-2026.08.11", "scope": "local"},
    ]
    assert FakeManager.instances[-1].remote_calls == 0


def test_data_list_remote_uses_valid_remote_release_listing(capsys) -> None:
    assert main(["data", "list", "--remote", "--format", "json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload == [
        {"dataset": "data-2026.08.12", "scope": "remote"},
        {"dataset": "data-2026.08.11", "scope": "remote"},
        {"dataset": "data-2026.08.10", "scope": "remote"},
    ]
    assert FakeManager.instances[-1].remote_calls == 1


def test_data_list_remote_offline_is_rejected_without_remote_call(capsys) -> None:
    FakeManager.fail_if_remote_called = True
    assert main(["data", "list", "--remote", "--offline", "--format", "json"]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "offline" in captured.err.lower()
    assert FakeManager.instances[-1].remote_calls == 0
