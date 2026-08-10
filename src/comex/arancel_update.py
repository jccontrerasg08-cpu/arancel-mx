from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from tempfile import NamedTemporaryFile
from typing import Any

import requests

from .diputados_ligie import (
    LedgerDocument, LedgerLink, LedgerSnapshot, diff_ledgers, parse_ligie_ledger, route_changes,
)
from .arancel_release import build_arancel_release


DEFAULT_LEDGER_URL = "https://www.diputados.gob.mx/LeyesBiblio/ref/ligie_2022.htm"


@dataclass(frozen=True)
class UpdateConfig:
    ledger_url: str = DEFAULT_LEDGER_URL
    state_path: Path = Path("data/arancel_mx/update_state/ligie_ledger.json")
    report_path: Path | None = None
    timeout_s: float = 60.0
    user_agent: str = "arancel-mx/1.0 (+https://github.com/)"


@dataclass(frozen=True)
class UpdatePlan:
    status: str
    events: tuple[dict[str, str], ...]
    jobs: tuple[str, ...]
    snapshot: dict[str, Any]

    def to_dict(self) -> dict[str, Any]:
        return {"status": self.status, "events": list(self.events), "jobs": list(self.jobs), "snapshot": self.snapshot}


@dataclass(frozen=True)
class UpdateResult:
    status: str
    jobs: tuple[str, ...]
    events: tuple[dict[str, str], ...]

    def to_dict(self) -> dict[str, Any]:
        return {"status": self.status, "jobs": list(self.jobs), "events": list(self.events)}


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


class LocalJobRunner:
    """Run the selected discovery union and materialize one validated release."""
    def __init__(
        self,
        raw_root: Path | None = None,
        release_root: Path | None = None,
        embedded_root: Path | None = None,
    ) -> None:
        self.raw_root = raw_root or Path(os.getenv("ARANCEL_MX_RAW_ROOT", "data/raw/arancel_mx"))
        self.release_root = release_root or Path(os.getenv("ARANCEL_MX_RELEASE_ROOT", "data/releases"))
        self.embedded_root = embedded_root or Path("data/embedded/latest")
        self.selected: list[str] = []

    def run_domain(self, job: str, plan: UpdatePlan) -> None:
        if job == "dof_verification":
            self.selected.append(job)
            return
        if job.endswith("discovery") or job in {"diputados_capture", "legal_timeline", "rate_timeline", "nico_timeline", "national_notes", "correlations", "full_legal_reconciliation", "canonical_rebuild"}:
            self.selected.append(job)
            return
        raise ValueError(f"unsupported arancel update job: {job}")

    def publish(self, plan: UpdatePlan) -> None:
        if "canonical_rebuild" not in self.selected:
            raise ValueError("changed legal ledger did not select canonical_rebuild")
        release_date = date.today()
        version = release_date.strftime("%Y.%m.%d")
        suffix = str(plan.snapshot.get("page_sha256", ""))[:8]
        output = self.release_root / version
        if output.exists():
            output = self.release_root / f"{version}-{suffix}"
        source_dir = self.raw_root / version / suffix
        summary = build_arancel_release(
            source_dir,
            output,
            version,
            release_date,
            float(os.getenv("ARANCEL_MX_TIMEOUT_SECONDS", "60")),
        )
        if summary.get("validation_status") != "passed":
            raise ValueError("candidate release validation did not pass")
        database = output / "arancel_mx.duckdb"
        if database.stat().st_size > 95 * 1024 * 1024:
            raise ValueError("embedded DuckDB exceeds 95 MiB")
        self.embedded_root.mkdir(parents=True, exist_ok=True)
        for filename in ("arancel_mx.duckdb", "manifest.json"):
            source = output / filename
            temporary = self.embedded_root / f".{filename}.next"
            temporary.write_bytes(source.read_bytes())
            os.replace(temporary, self.embedded_root / filename)


def run_legal_update(config: UpdateConfig, client: Any | None = None, job_runner: Any | None = None) -> UpdateResult:
    plan = check_for_updates(config, client)
    if plan.status == "no_change":
        return UpdateResult("no_change", (), ())
    runner = job_runner or LocalJobRunner()
    for job in plan.jobs:
        runner.run_domain(job, plan)
    runner.publish(plan)
    _atomic_write(config.state_path, plan.snapshot)
    return UpdateResult("published", plan.jobs, plan.events)


def update_status(config: UpdateConfig) -> dict[str, Any]:
    if not config.state_path.exists():
        return {"status": "uninitialized", "state_path": str(config.state_path)}
    snapshot = json.loads(config.state_path.read_text(encoding="utf-8"))
    return {"status": "ready", "state_path": str(config.state_path), "snapshot": snapshot}
