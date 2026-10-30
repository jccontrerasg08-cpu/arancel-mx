"""Typographic errata in the official snapshot, corrected from the DOF text.

SNICE's workbook is the source of every description. A handful of its entries
carry a typo that the DOF text does not have ("intesivo" for "intensivo").
``description_corrections.json`` lists each one with the exact snapshot text,
the corrected text and the DOF document that supports it.

A correction applies only while the snapshot still publishes exactly the
recorded text. If SNICE fixes or rewrites the entry, the correction is skipped
and reported as stale, so the registry never overrides new official text.
"""

from __future__ import annotations

import hashlib
from importlib.resources import files
import json
from typing import Any, Iterable, MutableMapping

_RESOURCE = "description_corrections.json"


def load_corrections(raw: bytes | None = None) -> tuple[str, list[dict[str, Any]]]:
    """Return the registry's SHA-256 and its corrections."""
    data = (
        raw
        if raw is not None
        else files("arancel_mx.sources").joinpath(_RESOURCE).read_bytes()
    )
    payload = json.loads(data)
    corrections = payload["corrections"]
    keys = [(item["level"], item["code"]) for item in corrections]
    if len(set(keys)) != len(keys):
        raise ValueError("description corrections repeat a level and code")
    for item in corrections:
        if item["snapshot"] == item["corrected"]:
            raise ValueError(f"description correction {item['code']} changes nothing")
    return hashlib.sha256(data).hexdigest(), corrections


def apply_description_corrections(
    classifications: Iterable[MutableMapping[str, Any]],
    raw: bytes | None = None,
) -> dict[str, object]:
    """Correct matching rows in place and report what was applied or skipped."""
    sha256, corrections = load_corrections(raw)
    by_key = {(item["level"], item["code"]): item for item in corrections}
    applied: list[str] = []
    for row in classifications:
        item = by_key.get((row.get("level"), row.get("code")))
        if item is not None and row.get("description") == item["snapshot"]:
            row["description"] = item["corrected"]
            applied.append(str(item["code"]))
    stale = sorted(
        str(item["code"]) for item in corrections if item["code"] not in applied
    )
    return {
        "registry_sha256": sha256,
        "applied": [
            {
                "code": item["code"],
                "snapshot": item["snapshot"],
                "corrected": item["corrected"],
                "source_url": item["source_url"],
                "sha256": item["sha256"],
            }
            for item in corrections
            if item["code"] in applied
        ],
        "stale": stale,
    }
