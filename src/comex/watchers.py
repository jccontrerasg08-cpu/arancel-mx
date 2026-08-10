"""Dry-run watchers for public VUCEM notifications and RFC portfolios."""

from __future__ import annotations

import json
import re
from datetime import UTC, datetime

from .cartera import load_cartera
from .paths import ALERTS_PATH, RAW_DIR, STATE_DIR, ensure_data_dirs


def _load_seen() -> set[str]:
    path = STATE_DIR / "vucem-notificaciones.json"
    if not path.exists():
        return set()
    try:
        return set(json.loads(path.read_text(encoding="utf-8")).get("seen", []))
    except (OSError, json.JSONDecodeError, TypeError):
        return set()


def _save_seen(seen: set[str]) -> None:
    path = STATE_DIR / "vucem-notificaciones.json"
    path.write_text(json.dumps({"seen": sorted(seen)}, ensure_ascii=False, indent=2), encoding="utf-8")


def _read_notifications_text() -> str:
    path = RAW_DIR / "vucem-notificaciones" / "notificaciones.html"
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8", errors="ignore")


def _snippet(text: str, rfc: str, radius: int = 260) -> str:
    idx = text.upper().find(rfc)
    if idx < 0:
        return ""
    raw = text[max(0, idx - radius): idx + len(rfc) + radius]
    return re.sub(r"\s+", " ", re.sub(r"<[^>]+>", " ", raw)).strip()


def run_watch(dry_run: bool = True) -> dict:
    """Match VUCEM public notifications against cartera RFCs and write JSONL alerts."""
    ensure_data_dirs()
    text = _read_notifications_text()
    clientes = load_cartera()
    seen = _load_seen()
    emitted = []

    if not text or not clientes:
        return {
            "dry_run": dry_run,
            "clientes": len(clientes),
            "alerts": 0,
            "message": "Sin notificaciones descargadas o cartera vacia.",
        }

    upper = text.upper()
    for cliente in clientes:
        rfc = cliente["rfc"]
        if rfc not in upper:
            continue
        alert_id = f"vucem-notificaciones:{rfc}"
        if alert_id in seen:
            continue
        alert = {
            "alert_id": alert_id,
            "source": "vucem-notificaciones",
            "rfc": rfc,
            "razon": cliente.get("razon", ""),
            "title": "Coincidencia en notificaciones publicas VUCEM",
            "body": _snippet(text, rfc),
            "dry_run": dry_run,
            "created_at": datetime.now(UTC).isoformat(timespec="seconds").replace("+00:00", "Z"),
        }
        emitted.append(alert)
        seen.add(alert_id)

    if emitted:
        with ALERTS_PATH.open("a", encoding="utf-8") as fh:
            for alert in emitted:
                fh.write(json.dumps(alert, ensure_ascii=False) + "\n")
        _save_seen(seen)

    return {"dry_run": dry_run, "clientes": len(clientes), "alerts": len(emitted), "path": str(ALERTS_PATH)}


def recent_alerts(limit: int = 20) -> list[dict]:
    ensure_data_dirs()
    if not ALERTS_PATH.exists():
        return []
    lines = ALERTS_PATH.read_text(encoding="utf-8", errors="ignore").splitlines()
    alerts = []
    for line in lines[-limit:]:
        try:
            alerts.append(json.loads(line))
        except json.JSONDecodeError:
            continue
    return list(reversed(alerts))
