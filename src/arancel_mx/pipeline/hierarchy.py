"""Fail-closed assembly of the public tariff classification hierarchy."""

from __future__ import annotations

from collections.abc import Mapping, Sequence

from arancel_mx.domain.normalization import code_level, normalize_code


_LEVEL_ORDER = {
    "hs2": 0,
    "hs4": 1,
    "hs6": 2,
    "fraccion8": 3,
    "nico10": 4,
}


def _canonical_row(
    row: Mapping[str, object], expected_levels: set[str]
) -> dict[str, object]:
    item = dict(row)
    code = normalize_code(item.get("code"))
    level = str(item.get("level") or "")
    if level not in expected_levels:
        raise ValueError(f"unexpected classification level: {level}")
    if code_level(code) != level:
        raise ValueError(f"classification level does not match code: {level}:{code}")
    if not str(item.get("ligie_version") or "").strip():
        raise ValueError(f"missing ligie_version for classification: {level}:{code}")
    if not str(item.get("description") or "").strip():
        raise ValueError(f"missing description for classification: {level}:{code}")
    item["code"] = code
    return item


def _deduplicate(rows: Sequence[dict[str, object]]) -> list[dict[str, object]]:
    unique: dict[tuple[str, str, str], dict[str, object]] = {}
    for row in rows:
        key = (
            str(row["level"]),
            str(row["code"]),
            str(row["ligie_version"]),
        )
        previous = unique.get(key)
        if previous is None:
            unique[key] = row
        elif previous != row:
            raise ValueError(
                "conflicting duplicate classification: " + ":".join(key)
            )
    return list(unique.values())


def assemble_classifications(
    hs_rows: Sequence[Mapping[str, object]],
    fraction_rows: Sequence[Mapping[str, object]],
    nico_rows: Sequence[Mapping[str, object]],
) -> list[dict[str, object]]:
    """Validate and combine HS, Mexican fraction, and NICO classifications."""
    hs = [
        _canonical_row(row, {"hs2", "hs4", "hs6"})
        for row in hs_rows
    ]
    fractions = [
        _canonical_row(row, {"fraccion8"})
        for row in fraction_rows
    ]
    nicos = [
        _canonical_row(row, {"nico10"})
        for row in nico_rows
    ]
    rows = _deduplicate([*hs, *fractions, *nicos])

    by_key = {
        (str(row["level"]), str(row["code"]), str(row["ligie_version"])): row
        for row in rows
    }
    for row in rows:
        level = str(row["level"])
        code = str(row["code"])
        version = str(row["ligie_version"])
        if level == "hs4" and ("hs2", code[:2], version) not in by_key:
            raise ValueError(f"missing HS2 parent: {code}:{version}")
        if level == "hs6" and ("hs4", code[:4], version) not in by_key:
            raise ValueError(f"missing HS4 parent: {code}:{version}")
        if level == "fraccion8" and ("hs6", code[:6], version) not in by_key:
            raise ValueError(f"missing HS6 parent: {code}:{version}")
        if level == "nico10" and ("fraccion8", code[:8], version) not in by_key:
            raise ValueError(f"missing fraction parent: {code}:{version}")

    fraction_keys = {
        (str(row["code"]), str(row["ligie_version"]))
        for row in rows
        if str(row["level"]) == "fraccion8"
    }
    nico_parent_keys = {
        (str(row["code"])[:8], str(row["ligie_version"]))
        for row in rows
        if str(row["level"]) == "nico10"
    }
    missing_nico_coverage = sorted(
        code for code, _version in fraction_keys - nico_parent_keys
    )
    if missing_nico_coverage:
        raise ValueError(
            "current tariff fractions missing NICO coverage: "
            + ", ".join(missing_nico_coverage)
        )

    return sorted(
        rows,
        key=lambda row: (
            _LEVEL_ORDER[str(row["level"])],
            str(row["code"]),
            str(row["ligie_version"]),
        ),
    )
