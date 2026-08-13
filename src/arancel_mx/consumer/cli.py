"""Consumer command parser composition and command handlers."""

from __future__ import annotations

import argparse
import sys

from arancel_mx.consumer.config import resolve_config
from arancel_mx.consumer.dataset import Dataset
from arancel_mx.consumer.doctor import doctor_to_dict, render_doctor_human, run_doctor
from arancel_mx.consumer.errors import DatasetUnavailableError
from arancel_mx.consumer.manager import DatasetManager
from arancel_mx.consumer.output import CsvSchema, render, render_json


_OUTPUT_FORMATS = ("table", "json", "csv")
_QUERY_ACTIONS = {
    "lookup",
    "search",
    "parent",
    "children",
    "provenance",
    "ficha",
    "chapters",
    "compare",
}
_QUERY_CSV_SCHEMAS: dict[str, CsvSchema] = {
    "lookup": "tariff",
    "search": "search",
    "parent": "tariff",
    "children": "tariff",
    "provenance": "provenance",
    "ficha": "ficha",
    "chapters": "tariff",
    "compare": "compare",
}


def _positive_int(value: str) -> int:
    try:
        parsed = int(value)
    except ValueError as exc:
        raise argparse.ArgumentTypeError("must be an integer greater than zero") from exc
    if parsed <= 0:
        raise argparse.ArgumentTypeError("must be greater than zero")
    return parsed


def _add_offline(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--offline",
        action=argparse.BooleanOptionalAction,
        default=None,
        help="Use verified local data only and make no network requests",
    )


def _add_dataset_selection(parser: argparse.ArgumentParser) -> None:
    parser.add_argument(
        "--dataset",
        help="Pin an exact data-YYYY.MM.DD release instead of the latest selection",
    )
    _add_offline(parser)


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
    data_subparsers = data.add_subparsers(dest="data_command", required=True)

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
    _add_offline(update)
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

    _add_query_command(
        subparsers,
        "lookup",
        help_text="Busca un código arancelario exacto",
    )

    search = _add_query_command(
        subparsers,
        "search",
        help_text="Busca por código o descripción",
        positional="text",
    )
    search.add_argument("--limit", type=_positive_int, default=20)

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
    _add_query_command(
        subparsers,
        "ficha",
        help_text="Muestra la ficha jerárquica (capítulo → fracción/NICO) de un código",
    )
    _add_query_command(
        subparsers,
        "compare",
        help_text="Compara HS6, MX8 o NICO del dataset GitHub con VUCEM (informativo)",
    )
    chapters = subparsers.add_parser(
        "chapters",
        help="Lista los capítulos HS2 vigentes",
    )
    _add_dataset_selection(chapters)
    _add_output_format(chapters)
    chapters.set_defaults(consumer_action="chapters")


def _consumer_config(namespace: argparse.Namespace):
    options: dict[str, object] = {}
    if getattr(namespace, "dataset", None) is not None:
        options["dataset"] = namespace.dataset
    if getattr(namespace, "offline", None) is not None:
        options["offline"] = namespace.offline
    try:
        return resolve_config(**options)
    except ValueError as exc:
        raise DatasetUnavailableError(
            f"invalid consumer configuration: {exc}"
        ) from exc


def _selected_dataset(namespace: argparse.Namespace) -> Dataset:
    # Validate environment/configuration through the same public error boundary
    # used by data and doctor before Dataset resolves it internally.
    _consumer_config(namespace)
    options = {"offline": namespace.offline}
    if namespace.dataset:
        return Dataset.version(namespace.dataset, **options)
    return Dataset.latest(**options)


def _manager(namespace: argparse.Namespace) -> DatasetManager:
    return DatasetManager(_consumer_config(namespace))


def _emit(
    value: object,
    *,
    format_name: str,
    empty_csv_schema: CsvSchema | None = None,
) -> None:
    text = render(
        value,
        format_name=format_name,
        empty_csv_schema=empty_csv_schema,
    )
    sys.stdout.write(text)
    if text and not text.endswith("\n"):
        sys.stdout.write("\n")


def _run_query(namespace: argparse.Namespace) -> int:
    dataset = _selected_dataset(namespace)
    action = namespace.consumer_action
    if action == "lookup":
        value: object = dataset.lookup(namespace.code)
    elif action == "search":
        value = dataset.search(namespace.text, limit=namespace.limit)
    elif action == "parent":
        parent_record = dataset.parent(namespace.code)
        value = () if parent_record is None and namespace.format != "json" else parent_record
    elif action == "children":
        value = dataset.children(namespace.code)
    elif action == "provenance":
        value = dataset.provenance(namespace.code)
    elif action == "ficha":
        value = dataset.ficha(namespace.code)
    elif action == "compare":
        value = dataset.compare(
            namespace.code, fetch=namespace.offline is not True
        )
    elif action == "chapters":
        value = dataset.chapters()
    else:
        raise ValueError(f"unsupported consumer query action: {action}")
    _emit(
        value,
        format_name=namespace.format,
        empty_csv_schema=_QUERY_CSV_SCHEMAS[action],
    )
    return 0


def _run_data_download(namespace: argparse.Namespace) -> int:
    manager = _manager(namespace)
    path = manager.ensure(namespace.dataset)
    _emit({"path": str(path), "status": "verified"}, format_name=namespace.format)
    return 0


def _run_data_path(namespace: argparse.Namespace) -> int:
    path = _manager(namespace).selected_path(namespace.dataset)
    sys.stdout.write(str(path) + "\n")
    return 0


def _run_data_status(namespace: argparse.Namespace) -> int:
    manager = _manager(namespace)
    local_versions = manager.list_local()
    local_latest = local_versions[-1] if local_versions else None
    selected = namespace.dataset or manager.config.dataset or local_latest
    remote_latest = None
    if not manager.config.offline:
        remote_versions = manager.list_remote()
        remote_latest = remote_versions[0] if remote_versions else None
    update_available = bool(
        remote_latest is not None and (local_latest is None or remote_latest > local_latest)
    )
    _emit(
        {
            "local_latest": local_latest,
            "local_versions": local_versions,
            "offline": manager.config.offline,
            "remote_latest": remote_latest,
            "selected": selected,
            "update_available": update_available,
        },
        format_name=namespace.format,
    )
    return 0


def _run_data_list(namespace: argparse.Namespace) -> int:
    manager = _manager(namespace)
    if namespace.remote:
        if manager.config.offline:
            raise DatasetUnavailableError(
                "remote dataset listing is unavailable in offline mode"
            )
        versions = manager.list_remote()
        scope = "remote"
    else:
        versions = manager.list_local()
        scope = "local"
    rows = tuple({"dataset": version, "scope": scope} for version in versions)
    _emit(
        rows,
        format_name=namespace.format,
        empty_csv_schema="dataset",
    )
    return 0


def _run_data_update(namespace: argparse.Namespace) -> int:
    manager = _manager(namespace)
    if manager.config.offline:
        raise DatasetUnavailableError(
            "dataset update requires network access and is unavailable in offline mode"
        )
    status, path = manager.update()
    _emit({"path": str(path), "status": status}, format_name=namespace.format)
    return 0


def _run_data_verify(namespace: argparse.Namespace) -> int:
    manager = _manager(namespace)
    if manager.config.offline and (namespace.online or namespace.bundle):
        raise DatasetUnavailableError(
            "online or bundle verification is unavailable in offline mode"
        )
    online = bool(namespace.online or namespace.bundle)
    info = manager.verify(
        namespace.dataset,
        online=online,
        bundle=bool(namespace.bundle),
    )
    _emit(info, format_name=namespace.format)
    return 0


def _run_doctor(namespace: argparse.Namespace) -> int:
    result = run_doctor(_consumer_config(namespace))
    if namespace.json:
        sys.stdout.write(render_json(doctor_to_dict(result)) + "\n")
    else:
        sys.stdout.write(render_doctor_human(result) + "\n")
    return result.exit_code


def run_consumer(namespace: argparse.Namespace) -> int:
    """Run one parsed consumer command and return its process exit code."""

    action = getattr(namespace, "consumer_action", None)
    if action in _QUERY_ACTIONS:
        return _run_query(namespace)
    if action == "data_download":
        return _run_data_download(namespace)
    if action == "data_path":
        return _run_data_path(namespace)
    if action == "data_status":
        return _run_data_status(namespace)
    if action == "data_list":
        return _run_data_list(namespace)
    if action == "data_update":
        return _run_data_update(namespace)
    if action == "data_verify":
        return _run_data_verify(namespace)
    if action == "doctor":
        return _run_doctor(namespace)
    raise ValueError(f"unsupported consumer command: {action}")
