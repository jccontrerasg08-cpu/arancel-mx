from __future__ import annotations

import csv
import json
import re
import unicodedata
from collections import defaultdict
from datetime import datetime, timezone
from decimal import Decimal, InvalidOperation
from pathlib import Path
from typing import Iterable, Mapping

HEADER_ALIASES = {
    "year": {"anio", "ano", "year"}, "month": {"mes", "month"}, "flow": {"tipo", "flow", "flujo"},
    "tariff": {"tarifa", "fraccion", "fraccion_arancelaria", "fraccion_nico", "nico"},
    "unit": {"umed", "unidad_medida", "unit"}, "partner": {"pais_o_d", "pais_origen_destino", "pais", "country", "socio"},
    "customs": {"aduana", "customs"}, "transport": {"mtra", "medio_transporte", "transport"},
    "status": {"estatus_cifra", "estado_cifra", "status"}, "quantity": {"cantidad", "quantity"},
    "value_mxn": {"val_mnx", "val_mxn", "valor_mxn", "value_mxn"}, "value_usd": {"val_usd", "valor_usd", "value_usd"},
}

def _key(value: object) -> str:
    text = unicodedata.normalize("NFKD", str(value or "")).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"[^a-z0-9]+", "_", text.lower()).strip("_")

def _columns(fieldnames: Iterable[str | None]) -> dict[str, str]:
    normalized = {_key(name): str(name) for name in fieldnames if name}
    return {target: normalized[alias] for target, aliases in HEADER_ALIASES.items() for alias in aliases if alias in normalized}

def parse_decimal(value: object) -> Decimal | None:
    text = str(value or "").strip().replace(" ", "")
    if not text or text.upper() in {"NA", "N/D", "NULL", "-", "C"}: return None
    text = text.replace("$", "")
    if "," in text and "." in text:
        text = text.replace(",", "") if text.rfind(".") > text.rfind(",") else text.replace(".", "").replace(",", ".")
    elif "," in text:
        text = text.replace(",", ".") if text.count(",") == 1 and len(text.rsplit(",", 1)[1]) <= 2 else text.replace(",", "")
    try: return Decimal(text)
    except InvalidOperation: return None

def is_confidential(status: object) -> bool:
    text = _key(status)
    return text in {"c", "confidencial", "confidential", "reservado"} or "confiden" in text

def canonical_row(row: Mapping[str, object], columns: Mapping[str, str]) -> dict[str, object]:
    get = lambda name: str(row.get(columns[name], "")).strip() if name in columns else ""
    year, month = get("year"), get("month")
    period = f"{int(year):04d}-{int(month):02d}" if year.isdigit() and month.isdigit() else ""
    return {"period": period, "flow": get("flow") or "Sin especificar", "partner": get("partner") or "No especificado", "tariff": re.sub(r"\D", "", get("tariff")), "unit": get("unit"), "status": get("status"), "quantity": parse_decimal(row.get(columns.get("quantity", ""))), "value_mxn": parse_decimal(row.get(columns.get("value_mxn", ""))), "value_usd": parse_decimal(row.get(columns.get("value_usd", "")))}

def _public_amount(row: Mapping[str, object], measure: str) -> Decimal | None:
    return None if is_confidential(row.get("status")) else row.get(measure)  # type: ignore[return-value]

def _serialize(groups: Mapping[tuple[str, ...], dict[str, object]], labels: tuple[str, ...], value_key: str) -> list[dict[str, object]]:
    result=[]
    for key, state in groups.items():
        item=dict(zip(labels,key)); item[value_key]=float(state["value"]) if state["value"] is not None else None
        item.update(rows=state["rows"], confidential_rows=state["confidential_rows"], unavailable_value_rows=state["unavailable_value_rows"]); result.append(item)
    return sorted(result,key=lambda item: (str(item.get("period", "")), -(item[value_key] or -1)))

def build_snapshot(rows: Iterable[Mapping[str, object]], *, source_url: str = "", retrieved_at: str | None = None) -> dict[str, object]:
    rows=list(rows); monthly=defaultdict(lambda:{"value":Decimal(0),"rows":0,"confidential_rows":0,"unavailable_value_rows":0}); partners=defaultdict(lambda:{"value":Decimal(0),"rows":0,"confidential_rows":0,"unavailable_value_rows":0}); tariffs=defaultdict(lambda:{"value":Decimal(0),"rows":0,"confidential_rows":0,"unavailable_value_rows":0})
    periods=[]
    for row in rows:
        period, flow=str(row.get("period", "")),str(row.get("flow", "Sin especificar")); periods.append(period) if period else None
        tariff=str(row.get("tariff", "")); group=tariff[:4] if len(tariff)>=4 else (tariff or "Sin fracción")
        for bucket,key in ((monthly,(flow,period)),(partners,(flow,str(row.get("partner", "No especificado")))),(tariffs,(flow,group))):
            state=bucket[key]; state["rows"]+=1
            if is_confidential(row.get("status")): state["confidential_rows"]+=1; continue
            amount=_public_amount(row,"value_usd")
            if amount is None: state["unavailable_value_rows"]+=1
            else: state["value"]+=amount
    now=retrieved_at or datetime.now(timezone.utc).replace(microsecond=0).isoformat().replace("+00:00","Z")
    return {"schema_version":"1.0.0","status":"ready" if rows else "not_loaded","generated_at":now,"source":{"publisher":"INEGI","dataset":"Balanza Comercial de Mercancías de México (BCMM)","url":source_url},"coverage":{"period_start":min(periods) if periods else None,"period_end":max(periods) if periods else None,"input_rows":len(rows)},"measures":{"value_usd":"Valor en dólares estadounidenses corrientes, salvo la convención oficial del archivo fuente.","quantity":"Cantidad publicada con su unidad de medida (UMED)."},"dimensions":["flow","period","partner","tariff_group"],"observations":{"monthly":_serialize(monthly,("flow","period"),"value_usd"),"partners":sorted(_serialize(partners,("flow","partner"),"value_usd"),key=lambda x:(x["flow"],-(x["value_usd"] or -1))),"tariff_groups":sorted(_serialize(tariffs,("flow","tariff_group"),"value_usd"),key=lambda x:(x["flow"],-(x["value_usd"] or -1)))},"notes":["Los registros confidenciales se cuentan y nunca se imputan como cero.","Las agregaciones no sustituyen las cifras, metodología ni metadatos publicados por INEGI."]}

def read_bcmm_csv(path: Path) -> list[dict[str, object]]:
    raw=path.read_bytes()
    try:
        text=raw.decode("utf-8-sig")
    except UnicodeDecodeError:
        text=raw.decode("latin-1")
    dialect=csv.Sniffer().sniff(text[:4096], delimiters=",;\t|")
    reader=csv.DictReader(text.splitlines(), dialect=dialect); columns=_columns(reader.fieldnames or [])
    if not {"year","month","flow"}.issubset(columns): raise ValueError("BCMM file must include ANIO, MES and TIPO columns")
    return [canonical_row(row, columns) for row in reader]

def write_snapshot(inputs: Iterable[Path], output: Path, source_url: str = "") -> dict[str, object]:
    records=[record for input_path in inputs for record in read_bcmm_csv(input_path)]; snapshot=build_snapshot(records,source_url=source_url); output.parent.mkdir(parents=True,exist_ok=True); output.write_text(json.dumps(snapshot,ensure_ascii=False,indent=2)+"\n",encoding="utf-8"); return snapshot
