"""Deterministic row-level comparison between two published dataset releases.

The comparison reads the current rows of the public ``arancel_mx`` view in two
DuckDB files and reports literal differences. It never normalizes text before
deciding that a value changed, never interprets a difference as a legal event,
and never fills a missing value: a change between two snapshots is evidence that
the published data differ, not proof of a decree or of its entry into force.
"""

from __future__ import annotations

from collections import Counter
from collections.abc import Iterable, Mapping
from typing import Any

DIFF_POLICY_VERSION = "release-diff-v1"

# Columns compared for every current row. Each maps to the event it produces.
COMPARED_FIELDS: tuple[tuple[str, str], ...] = (
    ("description", "description_changed"),
    ("igi_text", "igi_changed"),
    ("ige_text", "ige_changed"),
    ("unit_code", "unit_changed"),
    ("parent", "hierarchy_changed"),
)

EVENTS: tuple[str, ...] = ("row_added", "row_removed", *(event for _, event in COMPARED_FIELDS))

LEVELS: tuple[str, ...] = ("hs2", "hs4", "hs6", "fraccion8", "nico10")

CURRENT_ROWS_SQL = """
    SELECT code, level, description, igi_text, ige_text, unit_code,
           CASE level
             WHEN 'hs4' THEN hs2
             WHEN 'hs6' THEN hs4
             WHEN 'fraccion8' THEN hs6
             WHEN 'nico10' THEN fraccion8
             ELSE NULL
           END AS parent
    FROM arancel_mx
    WHERE is_current
    ORDER BY code
"""

_COLUMNS = ("code", "level", "description", "igi_text", "ige_text", "unit_code", "parent")

NOT_A_LEGAL_EVENT = (
    "Differences between two published snapshots. They are not legal events: "
    "check the DOF instrument and its entry into force before relying on a change."
)


def current_rows(connection: Any) -> dict[str, dict[str, object]]:
    """Return the current rows of one release keyed by code."""

    rows: dict[str, dict[str, object]] = {}
    for values in connection.execute(CURRENT_ROWS_SQL).fetchall():
        row = dict(zip(_COLUMNS, values, strict=True))
        code = str(row["code"])
        if code in rows:
            raise ValueError(f"release has more than one current row for {code}")
        rows[code] = row
    return rows


def _side(info: Mapping[str, object]) -> dict[str, object]:
    return {
        "dataset_version": info.get("dataset_version"),
        "release_verified": bool(info.get("release_verified")),
        "github_digest_state": info.get("github_digest_state"),
    }


def diff_rows(
    before: Mapping[str, Mapping[str, object]],
    after: Mapping[str, Mapping[str, object]],
    *,
    levels: Iterable[str] | None = None,
) -> tuple[dict[str, object], ...]:
    """Compare two code-keyed row maps and return one entry per event.

    A code can produce several events (for example a new description and a new
    IGI). Values are compared literally; ``None`` is kept as ``None``.
    """

    wanted = set(levels) if levels is not None else set(LEVELS)
    unknown = wanted - set(LEVELS)
    if unknown:
        raise ValueError(f"unknown level(s): {', '.join(sorted(unknown))}")
    changes: list[dict[str, object]] = []
    for code in sorted(set(before) | set(after)):
        old = before.get(code)
        new = after.get(code)
        level = str((new or old or {}).get("level"))
        if level not in wanted:
            continue
        if old is None:
            changes.append(_change(code, level, "row_added", None, new.get("description") if new else None))
            continue
        if new is None:
            changes.append(_change(code, level, "row_removed", old.get("description"), None))
            continue
        if old.get("level") != new.get("level"):
            raise ValueError(f"{code} changed level between releases")
        for field, event in COMPARED_FIELDS:
            if old.get(field) != new.get(field):
                changes.append(_change(code, level, event, old.get(field), new.get(field)))
    return tuple(changes)


def _change(code: str, level: str, event: str, old: object, new: object) -> dict[str, object]:
    return {"code": code, "level": level, "event": event, "old_value": old, "new_value": new}


def release_diff_report(
    before: Mapping[str, Mapping[str, object]],
    after: Mapping[str, Mapping[str, object]],
    *,
    from_info: Mapping[str, object],
    to_info: Mapping[str, object],
    levels: Iterable[str] | None = None,
) -> dict[str, object]:
    """Build the machine-readable comparison report for two releases."""

    changes = diff_rows(before, after, levels=levels)
    sides = {"from": _side(from_info), "to": _side(to_info)}
    verified = all(side["release_verified"] for side in sides.values())
    by_event = Counter(str(change["event"]) for change in changes)
    by_level = Counter(str(change["level"]) for change in changes)
    return {
        "policy_version": DIFF_POLICY_VERSION,
        "from": sides["from"],
        "to": sides["to"],
        "comparison_status": "verified_snapshots" if verified else "unverified_local_files",
        "levels": sorted(set(levels)) if levels is not None else list(LEVELS),
        "counts": {
            "rows_from": len(before),
            "rows_to": len(after),
            "changes": len(changes),
            "by_event": {event: by_event.get(event, 0) for event in EVENTS},
            "by_level": {level: by_level.get(level, 0) for level in LEVELS},
        },
        "note": NOT_A_LEGAL_EVENT,
        "changes": changes,
    }
