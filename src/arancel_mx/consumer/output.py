"""Deterministic human and machine serializers for consumer commands."""

from __future__ import annotations

import csv
from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from io import StringIO
from pathlib import Path
from typing import Mapping, Sequence

import json

from arancel_mx.consumer.models import ProvenanceRecord, SearchResult, TariffRecord


_TARIFF_FIELDS = (
    "code",
    "level",
    "description",
    "unit_name",
    "igi_text",
    "igi_kind",
    "igi_value",
    "ige_text",
    "ige_kind",
    "ige_value",
    "parent_code",
    "dataset_version",
    "schema_version",
    "effective_from",
    "effective_to",
    "is_current",
)
_PROVENANCE_FIELDS = (
    "source_document_id",
    "role",
    "is_primary",
    "authority",
    "publication_venue",
    "title",
    "source_url",
    "sha256",
    "published_at",
    "effective_from",
    "effective_to",
)


def _plain(value: object) -> object:
    if is_dataclass(value):
        return {key: _plain(item) for key, item in asdict(value).items()}
    if isinstance(value, Mapping):
        return {str(key): _plain(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [_plain(item) for item in value]
    if isinstance(value, (date, datetime)):
        return value.isoformat()
    if isinstance(value, Path):
        return str(value)
    return value


def render_json(value: object) -> str:
    """Render UTF-8-safe JSON with deterministic object key order."""

    return json.dumps(
        _plain(value),
        ensure_ascii=False,
        sort_keys=True,
        separators=(",", ":"),
    )


def _tariff_row(record: TariffRecord) -> dict[str, object]:
    return {field: _plain(getattr(record, field)) for field in _TARIFF_FIELDS}


def _csv_row(value: object) -> tuple[tuple[str, ...], dict[str, object]]:
    if isinstance(value, SearchResult):
        row = _tariff_row(value.record)
        return (
            ("score", "match_kind", *_TARIFF_FIELDS),
            {"score": value.score, "match_kind": value.match_kind, **row},
        )
    if isinstance(value, TariffRecord):
        return _TARIFF_FIELDS, _tariff_row(value)
    if isinstance(value, ProvenanceRecord):
        return (
            _PROVENANCE_FIELDS,
            {field: _plain(getattr(value, field)) for field in _PROVENANCE_FIELDS},
        )
    if isinstance(value, Mapping):
        fields = tuple(sorted(str(key) for key in value))
        return fields, {field: _plain(value[field]) for field in fields}
    if is_dataclass(value):
        payload = _plain(value)
        assert isinstance(payload, dict)
        fields = tuple(sorted(payload))
        return fields, payload
    raise TypeError(f"Unsupported CSV output type: {type(value).__name__}")


def _sequence(value: object) -> tuple[object, ...]:
    if isinstance(value, tuple):
        return value
    if isinstance(value, list):
        return tuple(value)
    return (value,)


def render_csv(value: object) -> str:
    """Render stable CSV headers and LF line endings for supported public values."""

    items = _sequence(value)
    if not items:
        return ""
    fields, first = _csv_row(items[0])
    rows = [first]
    for item in items[1:]:
        item_fields, row = _csv_row(item)
        if item_fields != fields:
            raise TypeError("CSV output sequence contains incompatible public types")
        rows.append(row)

    buffer = StringIO(newline="")
    writer = csv.DictWriter(
        buffer,
        fieldnames=list(fields),
        lineterminator="\n",
        extrasaction="raise",
    )
    writer.writeheader()
    for row in rows:
        writer.writerow({key: "" if row[key] is None else row[key] for key in fields})
    return buffer.getvalue()


def render_table(value: object) -> str:
    """Render a compact human table; this is intentionally not a machine contract."""

    items = _sequence(value)
    if not items:
        return "No results."
    fields, first = _csv_row(items[0])
    rows = [first]
    for item in items[1:]:
        item_fields, row = _csv_row(item)
        if item_fields != fields:
            raise TypeError("table output sequence contains incompatible public types")
        rows.append(row)

    display_rows = [
        ["" if row[field] is None else str(row[field]) for field in fields]
        for row in rows
    ]
    widths = [
        max(len(field), *(len(row[index]) for row in display_rows))
        for index, field in enumerate(fields)
    ]
    header = "  ".join(field.ljust(widths[index]) for index, field in enumerate(fields))
    separator = "  ".join("-" * width for width in widths)
    body = [
        "  ".join(cell.ljust(widths[index]) for index, cell in enumerate(row))
        for row in display_rows
    ]
    return "\n".join([header, separator, *body])


def render_path(path: str | Path) -> str:
    """Return only the platform-native path string."""

    return str(Path(path))


def render(value: object, *, format_name: str) -> str:
    """Dispatch one public value to the selected stable output format."""

    if format_name == "json":
        return render_json(value)
    if format_name == "csv":
        return render_csv(value)
    if format_name == "table":
        return render_table(value)
    raise ValueError(f"unsupported output format: {format_name}")
