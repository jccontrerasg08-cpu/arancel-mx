"""Consumer command parser composition and, later, command handlers."""

from __future__ import annotations

import argparse


_OUTPUT_FORMATS = ("table", "json", "csv")


def _add_dataset_selection(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--dataset",
        help="Pin an exact data-YYYY.MM.DD release instead of the latest selection",
    )
    parser.add_argument(
        "--offline",
        action="store_true",
        default=None,
        help="Use verified local data only and make no network requests",
    )


def _add_output_format(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--format",
        choices=_OUTPUT_FORMATS,
        default="table",
        help="Output format (default: table)",
    )


def _add_query_command(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
    name: str,
    *,
    help_text: str,
    positional: str = "code",
) -> argparse.ArgumentParser:
    parser = subparsers.add_parser(name, help=help_text)
    parser.add_argument(positional)
    _add_dataset_selection(parser)
    _add_output_format(parser)
    parser.set_defaults(consumer_action=name)
    return parser


def register_consumer_commands(
    subparsers: argparse._SubParsersAction[argparse.ArgumentParser],
) -> None:
    """Register the stable consumer command surface on the shared CLI parser."""

    doctor = subparsers.add_parser(
        "doctor",
        help="Diagnostica instalación, cache, datos y acceso público",
    )
    _add_dataset_selection(doctor)
    doctor.add_argument(
        "--json",
        action="store_true",
        help="Emit deterministic machine-readable diagnostics",
    )
    doctor.set_defaults(consumer_action="doctor")

    data = subparsers.add_parser(
        "data",
        help="Administra versiones verificadas del dataset público",
    )
    data_subparsers = data.add_subparsers(dest="data_command")

    status = data_subparsers.add_parser("status", help="Muestra estado local y remoto")
    _add_dataset_selection(status)
    _add_output_format(status)
    status.set_defaults(consumer_action="data_status")

    download = data_subparsers.add_parser(
        "download", help="Descarga y verifica un dataset antes de promoverlo al cache"
    )
    _add_dataset_selection(download)
    _add_output_format(download)
    download.set_defaults(consumer_action="data_download")

    update = data_subparsers.add_parser(
        "update", help="Descarga la release más reciente sin borrar versiones previas"
    )
    _add_dataset_selection(update)
    _add_output_format(update)
    update.set_defaults(consumer_action="data_update")

    list_command = data_subparsers.add_parser(
        "list", help="Lista datasets verificados locales o releases remotas válidas"
    )
    _add_dataset_selection(list_command)
    _add_output_format(list_command)
    list_command.add_argument(
        "--remote",
        action="store_true",
        help="List metadata from valid remote releases instead of local cache",
    )
    list_command.set_defaults(consumer_action="data_list")

    path = data_subparsers.add_parser(
        "path", help="Imprime únicamente la ruta local del DuckDB seleccionado"
    )
    _add_dataset_selection(path)
    path.set_defaults(consumer_action="data_path")

    verify = data_subparsers.add_parser(
        "verify", help="Revalida integridad local y opcionalmente la release remota"
    )
    _add_dataset_selection(verify)
    _add_output_format(verify)
    verify.add_argument(
        "--online",
        action="store_true",
        help="Compare cached metadata against the exact remote release",
    )
    verify.add_argument(
        "--bundle",
        action="store_true",
        help="Download and verify all six public release assets temporarily",
    )
    verify.set_defaults(consumer_action="data_verify")

    lookup = _add_query_command(
        subparsers,
        "lookup",
        help_text="Busca un código arancelario exacto",
    )
    lookup.set_defaults(consumer_action="lookup")

    search = _add_query_command(
        subparsers,
        "search",
        help_text="Busca por código o descripción",
        positional="text",
    )
    search.add_argument("--limit", type=int, default=20)
    search.set_defaults(consumer_action="search")

    _add_query_command(
        subparsers,
        "parent",
        help_text="Devuelve el padre directo de un código",
    )
    _add_query_command(
        subparsers,
        "children",
        help_text="Devuelve los hijos directos de un código",
    )
    _add_query_command(
        subparsers,
        "provenance",
        help_text="Muestra las fuentes trazables de un código",
    )
