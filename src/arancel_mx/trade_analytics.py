from __future__ import annotations

import csv
import json
import re
import unicodedata
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Iterable, Mapping, TypedDict

HEADER_ALIASES = {
    "year": {"anio", "ano", "year"}, "month": {"mes", "month"}, "flow": {"tipo", "flow", "flujo"},
    "tariff": {"tarifa", "fraccion", "fraccion_arancelaria", "fraccion_nico", "nico"},
    "unit": {"umed", "unidad_medida", "unit"}, "partner": {"pais_o_d", "pais_origen_destino", "pais", "country", "socio"},
    "customs": {"aduana", "customs"}, "transport": {"mtra", "medio_transporte", "transport"},
    "status": {"estatus_cifra", "estado_cifra", "status"}, "quantity": {"cantidad", "quantity"},
    "value_mxn": {"val_mnx", "val_mxn", "valor_mxn", "value_mxn"}, "value_usd": {"val_usd", "valor_usd", "value_usd"},
}


class Aggregate(TypedDict):
    value: Decimal
    rows: int
    confidential_rows: int
    unavailable_value_rows: int


def _key(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")


def _columns(fieldnames: Iterable[str | None]) -> dict[str, str]:
    normalized = {_key(name): str(name) for name in fieldnames if name}
    return {target: normalized[alias] for target, aliases in HEADER_ALIASES.items() for alias in aliases if alias in normalized}


def parse_decimal(value: object) -> Decimal | None:
    text = str(value or "").strip().replace(" ", "")
    if not text or text.upper() in {"NA", "N/D", "NULL", "-", "C"}:
        return None
    text = text.replace("$", "")
    if "," in text and "." in text:
        text = text.replace(",", "") if text.rfind(".") > text.rfind(",") else text.replace(".", "").replace(",", ".")
    elif "," in text:
        text = text.replace(",", ".") if text.count(",") == 1 and len(text.rsplit(",", 1)[1]) <= 2 else text.replace(",", "")
    try:
        return Decimal(text)
    except InvalidOperation:
        return None


def is_confidential(status: object) -> bool:
    text = _key(status)
    return text in {"c", "confidencial", "confidential", "reservado"} or "confiden" in text


def canonical_row(row: Mapping[str, object], columns: Mapping[str, str]) -> dict[str, object]:
    def get(name: str) -> str:
        return str(row.get(columns[name], "")).strip() if name in columns else ""

    year, month = get("year"), get("month")
    period = f"{int(year):04d}-{int(month):02d}" if year.isdigit() and month.isdigit() else ""
    return {
        "period": period, "flow": get("flow") or "Sin especificar", "partner": get("partner") or "No especificado",
        "tariff": re.sub(r"\D", "", get("tariff")), "unit": get("unit"), "status": get("status"),
        "quantity": parse_decimal(row.get(columns.get("quantity", ""))),
        "value_mxn": parse_decimal(row.get(columns.get("value_mxn", ""))),
        "value_usd": parse_decimal(row.get(columns.get("value_usd", ""))),
    }


def _new_aggregate() -> Aggregate:
    return {"value": Decimal(0), "rows": 0, "confidential_rows": 0, "unavailable_value_rows": 0}


def _serialize(groups: Mapping[tuple[str, ...], Aggregate], labels: tuple[str, ...], value_key: str) -> list[dict[str, object]]:
    result: list[dict[str, object]] = []
    for key, state in groups.items():
        item: dict[str, object] = dict(zip(labels, key))
        item[value_key] = float(state["value"])
        item["rows"] = state["rows"]
        item["confidential_rows"] = state["confidential_rows"]
        item["unavailable_value_rows"] = state["unavailable_value_rows"]
        result.append(item)

    def sort_key(item: dict[str, object]) -> tuple[str, float]:
        value = item.get(value_key)
        return str(item.get("period", "")), -(float(value) if isinstance(value, (int, float)) else -1.0)

    return sorted(result, key=sort_key)


def build_snapshot(rows: Iterable[Mapping[str, object]], *, source_url: str = "", retrieved_at: str | None = None) -> dict[str, object]:
    records = list(rows)
    monthly: defaultdict[tuple[str, ...], Aggregate] = defaultdict(_new_aggregate)
    partners: defaultdict[tuple[str, ...], Aggregate] = defaultdict(_new_aggregate)
    tariffs: defaultdict[tuple[str, ...], Aggregate] = defaultdict(_new_aggregate)
    periods: list[str] = []
    for row in records:
        period, flow = str(row.get("period", "")), str(row.get("flow", "Sin especificar"))
        if period:
            periods.append(period)
        tariff = str(row.get("tariff", ""))
        tariff_group = tariff[:4] if len(tariff) >= 4 else (tariff or "Sin fracción")
        for bucket, key in ((monthly, (flow, period)), (partners, (flow, str(row.get("partner", "No especificado")))), (tariffs, (flow, tariff_group))):
            state = bucket[key]
            state["rows"] += 1
            if is_confidential(row.get("status")):
                state["confidential_rows"] += 1
                continue
            amount = row.get("value_usd")
            if not isinstance(amount, Decimal):
                state["unavailable_value_rows"] += 1
            else:
                state["value"] += amount
    now = retrieved_at or datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00", "Z")
    partner_rows = _serialize(partners, ("flow", "partner"), "value_usd")
    tariff_rows = _serialize(tariffs, ("flow", "tariff_group"), "value_usd")
    return {
        "schema_version": "1.0.0", "status": "ready" if records else "not_loaded", "generated_at": now,
        "source": {"publisher": "INEGI", "dataset": "Balanza Comercial de Mercancías de México (BCMM)", "url": source_url},
        "coverage": {"period_start": min(periods) if periods else None, "period_end": max(periods) if periods else None, "input_rows": len(records)},
        "measures": {"value_usd": "Valor en dólares estadounidenses corrientes, salvo la convención oficial del archivo fuente.", "quantity": "Cantidad publicada con su unidad de medida (UMED)."},
        "dimensions": ["flow", "period", "partner", "tariff_group"],
        "observations": {
            "monthly": _serialize(monthly, ("flow", "period"), "value_usd"),
            "partners": sorted(partner_rows, key=lambda item: (str(item["flow"]), -float(item["value_usd"]))),
            "tariff_groups": sorted(tariff_rows, key=lambda item: (str(item["flow"]), -float(item["value_usd"]))),
        },
        "notes": ["Los registros confidenciales se cuentan y nunca se imputan como cero.", "Las agregaciones no sustituyen las cifras, metodología ni metadatos publicados por INEGI."],
    }


def read_bcmm_csv(path: Path) -> list[dict[str, object]]:
    raw = path.read_bytes()
    try:
        text = raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text = raw.decode("latin-1")
    dialect = csv.Sniffer().sniff(text[:4096], delimiters=",;\t|")
    reader = csv.DictReader(text.splitlines(), dialect=dialect)
    columns = _columns(reader.fieldnames or [])
    if not {"year", "month", "flow"}.issubset(columns):
        raise ValueError("BCMM file must include ANIO, MES and TIPO columns")
    return [canonical_row(row, columns) for row in reader]


def write_snapshot(inputs: Iterable[Path], output: Path, source_url: str = "") -> dict[str, object]:
    records = [record for input_path in inputs for record in read_bcmm_csv(input_path)]
    snapshot = build_snapshot(records, source_url=source_url)
    output.parent.mkdir(parents=True, exist_ok=True)
    output.write_text(json.dumps(snapshot, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    return snapshot
