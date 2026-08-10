"""Local DuckDB warehouse for dashboard-grade comercio exterior data."""

from __future__ import annotations

import json
from copy import deepcopy
from datetime import datetime
from pathlib import Path
from typing import Any

from src.models import DatosComercio, Serie

from . import db
from .paths import DATA_DIR, DB_PATH


JSON_CACHE_PATH = DATA_DIR / "comercio_exterior.json"


def _parse_datetime(value: Any, source_mtime: float | None = None) -> datetime:
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        candidate = value
        if len(candidate) == 10 and source_mtime:
            return datetime.fromtimestamp(source_mtime)
        try:
            return datetime.fromisoformat(candidate.replace("Z", "+00:00")).replace(tzinfo=None)
        except ValueError:
            pass
    if source_mtime:
        return datetime.fromtimestamp(source_mtime)
    return datetime.now()


def datos_from_payload(payload: dict[str, Any], source_mtime: float | None = None) -> DatosComercio:
    """Build the dashboard dataclass from a cache/export payload."""
    series = [
        Serie(
            nombre=str(item.get("nombre", "")),
            serie_id=str(item.get("serie_id", item.get("idSerie", ""))),
            flujo=str(item.get("flujo", "")),
            grupo=str(item.get("grupo", "")),
            fechas=[str(date_value) for date_value in item.get("fechas", [])],
            valores=[None if value is None else float(value) for value in item.get("valores", [])],
        )
        for item in payload.get("series", [])
    ]
    return DatosComercio(
        fuente=str(payload.get("fuente", "")),
        actualizado=_parse_datetime(payload.get("actualizado"), source_mtime),
        completo=bool(payload.get("completo", False)),
        series=series,
        anual=dict(payload.get("anual", {})),
        acumulado=dict(payload.get("acumulado", {})),
        paises_balanza=list(payload.get("paises_balanza", [])),
        aduanas=list(payload.get("aduanas", [])),
        industrias_exportacion=list(payload.get("industrias_exportacion", [])),
        importaciones_uso=list(payload.get("importaciones_uso", [])),
        balanza_componentes=list(payload.get("balanza_componentes", [])),
        recaudacion_aduanas=payload.get("recaudacion_aduanas"),
    )


def load_json_cache_to_warehouse(
    path: Path = JSON_CACHE_PATH,
    db_path: Path = DB_PATH,
) -> dict[str, Any]:
    """Load the legacy JSON cache into normalized DuckDB warehouse tables."""
    if not path.exists():
        return {"status": "missing", "source_file": str(path), "records_loaded": 0}
    source_mtime = path.stat().st_mtime
    payload = json.loads(path.read_text(encoding="utf-8"))
    data = datos_from_payload(payload, source_mtime)
    return save_dashboard_to_warehouse(
        data,
        db_path=db_path,
        source_code="json-cache",
        source_file=str(path),
        source_mtime=source_mtime,
    )


def save_dashboard_to_warehouse(
    data: DatosComercio,
    db_path: Path = DB_PATH,
    source_code: str = "dashboard",
    source_file: str | None = None,
    source_mtime: float | None = None,
) -> dict[str, Any]:
    """Replace dashboard warehouse facts in one transaction."""
    db.init_db(db_path)
    started_at = db.utc_now_naive()
    records_loaded = 0
    with db.connect(db_path) as conn:
        snapshot_id = db.next_id(conn, "warehouse_snapshot", "snapshot_id")
        try:
            conn.execute("BEGIN TRANSACTION")
            conn.execute(
                """
                INSERT INTO warehouse_snapshot (
                    snapshot_id, source_code, source_file, source_mtime, fuente,
                    actualizado, completo, status, started_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, 'RUNNING', ?)
                """,
                [
                    snapshot_id,
                    source_code,
                    source_file,
                    source_mtime,
                    data.fuente,
                    data.actualizado,
                    data.completo,
                    started_at,
                ],
            )

            for table in (
                "dim_banxico_series",
                "fact_banxico_series_monthly",
                "fact_dashboard_annual",
                "fact_dashboard_accumulated",
                "fact_country_balance",
                "dim_customs",
                "fact_customs_revenue",
                "fact_trade_component",
                "dashboard_country_balance",
                "dashboard_customs_revenue",
                "dashboard_cache_payload",
            ):
                conn.execute(f"DELETE FROM {table}")

            series_rows = [
                (serie.serie_id, serie.nombre, serie.flujo, serie.grupo, "miles de dolares", "banxico-sie")
                for serie in data.series
                if serie.serie_id
            ]
            if series_rows:
                conn.executemany(
                    """
                    INSERT INTO dim_banxico_series (
                        series_id, nombre, flujo, grupo, unit_name, source_code
                    )
                    VALUES (?, ?, ?, ?, ?, ?)
                    """,
                    series_rows,
                )
                records_loaded += len(series_rows)

            monthly_rows = []
            for serie in data.series:
                for fecha, value in zip(serie.fechas, serie.valores):
                    if value is None:
                        continue
                    try:
                        date_month = datetime.fromisoformat(str(fecha).replace("Z", "+00:00")).date()
                    except ValueError:
                        continue
                    monthly_rows.append((serie.serie_id, date_month, float(value), "banxico-sie"))
            if monthly_rows:
                conn.executemany(
                    """
                    INSERT INTO fact_banxico_series_monthly (
                        series_id, date_month, value, source_code
                    )
                    VALUES (?, ?, ?, ?)
                    """,
                    monthly_rows,
                )
                records_loaded += len(monthly_rows)

            anual = data.anual or {}
            period = str(anual.get("anio") or "")
            if period:
                conn.execute(
                    """
                    INSERT INTO fact_dashboard_annual VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                    """,
                    [
                        period,
                        _float_or_none(anual.get("exportaciones")),
                        _float_or_none(anual.get("importaciones")),
                        _float_or_none(anual.get("balanza")),
                    ],
                )
                records_loaded += 1

            acumulado = data.acumulado or {}
            label = str(acumulado.get("periodo") or "")
            accumulated_rows = []
            for year, values in acumulado.items():
                if year == "periodo" or not isinstance(values, dict):
                    continue
                accumulated_rows.append(
                    (
                        label,
                        str(year),
                        _float_or_none(values.get("exportaciones")),
                        _float_or_none(values.get("importaciones")),
                        _float_or_none(values.get("balanza")),
                    )
                )
            if accumulated_rows:
                conn.executemany(
                    """
                    INSERT INTO fact_dashboard_accumulated
                    VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    """,
                    accumulated_rows,
                )
                records_loaded += len(accumulated_rows)

            country_period = period or "actual"
            country_rows = [
                (country_period, str(row[0]), str(row[1]), _float_or_none(row[2]))
                for row in data.paises_balanza
                if len(row) >= 3 and str(row[1])
            ]
            if country_rows:
                conn.executemany(
                    """
                    INSERT INTO fact_country_balance
                    VALUES (?, ?, ?, ?, CURRENT_TIMESTAMP)
                    """,
                    country_rows,
                )
                conn.executemany(
                    """
                    INSERT INTO dashboard_country_balance (
                        period, country_name, iso3, balance_mdd
                    )
                    VALUES (?, ?, ?, ?)
                    """,
                    country_rows,
                )
                records_loaded += len(country_rows)

            component_rows = []
            for group_name, rows in (
                ("industrias_exportacion", data.industrias_exportacion),
                ("importaciones_uso", data.importaciones_uso),
                ("balanza_componentes", data.balanza_componentes),
            ):
                for idx, row in enumerate(rows):
                    if len(row) >= 2:
                        component_rows.append(
                            (group_name, str(row[0]), period or "actual", _float_or_none(row[1]), idx)
                        )
            if component_rows:
                conn.executemany(
                    """
                    INSERT INTO fact_trade_component
                    VALUES (?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    """,
                    component_rows,
                )
                records_loaded += len(component_rows)

            rec = data.recaudacion_aduanas or {}
            customs_period = str((rec.get("periodo_actual") or {}).get("etiqueta") or "actual")
            customs_source_rows = rec.get("aduanas") or _customs_from_aduanas_list(data.aduanas)
            dim_rows = []
            fact_rows = []
            compat_rows = []
            for item in customs_source_rows:
                cve = str(item.get("cve") or item.get("aduana") or "")
                if not cve:
                    continue
                dim_rows.append(
                    (
                        cve,
                        str(item.get("aduana") or cve),
                        str(item.get("tipo") or ""),
                        _float_or_none(item.get("lat")),
                        _float_or_none(item.get("lon")),
                    )
                )
                fact = (
                    customs_period,
                    cve,
                    _float_or_none(item.get("total")),
                    _float_or_none(item.get("iva")),
                    _float_or_none(item.get("igi")),
                    _float_or_none(item.get("dta")),
                    _float_or_none(item.get("ieps")),
                    _float_or_none(item.get("isan")),
                    _float_or_none(item.get("otros")),
                    _float_or_none(item.get("total_anio_previo_mismo_periodo")),
                    _float_or_none(item.get("variacion_nominal_pct")),
                )
                fact_rows.append(fact)
                compat_rows.append(
                    (
                        str(item.get("aduana") or cve),
                        cve,
                        str(item.get("tipo") or ""),
                        _float_or_none(item.get("lat")),
                        _float_or_none(item.get("lon")),
                        *_compat_fact_values(fact),
                    )
                )
            if dim_rows:
                conn.executemany(
                    """
                    INSERT INTO dim_customs (
                        cve, customs_name, customs_type, lat, lon
                    )
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    dim_rows,
                )
                records_loaded += len(dim_rows)
            if fact_rows:
                conn.executemany(
                    """
                    INSERT INTO fact_customs_revenue
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                    """,
                    fact_rows,
                )
                conn.executemany(
                    """
                    INSERT INTO dashboard_customs_revenue (
                        customs_name, cve, customs_type, lat, lon, total_mdp,
                        iva_mdp, igi_mdp, dta_mdp, ieps_mdp, isan_mdp,
                        otros_mdp, variation_pct, period
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """,
                    compat_rows,
                )
                records_loaded += len(fact_rows)

            conn.execute(
                """
                INSERT INTO dashboard_cache_payload VALUES
                    ('recaudacion_aduanas', ?, CURRENT_TIMESTAMP),
                    ('fuente', ?, CURRENT_TIMESTAMP)
                """,
                [json.dumps(data.recaudacion_aduanas or {}, ensure_ascii=False), json.dumps(data.fuente)],
            )

            conn.execute(
                """
                UPDATE warehouse_snapshot
                SET status = 'SUCCESS', finished_at = ?, records_loaded = ?, message = ?
                WHERE snapshot_id = ?
                """,
                [db.utc_now_naive(), records_loaded, "warehouse refreshed", snapshot_id],
            )
            conn.execute("COMMIT")
        except Exception as exc:
            conn.execute("ROLLBACK")
            conn.execute(
                """
                INSERT INTO warehouse_snapshot (
                    snapshot_id, source_code, source_file, source_mtime, fuente,
                    actualizado, completo, status, started_at, finished_at,
                    records_loaded, message
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, 'FAILED', ?, ?, 0, ?)
                """,
                [
                    snapshot_id,
                    source_code,
                    source_file,
                    source_mtime,
                    data.fuente,
                    data.actualizado,
                    data.completo,
                    started_at,
                    db.utc_now_naive(),
                    str(exc),
                ],
            )
            raise

    return {
        "status": "ok",
        "snapshot_id": snapshot_id,
        "records_loaded": records_loaded,
        "source_file": source_file,
        "db": str(db_path),
    }


def load_dashboard_from_warehouse(db_path: Path = DB_PATH) -> DatosComercio | None:
    """Read the latest dashboard state from DuckDB fact/dim tables."""
    if not db_path.exists():
        return None
    with db.connect(db_path, read_only=True) as conn:
        has_data = conn.execute("SELECT COUNT(*) FROM warehouse_snapshot WHERE status = 'SUCCESS'").fetchone()[0]
        if not has_data:
            return None

        snapshot = conn.execute(
            """
            SELECT fuente, actualizado, completo
            FROM warehouse_snapshot
            WHERE status = 'SUCCESS'
            ORDER BY finished_at DESC, snapshot_id DESC
            LIMIT 1
            """
        ).fetchone()
        fuente = snapshot[0] if snapshot else ""
        actualizado = snapshot[1] if snapshot and snapshot[1] else datetime.now()
        completo = bool(snapshot[2]) if snapshot else False

        series_rows = conn.execute(
            """
            SELECT s.series_id, s.nombre, s.flujo, s.grupo, f.date_month, f.value
            FROM dim_banxico_series s
            LEFT JOIN fact_banxico_series_monthly f USING (series_id)
            ORDER BY s.series_id, f.date_month
            """
        ).fetchall()
        series_map: dict[str, Serie] = {}
        for series_id, nombre, flujo, grupo, date_month, value in series_rows:
            if series_id not in series_map:
                series_map[series_id] = Serie(nombre, series_id, flujo or "", grupo or "", [], [])
            if date_month is not None:
                series_map[series_id].fechas.append(str(date_month))
                series_map[series_id].valores.append(None if value is None else float(value))

        annual_row = conn.execute(
            """
            SELECT period, exports_mdd, imports_mdd, balance_mdd
            FROM fact_dashboard_annual
            ORDER BY period DESC
            LIMIT 1
            """
        ).fetchone()
        anual = {}
        if annual_row:
            anual = {
                "anio": annual_row[0],
                "exportaciones": annual_row[1],
                "importaciones": annual_row[2],
                "balanza": annual_row[3],
            }

        accumulated_rows = conn.execute(
            """
            SELECT label, year, exports_mdd, imports_mdd, balance_mdd
            FROM fact_dashboard_accumulated
            ORDER BY year
            """
        ).fetchall()
        acumulado: dict[str, Any] = {}
        if accumulated_rows:
            acumulado["periodo"] = accumulated_rows[0][0]
            for _, year, exports, imports, balance in accumulated_rows:
                acumulado[str(year)] = {
                    "exportaciones": exports,
                    "importaciones": imports,
                    "balanza": balance,
                }

        country_rows = conn.execute(
            """
            SELECT country_name, iso3, balance_mdd
            FROM fact_country_balance
            ORDER BY balance_mdd DESC
            """
        ).fetchall()
        paises_balanza = [[name, iso3, balance] for name, iso3, balance in country_rows]

        components = _load_components(conn)

        customs_rows = conn.execute(
            """
            SELECT
                d.customs_name, d.cve, d.customs_type, d.lat, d.lon,
                f.total_mdp, f.iva_mdp, f.igi_mdp, f.dta_mdp, f.ieps_mdp,
                f.isan_mdp, f.otros_mdp, f.previous_total_mdp, f.variation_pct
            FROM fact_customs_revenue f
            JOIN dim_customs d USING (cve)
            ORDER BY f.total_mdp DESC
            """
        ).fetchall()
        aduanas = [[name, lat, lon, total] for name, _, _, lat, lon, total, *_ in customs_rows]

        recaudacion_aduanas = _load_payload(conn, "recaudacion_aduanas") or {}
        if customs_rows:
            recaudacion_aduanas = deepcopy(recaudacion_aduanas)
            recaudacion_aduanas["aduanas"] = [
                {
                    "aduana": row[0],
                    "cve": row[1],
                    "tipo": row[2],
                    "lat": row[3],
                    "lon": row[4],
                    "total": row[5],
                    "iva": row[6],
                    "igi": row[7],
                    "dta": row[8],
                    "ieps": row[9],
                    "isan": row[10],
                    "otros": row[11],
                    "total_anio_previo_mismo_periodo": row[12],
                    "variacion_nominal_pct": row[13],
                }
                for row in customs_rows
            ]

    return DatosComercio(
        fuente=fuente,
        actualizado=actualizado,
        completo=completo,
        series=list(series_map.values()),
        anual=anual,
        acumulado=acumulado,
        paises_balanza=paises_balanza,
        aduanas=aduanas,
        industrias_exportacion=components["industrias_exportacion"],
        importaciones_uso=components["importaciones_uso"],
        balanza_componentes=components["balanza_componentes"],
        recaudacion_aduanas=recaudacion_aduanas or None,
    )


def export_warehouse_to_json(path: Path = JSON_CACHE_PATH, db_path: Path = DB_PATH) -> dict[str, Any]:
    """Write the current SQL warehouse state to the legacy JSON cache/export file."""
    data = load_dashboard_from_warehouse(db_path)
    if not data:
        return {"status": "empty", "path": str(path)}
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(data.to_dict(), ensure_ascii=False, indent=2), encoding="utf-8")
    return {"status": "ok", "path": str(path)}


def customs_revenue_rows_sql(
    selected: list[str] | tuple[str, ...] | None = None,
    period: str | None = None,
    db_path: Path = DB_PATH,
) -> list[dict[str, Any]]:
    """Read customs revenue rows directly from the DuckDB warehouse."""
    if not db_path.exists():
        return []
    selected_values = [str(value) for value in (selected or []) if str(value)]
    with db.connect(db_path, read_only=True) as conn:
        active_period = period
        if not active_period:
            row = conn.execute(
                """
                SELECT period
                FROM fact_customs_revenue
                GROUP BY period
                ORDER BY MAX(updated_at) DESC, period DESC
                LIMIT 1
                """
            ).fetchone()
            active_period = row[0] if row else ""

        where = ["f.period = ?"]
        params: list[Any] = [active_period]
        if selected_values:
            placeholders = ", ".join("?" for _ in selected_values)
            where.append(f"f.cve IN ({placeholders})")
            params.extend(selected_values)

        rows = conn.execute(
            f"""
            SELECT
                d.customs_name, d.cve, d.customs_type, d.lat, d.lon,
                f.total_mdp, f.iva_mdp, f.igi_mdp, f.dta_mdp, f.ieps_mdp,
                f.isan_mdp, f.otros_mdp, f.variation_pct
            FROM fact_customs_revenue f
            JOIN dim_customs d USING (cve)
            WHERE {' AND '.join(where)}
            ORDER BY f.total_mdp DESC
            """,
            params,
        ).fetchall()

    return [
        {
            "aduana": row[0],
            "cve": row[1],
            "tipo": row[2],
            "lat": row[3],
            "lon": row[4],
            "total": row[5],
            "iva": row[6],
            "igi": row[7],
            "dta": row[8],
            "ieps": row[9],
            "isan": row[10],
            "otros": row[11],
            "variacion_nominal_pct": row[12],
        }
        for row in rows
    ]


def warehouse_status(db_path: Path = DB_PATH) -> dict[str, Any]:
    if not db_path.exists():
        return {"initialized": False, "db": str(db_path), "tables": {}}
    tables = {}
    with db.connect(db_path, read_only=True) as conn:
        for table in (
            "warehouse_snapshot",
            "dim_banxico_series",
            "fact_banxico_series_monthly",
            "fact_dashboard_annual",
            "fact_dashboard_accumulated",
            "fact_country_balance",
            "dim_customs",
            "fact_customs_revenue",
            "fact_trade_component",
        ):
            tables[table] = int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])
        latest = conn.execute(
            """
            SELECT status, source_code, source_file, finished_at, records_loaded, message
            FROM warehouse_snapshot
            ORDER BY started_at DESC, snapshot_id DESC
            LIMIT 1
            """
        ).fetchone()
    return {
        "initialized": True,
        "db": str(db_path),
        "tables": tables,
        "latest": {
            "status": latest[0],
            "source_code": latest[1],
            "source_file": latest[2],
            "finished_at": str(latest[3]) if latest[3] else "",
            "records_loaded": latest[4],
            "message": latest[5] or "",
        }
        if latest
        else None,
    }


def _load_components(conn) -> dict[str, list[list[Any]]]:
    rows = conn.execute(
        """
        SELECT component_group, component_name, value_mdd
        FROM fact_trade_component
        ORDER BY component_group, sort_order
        """
    ).fetchall()
    groups = {
        "industrias_exportacion": [],
        "importaciones_uso": [],
        "balanza_componentes": [],
    }
    for group, name, value in rows:
        if group in groups:
            groups[group].append([name, value])
    return groups


def _load_payload(conn, key: str) -> Any:
    row = conn.execute(
        "SELECT payload_json FROM dashboard_cache_payload WHERE cache_key = ?",
        [key],
    ).fetchone()
    if not row:
        return None
    try:
        return json.loads(row[0])
    except (TypeError, json.JSONDecodeError):
        return None


def _customs_from_aduanas_list(rows: list[list[Any]]) -> list[dict[str, Any]]:
    parsed = []
    for row in rows:
        if len(row) >= 4:
            parsed.append({"aduana": row[0], "lat": row[1], "lon": row[2], "total": row[3], "cve": row[0]})
    return parsed


def _float_or_none(value: Any) -> float | None:
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (TypeError, ValueError):
        return None


def _compat_fact_values(fact: tuple[Any, ...]) -> tuple[Any, ...]:
    period, _, total, iva, igi, dta, ieps, isan, otros, _, variation = fact
    return total, iva, igi, dta, ieps, isan, otros, variation, period
