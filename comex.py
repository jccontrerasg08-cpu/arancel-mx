"""Local CLI for NICO/TIGIE, ETL and VUCEM/ANAM watchers."""

from __future__ import annotations

import argparse
from datetime import date, datetime
import json
import sys
from pathlib import Path
from src.env import load_env

load_env()
from src.comex.cartera import add_cliente, cartera_summary, remove_cliente
from src.comex.catalogs import refresh_catalog_sql, rebuild_tigie_catalog, search_tigie
from src.comex.db import init_db
from src.comex.dof import dof_status, search_dof_publications
from src.comex.etl import SOURCES, etl_status, run_etl
from src.comex.forecast import forecast_monthly
from src.comex.legal_corpus import legal_corpus_status, retrieve_legal_context
from src.comex.rag import retrieve_rag_context
from src.comex.rag_security import scan_rag_corpus
from src.comex.site_audit import audit_site
from src.comex.warehouse import export_warehouse_to_json, load_json_cache_to_warehouse, warehouse_status
from src.comex.watchers import run_watch
from src.comex.arancel_release import build_arancel_release
from src.comex.arancel_publish import prepare_github_release
from src.comex.arancel_update import UpdateConfig, check_for_updates, run_legal_update, update_status


def _print_json(data: object) -> None:
    def serialize(value: object) -> str:
        if isinstance(value, datetime):
            return value.isoformat().replace("+00:00", "Z")
        if isinstance(value, date):
            return value.isoformat()
        raise TypeError(f"Object of type {type(value).__name__} is not JSON serializable")

    print(json.dumps(data, ensure_ascii=False, indent=2, default=serialize))


def _find_series(series: list, query: str):
    query = str(query or "").strip().lower()
    exact = next((item for item in series if item.nombre.lower() == query), None)
    return exact or next((item for item in series if query in item.nombre.lower()), None)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Herramientas locales de comercio exterior MX")
    sub = parser.add_subparsers(dest="command", required=True)

    sub.add_parser("init-db", help="Inicializa data/comex.duckdb")
    sub.add_parser("catalog-refresh", help="Reindexa catalogo SQL desde data/raw sin descargar")
    sub.add_parser("warehouse-refresh", help="Carga data/comercio_exterior.json hacia DuckDB")
    sub.add_parser("warehouse-status", help="Muestra estado del warehouse local DuckDB")
    sub.add_parser("warehouse-export", help="Exporta el estado DuckDB a data/comercio_exterior.json")
    arancel = sub.add_parser("arancel-build", help="Construye y valida la vista pública arancel_mx")
    arancel.add_argument("--source-dir", required=True)
    arancel.add_argument("--output-dir", required=True)
    arancel.add_argument("--dataset-version", required=True)
    arancel.add_argument("--effective-as-of", required=True)
    arancel.add_argument("--timeout", type=float)
    arancel_check = sub.add_parser("arancel-check", help="Compara el ledger LIGIE sin modificar el repositorio")
    arancel_check.add_argument("--state-path", default="data/arancel_mx/update_state/ligie_ledger.json")
    arancel_check.add_argument("--report-path")
    arancel_update = sub.add_parser("arancel-update", help="Ejecuta los trabajos legales selectivos y publica una vez")
    arancel_update.add_argument("--state-path", default="data/arancel_mx/update_state/ligie_ledger.json")
    arancel_update.add_argument("--report-path", default="data/arancel_mx/update_summary.json")
    arancel_status = sub.add_parser("arancel-status", help="Muestra el último ledger LIGIE validado")
    arancel_status.add_argument("--state-path", default="data/arancel_mx/update_state/ligie_ledger.json")
    package = sub.add_parser(
        "arancel-package-release", help="Verifica y prepara assets para GitHub Releases"
    )
    package.add_argument("--release-dir", required=True)
    package.add_argument("--source-dir", required=True)
    package.add_argument("--latest-dir", required=True)
    sub.add_parser("dof-status", help="Muestra publicaciones DOF de comercio exterior indexadas")
    dof_search = sub.add_parser("dof-search", help="Busca publicaciones DOF indexadas localmente")
    dof_search.add_argument("query")
    dof_search.add_argument("--limit", type=int, default=8)
    sub.add_parser("legal-corpus-status", help="Muestra documentos Markdown/TXT disponibles para el asistente")
    legal_search = sub.add_parser("legal-corpus-search", help="Busca fragmentos en el corpus documental local")
    legal_search.add_argument("query")
    legal_search.add_argument("--limit", type=int, default=5)
    rag_search = sub.add_parser("rag-search", help="Busca contexto RAG unificado para Comex Bot")
    rag_search.add_argument("query")
    sub.add_parser("rag-audit", help="Escanea el corpus RAG local por patrones riesgosos")
    site_audit = sub.add_parser("site-audit", help="Auditoria web pasiva: headers, endpoints y scripts")
    site_audit.add_argument("url")
    site_audit.add_argument("--timeout", type=int, default=10)
    forecast_cmd = sub.add_parser("forecast-serie", help="Pronostica una serie mensual del dashboard")
    forecast_cmd.add_argument("serie")
    forecast_cmd.add_argument("--horizon", type=int, default=12)

    etl = sub.add_parser("etl", help="Fuentes publicas ANAM/VUCEM")
    etl_sub = etl.add_subparsers(dest="etl_command", required=True)
    etl_run = etl_sub.add_parser("run", help="Descarga e indexa una fuente o todas")
    etl_run.add_argument("source", nargs="?", choices=sorted(SOURCES.keys()))
    etl_run.add_argument("--timeout", type=float, default=60.0)
    etl_sub.add_parser("status", help="Estado de manifest, fuentes y DuckDB")

    cartera = sub.add_parser("cartera", help="Cartera de RFCs vigilados")
    cartera_sub = cartera.add_subparsers(dest="cartera_command", required=True)
    cartera_sub.add_parser("list", help="Lista cartera")
    add = cartera_sub.add_parser("add", help="Agrega o reemplaza un RFC")
    add.add_argument("--rfc", required=True)
    add.add_argument("--razon", required=True)
    add.add_argument("--email")
    add.add_argument("--whatsapp")
    remove = cartera_sub.add_parser("remove", help="Elimina un RFC")
    remove.add_argument("rfc")

    watch = sub.add_parser("watch", help="Watchers publicos")
    watch_sub = watch.add_subparsers(dest="watch_command", required=True)
    run = watch_sub.add_parser("run", help="Ejecuta watcher VUCEM en dry-run/log")
    run.add_argument("--dry-run", action="store_true", default=True)

    buscar = sub.add_parser("buscar-fraccion", help="Busca fracciones TIGIE desde VUCEM")
    buscar.add_argument("descripcion")
    buscar.add_argument("--limit", type=int, default=5)
    buscar.add_argument("--rebuild", action="store_true", help="Reindexa assets locales antes de buscar")
    return parser


def main(argv: list[str] | None = None) -> int:
    args = build_parser().parse_args(argv)

    try:
        if args.command == "init-db":
            _print_json({"db": str(init_db()), "status": "ok"})
        elif args.command == "catalog-refresh":
            _print_json({"records_loaded": refresh_catalog_sql(), "status": "ok"})
        elif args.command == "warehouse-refresh":
            _print_json(load_json_cache_to_warehouse())
        elif args.command == "warehouse-status":
            _print_json(warehouse_status())
        elif args.command == "warehouse-export":
            _print_json(export_warehouse_to_json())
        elif args.command == "arancel-build":
            _print_json(build_arancel_release(
                Path(args.source_dir), Path(args.output_dir), args.dataset_version,
                args.effective_as_of, args.timeout,
            ))
        elif args.command == "arancel-check":
            config = UpdateConfig(
                state_path=Path(args.state_path),
                report_path=Path(args.report_path) if args.report_path else None,
            )
            _print_json(check_for_updates(config).to_dict())
        elif args.command == "arancel-update":
            config = UpdateConfig(state_path=Path(args.state_path), report_path=Path(args.report_path))
            _print_json(run_legal_update(config).to_dict())
        elif args.command == "arancel-status":
            _print_json(update_status(UpdateConfig(state_path=Path(args.state_path))))
        elif args.command == "arancel-package-release":
            _print_json(prepare_github_release(
                Path(args.release_dir), Path(args.source_dir), Path(args.latest_dir)
            ))
        elif args.command == "dof-status":
            _print_json(dof_status())
        elif args.command == "dof-search":
            _print_json(search_dof_publications(args.query, args.limit))
        elif args.command == "legal-corpus-status":
            _print_json(legal_corpus_status())
        elif args.command == "legal-corpus-search":
            _print_json(retrieve_legal_context(args.query, args.limit))
        elif args.command == "rag-search":
            _print_json([block.to_dict() for block in retrieve_rag_context(args.query)])
        elif args.command == "rag-audit":
            _print_json(scan_rag_corpus())
        elif args.command == "site-audit":
            _print_json(audit_site(args.url, args.timeout))
        elif args.command == "forecast-serie":
            from src.data_service import DataService

            data = DataService().get_data()
            serie = _find_series(data.series, args.serie)
            if not serie:
                raise ValueError("Serie no encontrada")
            _print_json({"serie": serie.nombre, **forecast_monthly(serie.fechas, serie.valores, args.horizon)})
        elif args.command == "etl" and args.etl_command == "run":
            _print_json(run_etl(args.source, timeout_s=args.timeout))
        elif args.command == "etl" and args.etl_command == "status":
            _print_json(etl_status())
        elif args.command == "cartera" and args.cartera_command == "list":
            _print_json(cartera_summary())
        elif args.command == "cartera" and args.cartera_command == "add":
            _print_json(add_cliente(args.rfc, args.razon, args.email, args.whatsapp))
        elif args.command == "cartera" and args.cartera_command == "remove":
            _print_json({"removed": remove_cliente(args.rfc)})
        elif args.command == "watch" and args.watch_command == "run":
            _print_json(run_watch(dry_run=True))
        elif args.command == "buscar-fraccion":
            if args.rebuild:
                rebuild_tigie_catalog()
            _print_json(search_tigie(args.descripcion, args.limit))
        else:
            raise ValueError("Comando no reconocido")
        return 0
    except Exception as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
