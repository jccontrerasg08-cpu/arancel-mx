from __future__ import annotations

import json
from pathlib import Path

import pytest

from arancel_mx.cli import main
from arancel_mx.consumer.config import ConsumerConfig
from arancel_mx.consumer.doctor import DiagnosticCheck, DoctorResult
import arancel_mx.consumer.cli as consumer_cli


RESULTS = {
    "HEALTHY": DoctorResult(
        "HEALTHY",
        (
            DiagnosticCheck("package_version", "pass", "arancel-mx 0.2.0", (("version", "0.2.0"),)),
            DiagnosticCheck("network_release", "pass", "public release metadata is reachable", (("latest", "data-2026.08.11"),)),
        ),
    ),
    "DEGRADED": DoctorResult(
        "DEGRADED",
        (
            DiagnosticCheck("verified_dataset", "pass", "verified local dataset is usable"),
            DiagnosticCheck("network_release", "warn", "public release metadata is currently unreachable"),
        ),
    ),
    "UNHEALTHY": DoctorResult(
        "UNHEALTHY",
        (
            DiagnosticCheck("verified_dataset", "fail", "no usable verified local dataset is available"),
        ),
    ),
}


@pytest.fixture
def doctor_harness(tmp_path: Path, monkeypatch: pytest.MonkeyPatch):
    state: dict[str, object] = {"status": "HEALTHY", "config_kwargs": None, "doctor_config": None}

    def fake_resolve_config(**kwargs: object) -> ConsumerConfig:
        state["config_kwargs"] = dict(kwargs)
        return ConsumerConfig(
            cache_dir=tmp_path / "cache ñ",
            dataset=kwargs.get("dataset"),
            offline=bool(kwargs.get("offline", False)),
            timeout=30.0,
        )

    def fake_run_doctor(config: ConsumerConfig) -> DoctorResult:
        state["doctor_config"] = config
        return RESULTS[str(state["status"])]

    monkeypatch.setattr(consumer_cli, "resolve_config", fake_resolve_config)
    monkeypatch.setattr(consumer_cli, "run_doctor", fake_run_doctor, raising=False)
    return state


def test_doctor_human_healthy_exit_zero(doctor_harness, capsys) -> None:
    assert main(["doctor"]) == 0
    captured = capsys.readouterr()
    assert "arancel-mx doctor" in captured.out
    assert "[OK] package_version" in captured.out
    assert "Status: HEALTHY" in captured.out
    assert captured.err == ""


def test_doctor_human_degraded_exit_one(doctor_harness, capsys) -> None:
    doctor_harness["status"] = "DEGRADED"
    assert main(["doctor"]) == 1
    captured = capsys.readouterr()
    assert "[WARN] network_release" in captured.out
    assert "Status: DEGRADED" in captured.out
    assert captured.err == ""


def test_doctor_human_unhealthy_exit_two(doctor_harness, capsys) -> None:
    doctor_harness["status"] = "UNHEALTHY"
    assert main(["doctor"]) == 2
    captured = capsys.readouterr()
    assert "[FAIL] verified_dataset" in captured.out
    assert "Status: UNHEALTHY" in captured.out
    assert captured.err == ""


def test_doctor_json_schema_is_stable(doctor_harness, capsys) -> None:
    assert main(["doctor", "--json"]) == 0
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    assert payload == {
        "checks": [
            {
                "detail": "arancel-mx 0.2.0",
                "metadata": {"version": "0.2.0"},
                "name": "package_version",
                "status": "pass",
            },
            {
                "detail": "public release metadata is reachable",
                "metadata": {"latest": "data-2026.08.11"},
                "name": "network_release",
                "status": "pass",
            },
        ],
        "exit_code": 0,
        "status": "HEALTHY",
    }
    assert "\u001b" not in captured.out
    assert captured.err == ""


def test_doctor_json_degraded_preserves_exit_one(doctor_harness, capsys) -> None:
    doctor_harness["status"] = "DEGRADED"
    assert main(["doctor", "--json"]) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["status"] == "DEGRADED"
    assert payload["exit_code"] == 1


def test_doctor_dataset_and_offline_options_reach_config(doctor_harness, capsys) -> None:
    assert main([
        "doctor",
        "--dataset",
        "data-2026.08.11",
        "--offline",
        "--json",
    ]) == 0
    capsys.readouterr()
    assert doctor_harness["config_kwargs"] == {
        "dataset": "data-2026.08.11",
        "offline": True,
    }
    config = doctor_harness["doctor_config"]
    assert isinstance(config, ConsumerConfig)
    assert config.dataset == "data-2026.08.11"
    assert config.offline is True
