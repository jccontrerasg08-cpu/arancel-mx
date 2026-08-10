"""Command-line interface for tariff build and release workflows."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from dataclasses import asdict, is_dataclass
from datetime import date, datetime
import json
from pathlib import Path
import sys
from typing import Any

import requests

from arancel_mx.pipeline.reconcile import reconcile_legal_instruments
from arancel_mx.pipeline.update import UpdateConfig, check_for_updates
from arancel_mx.release.package import build_release, prepare_release_archive


COMMANDS = ("build", "update", "reconcile", "release")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="arancel-mx",
        description="Construye y valida datos arancelarios de México.",
    )
    subparsers = parser.add_subparsers(dest="command")

    build = subparsers.add_parser("build", help="Exporta una base arancelaria validada")
    build.add_argument("--database", required=True)
    build.add_argument("--output-dir", required=True)

    update = subparsers.add_parser("update", help="Comprueba el ledger oficial de la LIGIE")
    update.add_argument("--state-path", default="data/update_state/ligie_ledger.json")
    update.add_argument("--report-path")
    update.add_argument("--ledger-url")

    reconcile = subparsers.add_parser("reconcile", help="Reconcilia evidencia legal arancelaria")
    reconcile.add_argument("--ledger-json", required=True)
    reconcile.add_argument("--dof-json", required=True)
    reconcile.add_argument("--snice-json", required=True)

    release = subparsers.add_parser("release", help="Verifica y prepara artefactos de publicación")
    release.add_argument("--release-dir", required=True)
    release.add_argument("--source-dir", required=True)
    release.add_argument("--latest-dir", required=True)
    return parser


def _json_default(value: object) -> object:
    if hasattr(value, "to_dict"):
        return value.to_dict()
    if is_dataclass(value):
        return asdict(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")


def _print_json(value: object) -> None:
    print(json.dumps(value, default=_json_default, ensure_ascii=False, sort_keys=True))


def _read_json(path: str) -> Any:
    return json.loads(Path(path).read_text(encoding="utf-8"))


def _dispatch(namespace: argparse.Namespace) -> object:
    if namespace.command == "build":
        return build_release(Path(namespace.database), Path(namespace.output_dir))
    if namespace.command == "update":
        options: dict[str, object] = {
            "state_path": Path(namespace.state_path),
            "report_path": Path(namespace.report_path) if namespace.report_path else None,
        }
        if namespace.ledger_url:
            options["ledger_url"] = namespace.ledger_url
        return check_for_updates(UpdateConfig(**options))
    if namespace.command == "reconcile":
        return reconcile_legal_instruments(
            _read_json(namespace.ledger_json),
            _read_json(namespace.dof_json),
            _read_json(namespace.snice_json),
        )
    if namespace.command == "release":
        return prepare_release_archive(
            Path(namespace.release_dir),
            Path(namespace.source_dir),
            Path(namespace.latest_dir),
        )
    raise ValueError(f"Unsupported command: {namespace.command}")


def main(argv: Sequence[str] | None = None) -> int:
    parser = build_parser()
    arguments = list(argv) if argv is not None else None
    if arguments == []:
        parser.print_help()
        return 0

    namespace = parser.parse_args(arguments)
    if namespace.command is None:
        parser.print_help()
        return 0
    try:
        _print_json(_dispatch(namespace))
    except (ValueError, FileNotFoundError, json.JSONDecodeError, requests.RequestException) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    return 0


entrypoint = main
