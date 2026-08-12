"""Command-line interface for consumer and tariff-maintainer workflows."""

from __future__ import annotations

import argparse
from collections.abc import Sequence
from dataclasses import asdict, is_dataclass
from datetime import date, datetime
import importlib
import json
from pathlib import Path
import sys
from typing import Any

import requests

from arancel_mx import __version__
from arancel_mx.consumer.cli import register_consumer_commands, run_consumer
from arancel_mx.consumer.errors import ArancelMXError


COMMANDS = ("build", "check-updates", "update", "reconcile", "release")
_MAINTAINER_HINT = (
    "This command needs the maintainer dependencies. "
    'Install them with: pip install "arancel-mx[maintainer]"'
)


def _missing_maintainer_extra(exc: ModuleNotFoundError) -> ValueError:
    missing = exc.name or "a required package"
    return ValueError(f"{_MAINTAINER_HINT} (missing: {missing})")


def _invoke_maintainer(
    module_name: str,
    attr: str,
    *args: object,
    **kwargs: object,
) -> object:
    try:
        implementation = getattr(importlib.import_module(module_name), attr)
        return implementation(*args, **kwargs)
    except ModuleNotFoundError as exc:
        raise _missing_maintainer_extra(exc) from exc


def build_release(database: Path, output: Path) -> object:
    """Lazy maintainer wrapper for release building."""

    return _invoke_maintainer(
        "arancel_mx.release.package",
        "build_release",
        database,
        output,
    )


def check_for_updates(config: object) -> object:
    """Lazy maintainer wrapper for official-source update checks."""

    return _invoke_maintainer("arancel_mx.pipeline.update", "check_for_updates", config)


def reconcile_legal_instruments(*items: object) -> object:
    """Lazy maintainer wrapper for legal-evidence reconciliation."""

    return _invoke_maintainer(
        "arancel_mx.pipeline.reconcile",
        "reconcile_legal_instruments",
        *items,
    )


def prepare_release_archive(*paths: Path) -> object:
    """Lazy maintainer wrapper for publication bundle preparation."""

    return _invoke_maintainer(
        "arancel_mx.release.package",
        "prepare_release_archive",
        *paths,
    )


def _add_update_arguments(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--state-path", default="data/update_state/ligie_ledger.json")
    parser.add_argument("--report-path")
    parser.add_argument("--ledger-url")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="arancel-mx",
        description="Consulta, verifica y construye datos arancelarios de México.",
    )
    parser.add_argument(
        "--version",
        action="version",
        version=f"%(prog)s {__version__}",
    )
    subparsers = parser.add_subparsers(dest="command")

    register_consumer_commands(subparsers)

    build = subparsers.add_parser("build", help="Exporta una base arancelaria validada")
    build.add_argument("--database", required=True)
    build.add_argument("--output-dir", required=True)

    check_updates = subparsers.add_parser(
        "check-updates",
        help="Comprueba cambios del ledger oficial sin modificar el estado aceptado",
    )
    _add_update_arguments(check_updates)

    update = subparsers.add_parser(
        "update",
        help="Alias obsoleto y de solo lectura para check-updates",
    )
    _add_update_arguments(update)

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


def _update_config(namespace: argparse.Namespace) -> object:
    options: dict[str, object] = {
        "state_path": Path(namespace.state_path),
        "report_path": Path(namespace.report_path) if namespace.report_path else None,
    }
    if namespace.ledger_url:
        options["ledger_url"] = namespace.ledger_url
    return _invoke_maintainer("arancel_mx.pipeline.update", "UpdateConfig", **options)


def _dispatch(namespace: argparse.Namespace) -> object:
    if namespace.command == "build":
        return build_release(Path(namespace.database), Path(namespace.output_dir))
    if namespace.command in {"check-updates", "update"}:
        return check_for_updates(_update_config(namespace))
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

    try:
        namespace = parser.parse_args(arguments)
    except SystemExit as exc:
        # argparse uses SystemExit for help/version as well as syntax errors. The
        # console entrypoint can return the same code while remaining easy to test.
        return int(exc.code or 0)

    if namespace.command is None:
        parser.print_help()
        return 0
    if namespace.command == "update":
        print(
            "warning: 'update' is a deprecated read-only alias; use check-updates",
            file=sys.stderr,
        )

    if hasattr(namespace, "consumer_action"):
        try:
            return run_consumer(namespace)
        except ArancelMXError as error:
            print(f"error: {error}", file=sys.stderr)
            return 2

    try:
        _print_json(_dispatch(namespace))
    except (
        ValueError,
        FileNotFoundError,
        json.JSONDecodeError,
        requests.RequestException,
    ) as error:
        print(f"error: {error}", file=sys.stderr)
        return 2
    return 0


entrypoint = main
