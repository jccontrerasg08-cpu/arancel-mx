from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

import requests

from arancel_mx.sources.diputados import (
    LedgerDocument, LedgerLink, LedgerSnapshot, diff_ledgers, parse_ligie_ledger, route_changes,
)


DEFAULT_LEDGER_URL = "https://www.diputados.gob.mx/LeyesBiblio/ref/ligie_2022.htm"


@dataclass(frozen=True)
class UpdateConfig:
    ledger_url: str = DEFAULT_LEDGER_URL
    state_path: Path = Path("data/arancel_mx/update_state/ligie_ledger.json")
    report_path: Path | None = None
    timeout_s: float = 60.0
    user_agent: str = "arancel-mx/1.0 (+https://github.com/jccontrerasg08-cpu/arancel-mx)"


@dataclass(frozen=True)
class UpdatePlan:
    status: str
    events: tuple[dict[str, str], ...]
    jobs: tuple[str, ...]
    snapshot: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {"status": self.status, "events": list(self.events), "jobs": list(self.jobs), "snapshot": self.snapshot}


def _snapshot_dict(snapshot: LedgerSnapshot) -> dict[str, Any]:
    def link(item: LedgerLink) -> dict[str, Any]:
        data = asdict(item)
        data["displayed_date"] = item.displayed_date.isoformat() if item.displayed_date else None
        return data
    return {
        "base_url": snapshot.base_url,
        "last_law_reform": snapshot.last_law_reform.isoformat(),
        "latest_tariff_modification": snapshot.latest_tariff_modification.isoformat(),
        "page_sha256": snapshot.page_sha256,
        "documents": [
            {"category": item.category, "ordinal": item.ordinal, "title": item.title,
             "displayed_date": item.displayed_date.isoformat() if item.displayed_date else None,
             "links": [link(value) for value in item.links]}
            for item in snapshot.documents
        ],
    }


def _snapshot_from_dict(data: dict[str, Any]) -> LedgerSnapshot:
    documents = []
    for item in data["documents"]:
        links = tuple(LedgerLink(**{**value, "displayed_date": date.fromisoformat(value["displayed_date"]) if value.get("displayed_date") else None}) for value in item["links"])
        documents.append(LedgerDocument(
            item["category"], item["ordinal"], item["title"],
            date.fromisoformat(item["displayed_date"]) if item.get("displayed_date") else None, links,
        ))
    return LedgerSnapshot(
        data["base_url"], date.fromisoformat(data["last_law_reform"]),
        date.fromisoformat(data["latest_tariff_modification"]), tuple(documents), data["page_sha256"],
    )


def _atomic_write(path: Path, payload: dict[str, Any]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with NamedTemporaryFile("w", encoding="utf-8", dir=path.parent, delete=False) as handle:
        json.dump(payload, handle, ensure_ascii=False, sort_keys=True, separators=(",", ":"))
        handle.write("\n")
        temporary = Path(handle.name)
    os.replace(temporary, path)


def check_for_updates(config: UpdateConfig, client: Any | None = None) -> UpdatePlan:
    session = client or requests.Session()
    if hasattr(session, "headers"):
        session.headers["User-Agent"] = config.user_agent
    response = session.get(config.ledger_url, timeout=config.timeout_s)
    response.raise_for_status()
    current = parse_ligie_ledger(response.text, config.ledger_url)
    previous = None
    if config.state_path.exists():
        previous = _snapshot_from_dict(json.loads(config.state_path.read_text(encoding="utf-8")))
    changes = diff_ledgers(previous, current)
    jobs = route_changes(changes)
    plan = UpdatePlan(
        "changed" if changes else "no_change",
        tuple({"event_type": item.event_type, "detail": item.detail} for item in changes),
        jobs, _snapshot_dict(current),
    )
    if config.report_path:
        _atomic_write(config.report_path, plan.to_dict())
    return plan
