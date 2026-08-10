"""Parsers for free global HS catalog sources."""

from __future__ import annotations

import csv
import json
from pathlib import Path
from typing import Iterable

import pandas as pd


CODE_KEYS = {"id", "code", "productcode", "product_code", "hs", "hscode", "hs_code", "value"}
DESC_KEYS = {"name", "description", "desc", "label", "text", "productdescription", "product_description"}


def _clean_code(value: object) -> str:
    text = str(value or "").strip()
    if not text or text.lower() == "nan":
        return ""
    digits = "".join(ch for ch in text if ch.isdigit())
    return digits if len(digits) in {2, 4, 6} else ""


def _clean_description(value: object) -> str:
    return " ".join(str(value or "").replace("\ufeff", " ").split())


def parse_hs_global_file(path: Path, source_url: str = "") -> list[dict]:
    """Parse JSON/CSV-like HS product catalogs into normalized HS rows."""
    suffix = path.suffix.lower()
    if suffix == ".json":
        return parse_hs_global_json(path.read_text(encoding="utf-8", errors="ignore"), source_url)
    if suffix in {".xls", ".xlsx"}:
        return parse_hs_global_excel(path, source_url)
    return parse_hs_global_delimited(path.read_text(encoding="utf-8", errors="ignore"), source_url)


def parse_hs_global_excel(path: Path, source_url: str = "") -> list[dict]:
    rows: list[dict] = []
    sheets = pd.read_excel(path, sheet_name=None, dtype=object)
    for df in sheets.values():
        df = df.dropna(how="all")
        if df.empty:
            continue
        header = [str(value or "").strip() for value in df.iloc[0].tolist()]
        has_header = any(_normalize_key(value) in CODE_KEYS | DESC_KEYS for value in header)
        if has_header:
            body = df.iloc[1:].copy()
            body.columns = header
            for raw in body.to_dict(orient="records"):
                rows.extend(_rows_from_mapping(raw, source_url))
        else:
            for raw in df.itertuples(index=False, name=None):
                if len(raw) < 2:
                    continue
                for idx, value in enumerate(raw[:-1]):
                    code = _clean_code(value)
                    desc = _clean_description(raw[idx + 1])
                    if code and desc:
                        rows.append(_row(code, desc, source_url))
                        break
    return _dedupe(rows)


def parse_hs_global_json(text: str, source_url: str = "") -> list[dict]:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError:
        return []
    return _dedupe(_rows_from_dicts(_walk_dicts(payload), source_url))


def parse_hs_global_delimited(text: str, source_url: str = "") -> list[dict]:
    sample = text[:4096]
    try:
        dialect = csv.Sniffer().sniff(sample, delimiters=",;\t|")
    except csv.Error:
        dialect = csv.excel
    rows: list[dict] = []
    reader = csv.DictReader(text.splitlines(), dialect=dialect)
    if reader.fieldnames:
        for raw in reader:
            rows.extend(_rows_from_mapping(raw, source_url))
    if rows:
        return _dedupe(rows)

    plain_reader = csv.reader(text.splitlines(), dialect=dialect)
    for raw in plain_reader:
        if len(raw) < 2:
            continue
        code = _clean_code(raw[0])
        desc = _clean_description(raw[1])
        if code and desc:
            rows.append(_row(code, desc, source_url))
    return _dedupe(rows)


def _walk_dicts(value: object) -> Iterable[dict]:
    if isinstance(value, dict):
        yield value
        for child in value.values():
            yield from _walk_dicts(child)
    elif isinstance(value, list):
        for child in value:
            yield from _walk_dicts(child)


def _rows_from_dicts(items: Iterable[dict], source_url: str) -> list[dict]:
    rows: list[dict] = []
    for item in items:
        rows.extend(_rows_from_mapping(item, source_url))
    return rows


def _rows_from_mapping(item: dict, source_url: str) -> list[dict]:
    normalized = {_normalize_key(k): v for k, v in item.items()}
    code = ""
    desc = ""
    for key, value in normalized.items():
        compact = key.replace("_", "")
        if not code and (key in CODE_KEYS or compact in CODE_KEYS):
            code = _clean_code(value)
        if not desc and (key in DESC_KEYS or compact in DESC_KEYS):
            desc = _clean_description(value)
    if not code or not desc:
        return []
    return [_row(code, desc, source_url)]


def _normalize_key(value: object) -> str:
    return str(value).lower().replace(" ", "").replace("-", "_")


def _row(code: str, description: str, source_url: str) -> dict:
    return {
        "code": code,
        "description": description,
        "level": len(code),
        "source_url": source_url,
    }


def _dedupe(rows: Iterable[dict]) -> list[dict]:
    found: dict[str, dict] = {}
    for row in rows:
        code = row.get("code", "")
        desc = row.get("description", "")
        if code and desc and code not in found:
            found[code] = row
    return list(found.values())
