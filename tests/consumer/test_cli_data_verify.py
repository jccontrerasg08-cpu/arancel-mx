from __future__ import annotations

import json
from pathlib import Path

import pytest

from arancel_mx.cli import main
from arancel_mx.consumer.config import ConsumerConfig
from arancel_mx.consumer.errors import DatasetIntegrityError
from arancel_mx.consumer.models import DatasetInfo
import arancel_mx.consumer.cli as consumer_cli


class FakeManager:
    instances: list["FakeManager"] = []
    fail = False

    def __init__(self, config) -> None:
        self.config = config
        self.verify_calls: list[tuple[str | None, bool, bool]] = []
        self.__class__.instances.append(self)

    @classmethod
    def reset(cls) -> None:
        cls.instances.clear()
        cls.fail = False

    def verify(self, tag=None, *, online=False, bundle=False):
        self.verify_calls.append((tag, online, bundle))
        if self.fail:
            raise DatasetIntegrityError("SHA256SUMS checksum mismatch for arancel_mx.duckdb")
        return DatasetInfo(
            dataset_version="2026.08.11",
            schema_version="2",
            path="/tmp/cache/data-2026.08.11/arancel_mx.duckdb",
            source="managed-cache",
            structural_valid=True,
            release_verified=True,
            github_digest_state="verified",
        )


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


def test_data_verify_defaults_to_local_only(capsys) -> None:
    assert main(["data", "verify", "--format", "json"]) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["release_verified"] is True
    assert payload["github_digest_state"] == "verified"
    assert FakeManager.instances[-1].verify_calls == [(None, False, False)]


def test_data_verify_dataset_pin_is_preserved(capsys) -> None:
    assert main([
        "data",
        "verify",
        "--dataset",
        "data-2026.08.11",
        "--format",
        "json",
    ]) == 0
    capsys.readouterr()
    assert FakeManager.instances[-1].verify_calls == [
        ("data-2026.08.11", False, False)
    ]


def test_data_verify_online_compares_remote_identity(capsys) -> None:
    assert main(["data", "verify", "--online", "--format", "json"]) == 0
    capsys.readouterr()
    assert FakeManager.instances[-1].verify_calls == [(None, True, False)]


def test_data_verify_bundle_implies_online_certification(capsys) -> None:
    assert main(["data", "verify", "--bundle", "--format", "json"]) == 0
    capsys.readouterr()
    assert FakeManager.instances[-1].verify_calls == [(None, True, True)]


def test_data_verify_integrity_failure_is_exit_2_without_stdout(capsys) -> None:
    FakeManager.fail = True
    assert main(["data", "verify", "--format", "json"]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "SHA256SUMS checksum mismatch" in captured.err
    assert "Traceback" not in captured.err


def test_data_verify_online_is_rejected_in_offline_mode_before_verify(capsys) -> None:
    assert main([
        "data",
        "verify",
        "--offline",
        "--online",
        "--format",
        "json",
    ]) == 2
    captured = capsys.readouterr()
    assert captured.out == ""
    assert "offline" in captured.err.lower()
    assert FakeManager.instances[-1].verify_calls == []
