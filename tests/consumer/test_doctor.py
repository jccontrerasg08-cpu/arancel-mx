from __future__ import annotations

from pathlib import Path

import pytest

from arancel_mx.consumer.config import ConsumerConfig
from arancel_mx.consumer.doctor import DiagnosticCheck, DoctorResult, run_doctor
from arancel_mx.consumer.errors import DatasetDownloadError, DatasetUnavailableError
from arancel_mx.consumer.models import DatasetInfo


class FakeManager:
    def __init__(self, path: Path, *, network_fails: bool = False, no_dataset: bool = False) -> None:
        self.path = path
        self.network_fails = network_fails
        self.no_dataset = no_dataset
        self.remote_calls = 0
        self.verify_calls: list[str | None] = []

    def list_local(self) -> tuple[str, ...]:
        return () if self.no_dataset else ("data-2026.08.11",)

    def list_remote(self) -> tuple[str, ...]:
        self.remote_calls += 1
        if self.network_fails:
            raise DatasetDownloadError("GitHub releases unavailable")
        return ("data-2026.08.11",)

    def verify(self, tag=None, *, online=False, bundle=False) -> DatasetInfo:
        self.verify_calls.append(tag)
        if self.no_dataset:
            raise DatasetUnavailableError("No verified local dataset is available")
        return DatasetInfo(
            dataset_version="2026.08.11",
            schema_version="2",
            path=str(self.path),
            source="managed-cache",
            structural_valid=True,
            release_verified=True,
            github_digest_state="verified",
        )

    def selected_path(self, tag=None) -> Path:
        if self.no_dataset:
            raise DatasetUnavailableError("No verified local dataset is available")
        return self.path


def _config(tmp_path: Path, *, offline: bool = False) -> ConsumerConfig:
    return ConsumerConfig(
        cache_dir=tmp_path / "cache ñ",
        dataset=None,
        offline=offline,
        timeout=2.0,
    )


def _by_name(result: DoctorResult) -> dict[str, DiagnosticCheck]:
    return {check.name: check for check in result.checks}


def test_doctor_result_models_are_immutable() -> None:
    check = DiagnosticCheck("example", "pass", "ok", ())
    result = DoctorResult("HEALTHY", (check,))
    with pytest.raises(Exception):
        check.name = "mutated"  # type: ignore[misc]
    with pytest.raises(Exception):
        result.status = "UNHEALTHY"  # type: ignore[misc]


def test_doctor_healthy_when_all_core_checks_pass(
    tmp_path: Path,
    consumer_duckdb: Path,
) -> None:
    result = run_doctor(
        _config(tmp_path),
        manager=FakeManager(consumer_duckdb),
    )

    assert result.status == "HEALTHY"
    assert result.exit_code == 0
    checks = _by_name(result)
    for name in (
        "package_version",
        "python_version",
        "platform",
        "distribution_metadata",
        "console_entrypoint",
        "source_registry",
        "cache_writable",
        "verified_dataset",
        "duckdb_query",
        "network_release",
        "offline_readiness",
    ):
        assert checks[name].status == "pass"


def test_doctor_degraded_when_network_fails_but_verified_cache_is_usable(
    tmp_path: Path,
    consumer_duckdb: Path,
) -> None:
    result = run_doctor(
        _config(tmp_path),
        manager=FakeManager(consumer_duckdb, network_fails=True),
    )

    assert result.status == "DEGRADED"
    assert result.exit_code == 1
    checks = _by_name(result)
    assert checks["network_release"].status == "warn"
    assert checks["verified_dataset"].status == "pass"
    assert checks["duckdb_query"].status == "pass"
    assert checks["offline_readiness"].status == "pass"


def test_doctor_unhealthy_when_no_usable_dataset_exists(
    tmp_path: Path,
    consumer_duckdb: Path,
) -> None:
    result = run_doctor(
        _config(tmp_path),
        manager=FakeManager(consumer_duckdb, no_dataset=True),
    )

    assert result.status == "UNHEALTHY"
    assert result.exit_code == 2
    checks = _by_name(result)
    assert checks["verified_dataset"].status == "fail"
    assert checks["duckdb_query"].status == "fail"
    assert checks["offline_readiness"].status == "fail"


def test_doctor_does_not_expose_sensitive_environment_values(
    tmp_path: Path,
    consumer_duckdb: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    secret = "SUPER-SECRET-TOKEN-DO-NOT-PRINT"
    monkeypatch.setenv("GITHUB_TOKEN", secret)
    monkeypatch.setenv("PYPI_API_TOKEN", secret)
    monkeypatch.setenv("SOME_PASSWORD", secret)

    result = run_doctor(
        _config(tmp_path),
        manager=FakeManager(consumer_duckdb),
    )

    assert secret not in repr(result)
    assert secret not in "\n".join(check.detail for check in result.checks)
    assert all(secret not in repr(check.metadata) for check in result.checks)


def test_doctor_checks_read_only_duckdb_query(
    tmp_path: Path,
    consumer_duckdb: Path,
) -> None:
    result = run_doctor(
        _config(tmp_path),
        manager=FakeManager(consumer_duckdb),
    )
    check = _by_name(result)["duckdb_query"]
    assert check.status == "pass"
    metadata = dict(check.metadata)
    assert metadata["sample_code"] == "01"
    assert metadata["read_only"] == "true"


def test_doctor_offline_skips_network_check(
    tmp_path: Path,
    consumer_duckdb: Path,
) -> None:
    manager = FakeManager(consumer_duckdb, network_fails=True)
    result = run_doctor(
        _config(tmp_path, offline=True),
        manager=manager,
    )

    assert result.status == "HEALTHY"
    assert result.exit_code == 0
    assert manager.remote_calls == 0
    assert _by_name(result)["network_release"].status == "skip"
