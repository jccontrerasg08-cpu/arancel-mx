from __future__ import annotations

import argparse
from collections.abc import Sequence


COMMANDS = ("build", "update", "reconcile", "release")


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="arancel-mx",
        description="Construye y valida datos arancelarios de México.",
    )
    subparsers = parser.add_subparsers(dest="command")
    for command in COMMANDS:
        subparsers.add_parser(command)
    return parser


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
    raise RuntimeError(f"El comando {namespace.command!r} aún no está conectado.")


entrypoint = main
