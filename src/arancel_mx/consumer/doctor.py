"""Non-sensitive diagnostics for the installed consumer package and dataset cache."""

from __future__ import annotations

from dataclasses import dataclass
from importlib import metadata, resources
import json
from pathlib import Path
import platform
import sys
import tempfile
from typing import Literal

import duckdb

from arancel_mx.consumer.config import ConsumerConfig
from arancel_mx.consumer.errors import ArancelMXError
from arancel_mx.consumer.manager import DatasetManager
from arancel_mx.storage.duckdb import connect as duckdb_connect


CheckStatus = Literal["pass", "warn", "fail", "skip"]
DoctorStatus = Literal["HEALTHY", "DEGRADED", "UNHEALTHY"]
MetadataItems = tuple[tuple[str, str], ...]


@dataclass(frozen=True, slots=True)
class DiagnosticCheck:
    """One immutable, deliberately non-sensitive diagnostic result."""

    name: str
    status: CheckStatus
    detail: str
    metadata: MetadataItems = ()


@dataclass(frozen=True, slots=True)
class DoctorResult:
    """Aggregate doctor result with a stable process exit contract."""

    status: DoctorStatus
    checks: tuple[DiagnosticCheck, ...]

    @property
    def exit_code(self) -> int:
        return {"HEALTHY": 0, "DEGRADED": 1, "UNHEALTHY": 2}[self.status]


def _check(
    check_name: str,
    status: CheckStatus,
    detail: str,
    **safe_metadata: object,
) -> DiagnosticCheck:
    return DiagnosticCheck(
        name=check_name,
        status=status,
        detail=detail,
        metadata=tuple(
            sorted((str(key), str(value)) for key, value in safe_metadata.items())
        ),
    )


def _package_checks() -> list[DiagnosticCheck]:
    checks: list[DiagnosticCheck] = []
    try:
        distribution = metadata.distribution("arancel-mx")
        version = distribution.version
        checks.append(_check("package_version", "pass", f"arancel-mx {version}", version=version))
        checks.append(
            _check(
                "distribution_metadata",
                "pass",
                "installed distribution metadata is readable",
                name=distribution.metadata.get("Name", "arancel-mx"),
            )
        )
    except metadata.PackageNotFoundError:
        checks.extend(
            [
                _check("package_version", "fail", "arancel-mx distribution metadata is missing"),
                _check("distribution_metadata", "fail", "installed distribution metadata is unavailable"),
            ]
        )

    python_version = ".".join(map(str, sys.version_info[:3]))
    checks.append(
        _check(
            "python_version",
            "pass" if sys.version_info >= (3, 11) else "fail",
            f"Python {python_version}",
            version=python_version,
        )
    )
    checks.append(
        _check(
            "platform",
            "pass",
            f"{platform.system()} {platform.machine()}",
            system=platform.system(),
            machine=platform.machine(),
        )
    )

    try:
        console_scripts = metadata.entry_points(group="console_scripts")
        entrypoint = next((entry for entry in console_scripts if entry.name == "arancel-mx"), None)
        if entrypoint is None:
            checks.append(_check("console_entrypoint", "fail", "arancel-mx console entrypoint is missing"))
        else:
            checks.append(
                _check(
                    "console_entrypoint",
                    "pass",
                    "arancel-mx console entrypoint is installed",
                    target=entrypoint.value,
                )
            )
    except (TypeError, AttributeError):
        checks.append(_check("console_entrypoint", "fail", "console entrypoint metadata is unreadable"))

    try:
        registry = resources.files("arancel_mx.sources").joinpath("source_registry.json")
        payload = json.loads(registry.read_text(encoding="utf-8"))
        if not isinstance(payload, (dict, list)) or not payload:
            raise ValueError("empty registry")
        checks.append(_check("source_registry", "pass", "packaged source registry is readable"))
    except (OSError, json.JSONDecodeError, ValueError, ModuleNotFoundError):
        checks.append(_check("source_registry", "fail", "packaged source registry is missing or invalid"))
    return checks


def _cache_writable_check(cache_dir: Path) -> DiagnosticCheck:
    probe: Path | None = None
    try:
        cache_dir.mkdir(parents=True, exist_ok=True)
        with tempfile.NamedTemporaryFile(mode="wb", prefix=".doctor-", dir=cache_dir, delete=False) as stream:
            stream.write(b"doctor")
            probe = Path(stream.name)
        probe.unlink()
        return _check("cache_writable", "pass", "cache directory is writable")
    except OSError:
        if probe is not None:
            try:
                probe.unlink(missing_ok=True)
            except OSError:
                pass
        return _check("cache_writable", "fail", "cache directory is not writable")


def _dataset_checks(
    config: ConsumerConfig,
    manager: DatasetManager,
) -> tuple[list[DiagnosticCheck], str | None, Path | None]:
    checks: list[DiagnosticCheck] = []
    selected: str | None = None
    path: Path | None = None
    try:
        local_versions = manager.list_local()
        selected = config.dataset or (local_versions[-1] if local_versions else None)
        if selected is None:
            raise ArancelMXError("No verified local dataset is available")
        info = manager.verify(selected)
        if not info.structural_valid or not info.release_verified:
            raise ArancelMXError("local dataset is not fully verified")
        path = manager.selected_path(selected)
        checks.append(
            _check(
                "verified_dataset",
                "pass",
                "verified local dataset is usable",
                dataset=selected,
                dataset_version=info.dataset_version or "",
                schema_version=info.schema_version or "",
            )
        )
    except ArancelMXError:
        checks.append(_check("verified_dataset", "fail", "no usable verified local dataset is available"))

    if path is None:
        checks.append(_check("duckdb_query", "fail", "read-only dataset query cannot run without verified data"))
        checks.append(_check("offline_readiness", "fail", "offline mode has no usable verified dataset"))
        return checks, selected, None

    try:
        with duckdb_connect(path, read_only=True) as connection:
            row = connection.execute(
                "SELECT code FROM arancel_mx WHERE is_current = TRUE ORDER BY code ASC LIMIT 1"
            ).fetchone()
        if row is None or not row[0]:
            raise duckdb.Error("no current tariff rows")
        checks.append(
            _check(
                "duckdb_query",
                "pass",
                "read-only DuckDB query succeeded",
                sample_code=str(row[0]),
                read_only="true",
            )
        )
        checks.append(
            _check(
                "offline_readiness",
                "pass",
                "verified dataset is ready for offline queries",
                dataset=selected or "",
            )
        )
    except (duckdb.Error, OSError):
        checks.append(_check("duckdb_query", "fail", "read-only DuckDB query failed"))
        checks.append(_check("offline_readiness", "fail", "verified dataset is not ready for offline queries"))
    return checks, selected, path


def _network_check(config: ConsumerConfig, manager: DatasetManager) -> DiagnosticCheck:
    if config.offline:
        return _check("network_release", "skip", "network check skipped by offline mode")
    try:
        remote = manager.list_remote()
        if not remote:
            return _check("network_release", "warn", "no valid remote data releases were found")
        return _check("network_release", "pass", "public release metadata is reachable", latest=remote[0])
    except ArancelMXError:
        return _check("network_release", "warn", "public release metadata is currently unreachable")


def run_doctor(
    config: ConsumerConfig,
    *,
    manager: DatasetManager | None = None,
) -> DoctorResult:
    """Run deterministic diagnostics without exposing environment values or secrets."""

    active_manager = manager if manager is not None else DatasetManager(config)
    checks = _package_checks()
    checks.append(_cache_writable_check(config.cache_dir))
    dataset_checks, _, _ = _dataset_checks(config, active_manager)
    checks.extend(dataset_checks)
    checks.append(_network_check(config, active_manager))
    if any(check.status == "fail" for check in checks):
        status: DoctorStatus = "UNHEALTHY"
    elif any(check.status == "warn" for check in checks):
        status = "DEGRADED"
    else:
        status = "HEALTHY"
    return DoctorResult(status=status, checks=tuple(checks))


def doctor_to_dict(result: DoctorResult) -> dict[str, object]:
    """Convert a doctor result into its stable machine-readable schema."""

    return {
        "checks": [
            {
                "detail": check.detail,
                "metadata": dict(check.metadata),
                "name": check.name,
                "status": check.status,
            }
            for check in result.checks
        ],
        "exit_code": result.exit_code,
        "status": result.status,
    }


def render_doctor_human(result: DoctorResult) -> str:
    """Render compact diagnostics without ANSI state or sensitive values."""

    marker = {"pass": "OK", "warn": "WARN", "fail": "FAIL", "skip": "SKIP"}
    lines = ["arancel-mx doctor", ""]
    lines.extend(f"[{marker[check.status]}] {check.name}: {check.detail}" for check in result.checks)
    lines.extend(["", f"Status: {result.status}"])
    return "\n".join(lines)
