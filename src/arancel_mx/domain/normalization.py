"""Canonical LIGIE normalization, identity, and release helpers."""

from __future__ import annotations

from collections.abc import Mapping
from collections import defaultdict
from datetime import date, datetime
from decimal import Decimal
import hashlib
import json
import re
from typing import Any, cast
import unicodedata

PUBLIC_COLUMNS = (
    "record_id",
    "record_version",
    "is_current",
    "code",
    "formatted_code",
    "level",
    "hs2",
    "hs4",
    "hs6",
    "fraccion8",
    "nico2",
    "nico10",
    "name",
    "description",
    "name_is_derived",
    "unit_code",
    "unit_name",
    "values_from_level",
    "igi_text",
    "igi_kind",
    "igi_value",
    "ige_text",
    "ige_kind",
    "ige_value",
    "ligie_version",
    "dataset_version",
    "schema_version",
    "record_hash",
    "validity_basis",
    "updated_at",
    "published_at",
    "classification_effective_from",
    "classification_effective_to",
    "rate_effective_from",
    "rate_effective_to",
    "effective_from",
    "effective_to",
    "observed_at",
    "retrieved_at",
    "primary_source_document_id",
    "primary_source_authority",
    "primary_source_url",
    "source_document_ids_json",
    "source_count",
)

_LEVEL_BY_LENGTH = {
    2: "hs2",
    4: "hs4",
    6: "hs6",
    8: "fraccion8",
    10: "nico10",
}

_SEMANTIC_HASH_FIELDS = (
    "level",
    "code",
    "hs2",
    "hs4",
    "hs6",
    "fraccion8",
    "nico2",
    "nico10",
    "name",
    "description",
    "unit_code",
    "unit_name",
    "values_from_level",
    "igi_text",
    "igi_kind",
    "igi_value",
    "ige_text",
    "ige_kind",
    "ige_value",
    "ligie_version",
    "validity_basis",
    "classification_effective_from",
    "classification_effective_to",
    "rate_effective_from",
    "rate_effective_to",
    "effective_from",
    "effective_to",
)


def _plain_number(value: Decimal) -> str:
    plain = format(value, "f")
    if "." in plain:
        plain = plain.rstrip("0").rstrip(".")
    return plain or "0"


def _json_value(value: Any) -> Any:
    if isinstance(value, Decimal):
        return _plain_number(value)
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Mapping):
        return {str(key): _json_value(item) for key, item in value.items()}
    if isinstance(value, (list, tuple)):
        return [_json_value(item) for item in value]
    return value


def canonical_json(value: Any) -> str:
    return json.dumps(
        _json_value(value),
        ensure_ascii=False,
        separators=(",", ":"),
    )


def normalize_code(value: object, component_width: int | None = None) -> str:
    if value is None or isinstance(value, bool):
        raise ValueError("Tariff code is required")
    if isinstance(value, float):
        if not value.is_integer():
            raise ValueError(f"Invalid numeric tariff code: {value!r}")
        text = str(int(value))
    else:
        text = str(value).strip()

    if not text:
        raise ValueError("Tariff code is required")
    if re.search(r"[^0-9.\s]", text):
        raise ValueError(f"Invalid tariff code: {value!r}")
    digits = re.sub(r"[.\s]", "", text)
    if not digits:
        raise ValueError(f"Invalid tariff code: {value!r}")

    if component_width is not None:
        if component_width < 1 or len(digits) > component_width:
            raise ValueError(f"Invalid component width for {value!r}")
        return digits.zfill(component_width)

    if len(digits) not in _LEVEL_BY_LENGTH:
        raise ValueError(f"Invalid tariff code length: {value!r}")
    return digits


def code_level(code: str) -> str:
    digits = normalize_code(code)
    return _LEVEL_BY_LENGTH[len(digits)]


def fold_text(value: object) -> str:
    """Accent-fold and collapse whitespace for catalog/HTML matching."""
    text = "" if value is None else " ".join(str(value).split())
    normalized = unicodedata.normalize("NFKD", text)
    return "".join(char for char in normalized if not unicodedata.combining(char))


def format_normalized_code(digits: str) -> str:
    if len(digits) == 2:
        return digits
    if len(digits) == 4:
        return f"{digits[:2]}.{digits[2:]}"
    if len(digits) == 6:
        return f"{digits[:4]}.{digits[4:]}"
    if len(digits) == 8:
        return f"{digits[:4]}.{digits[4:6]}.{digits[6:]}"
    return f"{digits[:4]}.{digits[4:6]}.{digits[6:8]} {digits[8:]}"


def format_code(code: str) -> str:
    return format_normalized_code(normalize_code(code))


def _truncate_name(value: str) -> str:
    if len(value) <= 120:
        return value.rstrip()
    boundary = value.rfind(" ", 0, 121)
    end = boundary if boundary > 0 else 120
    return value[:end].rstrip()


def derive_name(description: str) -> str:
    normalized = " ".join(str(description or "").split())
    if not normalized:
        raise ValueError("Official description is required")
    boundaries = [index for mark in ";.:" if (index := normalized.find(mark)) >= 0]
    candidate = normalized[: min(boundaries)] if boundaries else normalized
    candidate = candidate.rstrip(" \t\r\n;.:")
    if not candidate:
        candidate = normalized
    return _truncate_name(candidate)


def parse_duty(text: object) -> tuple[str | None, Decimal | None, str | None]:
    if text is None:
        return None, None, None
    literal = " ".join(str(text).split())
    if not literal:
        return None, None, None

    folded = literal.casefold().strip().rstrip(".")
    if folded in {"ex", "exento", "exenta", "exentos", "exentas"}:
        return "exento", Decimal("0"), literal
    if folded.startswith("prohibid"):
        return "prohibida", None, literal

    numeric = re.fullmatch(r"([+-]?\d+(?:[.,]\d+)?)\s*%?", literal)
    if numeric:
        return "ad_valorem", Decimal(numeric.group(1).replace(",", ".")), literal

    has_percent = "%" in literal
    has_specific_marker = bool(
        re.search(
            r"(?:[/+]\s*\w+|\b(?:usd|mxn|dls|d[oó]lar(?:es)?|kg|kilogramo|g|gramo|l|litro|m2|m²|m3|m³|pza|pieza|cabeza)\b)",
            folded,
        )
    )
    if has_percent and has_specific_marker:
        return "compuesta", None, literal
    if re.search(r"\d", literal) and has_specific_marker:
        return "especifica", None, literal
    return "desconocida", None, literal


def semantic_record_hash(row: Mapping[str, object]) -> str:
    payload = {field: row.get(field) for field in _SEMANTIC_HASH_FIELDS}
    return hashlib.sha256(canonical_json(payload).encode("utf-8")).hexdigest()


def record_id(row: Mapping[str, object]) -> str:
    identity = [
        row.get("level"),
        row.get("code"),
        row.get("ligie_version"),
        row.get("effective_from"),
        row.get("effective_to"),
        row.get("record_version"),
    ]
    return hashlib.sha256(canonical_json(identity).encode("utf-8")).hexdigest()


def _later_start(left: date | None, right: date | None) -> date | None:
    if left is None:
        return right
    if right is None:
        return left
    return max(left, right)


def _earlier_end(left: date | None, right: date | None) -> date | None:
    if left is None:
        return right
    if right is None:
        return left
    return min(left, right)


def _interval_intersection(
    left_start: date | None,
    left_end: date | None,
    right_start: date | None,
    right_end: date | None,
) -> tuple[date | None, date | None] | None:
    start = _later_start(left_start, right_start)
    end = _earlier_end(left_end, right_end)
    if start is not None and end is not None and start > end:
        return None
    return start, end


def _hierarchy(code: str) -> dict[str, str | None]:
    return {
        "hs2": code[:2],
        "hs4": code[:4] if len(code) >= 4 else None,
        "hs6": code[:6] if len(code) >= 6 else None,
        "fraccion8": code[:8] if len(code) >= 8 else None,
        "nico2": code[8:10] if len(code) == 10 else None,
        "nico10": code if len(code) == 10 else None,
    }


def _latest_date(*values: object) -> object:
    present: list[Any] = [value for value in values if value is not None]
    return max(present) if present else None


def consolidate_records(
    classifications: list[Mapping[str, object]],
    rates: list[Mapping[str, object]],
    release: Mapping[str, object],
) -> list[dict[str, object]]:
    """Intersect classification and rate revisions into deterministic public records."""
    effective_as_of = release.get("effective_as_of")
    if not isinstance(effective_as_of, date):
        raise ValueError("release.effective_as_of must be a date")

    rates_by_parent: dict[tuple[str, object], list[Mapping[str, object]]] = defaultdict(list)
    for rate_row in rates:
        rates_by_parent[(normalize_code(rate_row["code"]), rate_row.get("ligie_version"))].append(
            rate_row
        )
    fractions_by_code: dict[tuple[str, object], list[Mapping[str, object]]] = defaultdict(list)
    for classification in classifications:
        if classification.get("level") == "fraccion8":
            fractions_by_code[
                (normalize_code(classification["code"]), classification.get("ligie_version"))
            ].append(classification)

    candidates: list[dict[str, object]] = []
    for classification in classifications:
        code = normalize_code(classification["code"])
        level = str(classification.get("level") or code_level(code))
        if level != code_level(code):
            raise ValueError(f"Level {level!r} does not match code {code!r}")

        applicability: list[
            tuple[Mapping[str, object] | None, Mapping[str, object] | None]
        ]
        if level in {"fraccion8", "nico10"}:
            parent_code = code[:8]
            key = (parent_code, classification.get("ligie_version"))
            applicable_rates = rates_by_parent.get(key, [])
            if level == "nico10":
                parent_classifications = fractions_by_code.get(key, [])
                applicability = [
                    (rate, parent)
                    for rate in applicable_rates
                    for parent in parent_classifications
                ]
                if not applicable_rates:
                    raise ValueError(
                        f"NICO {code} has no matching tariff rate for publication"
                    )
                if not parent_classifications:
                    raise ValueError(
                        f"NICO {code} has no contemporaneous parent fraction for publication"
                    )
                if not applicability:
                    raise ValueError(
                        f"NICO {code} has no publishable rate/parent intersection"
                    )
            else:
                if not applicable_rates:
                    raise ValueError(
                        f"tariff fraction {code} has no matching tariff rate for publication"
                    )
                applicability = [(rate, None) for rate in applicable_rates]
        else:
            applicability = [(None, None)]

        produced = 0
        for rate, parent_classification in applicability:
            classification_start = cast(
                date | None, classification.get("classification_effective_from")
            )
            classification_end = cast(
                date | None, classification.get("classification_effective_to")
            )
            effective: tuple[date | None, date | None] | None
            if rate is None:
                effective = (classification_start, classification_end)
            else:
                effective = _interval_intersection(
                    classification_start,
                    classification_end,
                    rate.get("rate_effective_from"),
                    rate.get("rate_effective_to"),
                )
            if effective is None:
                continue
            if parent_classification is not None:
                effective = _interval_intersection(
                    effective[0],
                    effective[1],
                    parent_classification.get("classification_effective_from"),
                    parent_classification.get("classification_effective_to"),
                )
                if effective is None:
                    continue

            effective_from, effective_to = effective
            source_ids = sorted(
                {
                    str(source_id)
                    for source_id in (
                        classification.get("source_document_id"),
                        parent_classification.get("source_document_id")
                        if parent_classification
                        else None,
                        rate.get("source_document_id") if rate else None,
                    )
                    if source_id
                }
            )
            description = " ".join(str(classification["description"]).split())
            if level == "nico10":
                primary_source_document_id = classification.get("source_document_id")
            elif rate is not None:
                primary_source_document_id = rate.get("source_document_id")
            else:
                primary_source_document_id = classification.get("source_document_id")
            row: dict[str, object] = {
                "record_id": None,
                "record_version": None,
                "is_current": (
                    (effective_from is None or effective_from <= effective_as_of)
                    and (effective_to is None or effective_to >= effective_as_of)
                    and (
                        effective_from is not None
                        or classification.get("validity_basis") == "observed_snapshot"
                    )
                ),
                "code": code,
                "formatted_code": format_code(code),
                "level": level,
                **_hierarchy(code),
                "name": derive_name(description),
                "description": description,
                "name_is_derived": True,
                "unit_code": rate.get("unit_code") if rate else None,
                "unit_name": rate.get("unit_name") if rate else None,
                "values_from_level": "fraccion8" if rate else None,
                "igi_text": rate.get("igi_text") if rate else None,
                "igi_kind": rate.get("igi_kind") if rate else None,
                "igi_value": rate.get("igi_value") if rate else None,
                "ige_text": rate.get("ige_text") if rate else None,
                "ige_kind": rate.get("ige_kind") if rate else None,
                "ige_value": rate.get("ige_value") if rate else None,
                "ligie_version": classification.get("ligie_version"),
                "dataset_version": release.get("dataset_version"),
                "schema_version": release.get("schema_version"),
                "record_hash": None,
                "validity_basis": classification.get("validity_basis"),
                "updated_at": _latest_date(
                    classification.get("updated_at"),
                    rate.get("updated_at") if rate else None,
                ),
                "published_at": _latest_date(
                    classification.get("published_at"),
                    rate.get("published_at") if rate else None,
                ),
                "classification_effective_from": classification_start,
                "classification_effective_to": classification_end,
                "rate_effective_from": rate.get("rate_effective_from") if rate else None,
                "rate_effective_to": rate.get("rate_effective_to") if rate else None,
                "effective_from": effective_from,
                "effective_to": effective_to,
                "observed_at": None,
                "retrieved_at": None,
                "primary_source_document_id": primary_source_document_id,
                "primary_source_authority": None,
                "primary_source_url": None,
                "source_document_ids_json": canonical_json(source_ids),
                "source_count": len(source_ids),
            }
            row["record_hash"] = semantic_record_hash(row)
            candidates.append(row)
            produced += 1

        if level in {"fraccion8", "nico10"} and produced == 0:
            raise ValueError(
                f"{level} {code} has no overlapping rate/parent interval for publication"
            )

    def sort_key(row: Mapping[str, object]) -> tuple[object, ...]:
        effective_from = row.get("effective_from")
        return (
            str(row.get("level")),
            str(row.get("code")),
            str(row.get("ligie_version")),
            effective_from is not None,
            effective_from or date.min,
            row.get("published_at") or date.min,
            str(row.get("record_hash")),
        )

    candidates.sort(key=sort_key)
    version_by_identity: dict[tuple[object, object, object], int] = {}
    for row in candidates:
        identity = (row["level"], row["code"], row["ligie_version"])
        version = version_by_identity.get(identity, 0) + 1
        version_by_identity[identity] = version
        row["record_version"] = version
        row["record_id"] = record_id(row)
    return candidates
