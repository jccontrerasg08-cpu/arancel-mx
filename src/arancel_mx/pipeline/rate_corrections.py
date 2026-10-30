"""Rates SNICE still publishes after the instrument that set them expired.

``rate_corrections.json`` lists each one with the exact snapshot duty, the
duty the DOF text sets today, the day that duty took effect and the DOF
documents that support it.

A correction applies only while the snapshot still publishes exactly the
recorded duty. If SNICE updates or changes it, the correction is skipped and
reported as stale, so the registry never overrides new official data.
"""

from __future__ import annotations

from datetime import date
import hashlib
from importlib.resources import files
import json
from typing import Any, Iterable, Mapping, MutableMapping

from arancel_mx.domain.normalization import parse_duty

_RESOURCE = "rate_corrections.json"
_DUTIES = ("igi", "ige")


def _meaning(text: object) -> tuple[object, object]:
    kind, value, _ = parse_duty(text)
    return kind, value


def load_rate_corrections(raw: bytes | None = None) -> tuple[str, list[dict[str, Any]]]:
    """Return the registry's SHA-256 and its corrections."""
    data = raw if raw is not None else files("arancel_mx.sources").joinpath(_RESOURCE).read_bytes()
    corrections = json.loads(data)["corrections"]
    keys = [(item["code"], item["duty"]) for item in corrections]
    if len(set(keys)) != len(keys):
        raise ValueError("rate corrections repeat a code and duty")
    for item in corrections:
        if item["duty"] not in _DUTIES:
            raise ValueError(f"rate correction {item['code']} names unknown duty {item['duty']!r}")
        if _meaning(item["snapshot"]) == _meaning(item["corrected"]):
            raise ValueError(f"rate correction {item['code']} changes nothing")
        if not item["sources"]:
            raise ValueError(f"rate correction {item['code']} cites no source")
        date.fromisoformat(item["rate_effective_from"])
    return hashlib.sha256(data).hexdigest(), corrections


def apply_rate_corrections(
    rates: Iterable[MutableMapping[str, Any]],
    raw: bytes | None = None,
) -> dict[str, object]:
    """Correct matching rate rows in place and report what was applied or skipped."""
    sha256, corrections = load_rate_corrections(raw)
    by_code: dict[str, list[dict[str, Any]]] = {}
    for item in corrections:
        by_code.setdefault(item["code"], []).append(item)
    applied: list[dict[str, Any]] = []
    for row in rates:
        for item in by_code.get(str(row.get("code")), ()):
            duty = item["duty"]
            if _meaning(row.get(f"{duty}_text")) != _meaning(item["snapshot"]):
                continue
            kind, value, literal = parse_duty(item["corrected"])
            row[f"{duty}_text"] = literal
            row[f"{duty}_kind"] = kind
            row[f"{duty}_value"] = value
            applied.append(item)
    return {
        "registry_sha256": sha256,
        "applied": [
            {
                "code": item["code"],
                "duty": item["duty"],
                "snapshot": item["snapshot"],
                "corrected": item["corrected"],
                "rate_effective_from": item["rate_effective_from"],
                "sources": item["sources"],
            }
            for item in applied
        ],
        "stale": sorted(
            f"{item['code']}:{item['duty']}" for item in corrections if item not in applied
        ),
    }


def date_corrected_rates(
    rates: Iterable[MutableMapping[str, Any]], report: Mapping[str, Any]
) -> int:
    """Give a corrected row the start its correction documents when none was inferred."""
    starts = {
        str(item["code"]): date.fromisoformat(str(item["rate_effective_from"]))
        for item in report["applied"]
    }
    dated = 0
    for row in rates:
        start = starts.get(str(row.get("code")))
        if start is not None and row.get("rate_effective_from") is None:
            row["rate_effective_from"] = start
            dated += 1
    return dated
