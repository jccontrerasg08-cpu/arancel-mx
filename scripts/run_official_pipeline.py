"""Run the official dataset build and always emit structured diagnostics."""

from __future__ import annotations

import argparse
from collections.abc import Mapping, Sequence
from datetime import date, datetime, timezone
import json
import os
from pathlib import Path
import sys
import tempfile
from typing import Any, Callable
from zipfile import BadZipFile

import requests
from xlrd.biffh import XLRDError

from arancel_mx.pipeline.official_dataset import (
    OfficialDatasetConfig,
    build_official_dataset,
)


MAX_DIAGNOSTIC_LENGTH = 1200
_SECRET_KEY_MARKERS = ("TOKEN", "SECRET", "PASSWORD", "PRIVATE_KEY", "API_KEY")


def _sanitize_message(message: object) -> str:
    text = " ".join(str(message).split())
    secret_values = {
        value
        for key, value in os.environ.items()
        if value and any(marker in key.upper() for marker in _SECRET_KEY_MARKERS)
    }
    for value in sorted(secret_values, key=len, reverse=True):
        text = text.replace(value, "[REDACTED]")
    if len(text) > MAX_DIAGNOSTIC_LENGTH:
        text = text[: MAX_DIAGNOSTIC_LENGTH - 3] + "..."
    return text or "pipeline failed without an error message"


def classify_failure(error: BaseException) -> str:
    message = str(error).lower()
    if "legal reconciliation" in message or "missing_dof_evidence" in message:
        return "legal_reconciliation"
    if isinstance(error, requests.RequestException):
        return "source_network"
    if "missing official snapshot" in message or "ambiguous official snapshot" in message:
        return "source_discovery"
    if "source registry" in message or "registered source" in message:
        return "source_registry"
    if "checksum" in message or ("sha256" in message and "mismatch" in message):
        return "checksum"
    if "profile" in message:
        return "parser_profile"
    if isinstance(error, (BadZipFile, XLRDError)):
        return "parser"
    if any(word in message for word in ("workbook", "parser", "parse ", "pdf")):
        return "parser"
    if any(
        phrase in message
        for phrase in (
            "validation",
            "canonical database",
            "tariff values",
            "row_count",
            "contains no rows",
            "contains no tariff",
            "validation_status",
        )
    ):
        return "validation"
    if isinstance(error, (ValueError, OSError)):
        return "domain_error"
    return "unexpected_error"


def _atomic_write_json(path: Path, value: Mapping[str, object]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    payload = json.dumps(
        value,
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    ) + "\n"
    handle = tempfile.NamedTemporaryFile(
        mode="w",
        encoding="utf-8",
        newline="",
        dir=path.parent,
        prefix=f".{path.name}.",
        suffix=".tmp",
        delete=False,
    )
    temporary = Path(handle.name)
    try:
        with handle:
            handle.write(payload)
            handle.flush()
            os.fsync(handle.fileno())
        temporary.replace(path)
    except Exception:
        temporary.unlink(missing_ok=True)
        raise


def execute_pipeline(
    config: OfficialDatasetConfig,
    *,
    previous_manifest: Mapping[str, object] | None,
    result_path: Path,
    builder: Callable[..., dict[str, object]] = build_official_dataset,
) -> tuple[int, dict[str, object]]:
    try:
        summary = builder(config, previous_manifest=previous_manifest)
        status = summary.get("status")
        if status == "no_change":
            result: dict[str, object] = {
                "status": "no_change",
                "stage": "complete",
                "dataset_version": config.dataset_version,
                "artifact_name": config.github_artifact_name,
                "message": "registered source identity is unchanged",
            }
        elif status == "built":
            if not config.output_dir.is_dir():
                raise ValueError("successful build did not create the release directory")
            result = {
                "status": "built",
                "stage": "complete",
                "dataset_version": config.dataset_version,
                "artifact_name": config.github_artifact_name,
                "release_dir": str(config.output_dir),
            }
        else:
            raise ValueError(f"unsupported official pipeline status: {status}")
        exit_code = 0
    except Exception as error:  # noqa: BLE001 - automation boundary must diagnose all failures
        result = {
            "status": "failed",
            "stage": "build",
            "dataset_version": config.dataset_version,
            "failure_category": classify_failure(error),
            "message": _sanitize_message(error),
        }
        exit_code = 2

    try:
        _atomic_write_json(Path(result_path), result)
    except Exception as write_error:  # noqa: BLE001 - preserve a diagnostic on stderr
        print(
            f"error: unable to write pipeline diagnostics: {_sanitize_message(write_error)}",
            file=sys.stderr,
        )
        return 2, result
    return exit_code, result


def _parse_generated_at(value: str | None) -> datetime:
    if value is None:
        return datetime.now(timezone.utc).replace(microsecond=0)
    normalized = value[:-1] + "+00:00" if value.endswith("Z") else value
    parsed = datetime.fromisoformat(normalized)
    if parsed.tzinfo is None or parsed.utcoffset() is None:
        raise ValueError("generated-at must include a timezone")
    return parsed.astimezone(timezone.utc).replace(microsecond=0)


def _load_previous_manifest(path: Path | None) -> dict[str, object] | None:
    if path is None or not path.exists():
        return None
    value = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(value, dict):
        raise ValueError("previous manifest must contain a JSON object")
    return value


def _provenance_from_environment() -> dict[str, str]:
    run_id = os.getenv("GITHUB_RUN_ID", "local")
    run_attempt = os.getenv("GITHUB_RUN_ATTEMPT", "local")
    artifact_name = os.getenv("ARANCEL_MX_ARTIFACT_NAME")
    if not artifact_name:
        artifact_name = (
            f"arancel-mx-{run_id}-{run_attempt}"
            if run_id != "local" and run_attempt != "local"
            else "local"
        )
    return {
        "git_commit_sha": os.getenv("GITHUB_SHA", "local"),
        "github_run_id": run_id,
        "github_run_attempt": run_attempt,
        "github_workflow_ref": os.getenv("GITHUB_WORKFLOW_REF", "local"),
        "github_artifact_name": artifact_name,
    }


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--work-dir", type=Path, default=Path("out/work"))
    parser.add_argument("--output-dir", type=Path, default=Path("out/release"))
    parser.add_argument("--effective-as-of", required=True)
    parser.add_argument("--dataset-version", required=True)
    parser.add_argument("--generated-at")
    parser.add_argument("--timeout", type=float, default=60.0)
    parser.add_argument("--previous-manifest", type=Path)
    parser.add_argument(
        "--result-path",
        type=Path,
        default=Path("out/pipeline-result.json"),
    )
    return parser


def _config_from_args(args: argparse.Namespace) -> OfficialDatasetConfig:
    if args.timeout <= 0:
        raise ValueError("timeout must be positive")
    try:
        effective_as_of = date.fromisoformat(args.effective_as_of)
    except ValueError as exc:
        raise ValueError("effective-as-of must use YYYY-MM-DD") from exc
    return OfficialDatasetConfig(
        work_dir=args.work_dir,
        output_dir=args.output_dir,
        effective_as_of=effective_as_of,
        dataset_version=args.dataset_version,
        generated_at=_parse_generated_at(args.generated_at),
        timeout_s=args.timeout,
        **_provenance_from_environment(),
    )


def main(argv: Sequence[str] | None = None) -> int:
    args = build_parser().parse_args(list(argv) if argv is not None else None)
    result_path = Path(args.result_path)
    try:
        config = _config_from_args(args)
        previous_manifest = _load_previous_manifest(args.previous_manifest)
    except Exception as error:  # noqa: BLE001 - configuration must also emit diagnostics
        dataset_version = str(getattr(args, "dataset_version", "unknown"))
        result = {
            "status": "failed",
            "stage": "configuration",
            "dataset_version": dataset_version,
            "failure_category": classify_failure(error),
            "message": _sanitize_message(error),
        }
        try:
            _atomic_write_json(result_path, result)
        except Exception as write_error:  # noqa: BLE001
            print(
                f"error: unable to write pipeline diagnostics: {_sanitize_message(write_error)}",
                file=sys.stderr,
            )
        print(json.dumps(result, ensure_ascii=False, sort_keys=True))
        return 2

    exit_code, result = execute_pipeline(
        config,
        previous_manifest=previous_manifest,
        result_path=result_path,
    )
    print(json.dumps(result, ensure_ascii=False, sort_keys=True))
    return exit_code


if __name__ == "__main__":
    raise SystemExit(main())
