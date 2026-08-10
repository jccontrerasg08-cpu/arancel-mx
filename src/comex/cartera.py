"""RFC portfolio used by public watchers."""

from __future__ import annotations

import json
import re
from pathlib import Path

from .paths import CARTERA_PATH, ensure_data_dirs


RFC_RE = re.compile(r"^[A-Z&]{3,4}\d{6}[A-Z0-9]{3}$")


def normalize_rfc(value: str) -> str:
    return re.sub(r"[^A-Z0-9&]", "", (value or "").upper())


def load_cartera(path: Path = CARTERA_PATH) -> list[dict]:
    ensure_data_dirs()
    if not path.exists():
        return []
    try:
        raw = json.loads(path.read_text(encoding="utf-8"))
        return list(raw.get("clientes", []))
    except (OSError, json.JSONDecodeError, TypeError):
        return []


def save_cartera(items: list[dict], path: Path = CARTERA_PATH) -> None:
    ensure_data_dirs()
    payload = {"clientes": sorted(items, key=lambda item: item["rfc"])}
    path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


def add_cliente(rfc: str, razon: str, email: str | None = None, whatsapp: str | None = None) -> dict:
    normalized = normalize_rfc(rfc)
    if not RFC_RE.match(normalized):
        raise ValueError(f"RFC invalido: {rfc}")
    items = [item for item in load_cartera() if item.get("rfc") != normalized]
    cliente = {
        "rfc": normalized,
        "razon": razon.strip() or normalized,
        "email": email or "",
        "whatsapp": whatsapp or "",
    }
    items.append(cliente)
    save_cartera(items)
    return cliente


def remove_cliente(rfc: str) -> bool:
    normalized = normalize_rfc(rfc)
    before = load_cartera()
    after = [item for item in before if item.get("rfc") != normalized]
    save_cartera(after)
    return len(after) != len(before)


def cartera_summary() -> dict:
    items = load_cartera()
    return {"path": str(CARTERA_PATH), "count": len(items), "clientes": items}
