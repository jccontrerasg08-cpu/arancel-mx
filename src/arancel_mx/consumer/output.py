"""Deterministic human and machine serializers for consumer commands."""

from __future__ import annotations

import csv
from dataclasses import asdict, is_dataclass
from datetime import date, datetime
from io import StringIO
from pathlib import Path
from typing import Literal, Mapping, Sequence

import json

from arancel_mx.consumer.models import CompareRow, Ficha, ProvenanceRecord, SearchResult, SuggestHit, TariffRecord
from arancel_mx.consumer.query import SUGGEST_DISCLAIMER, format_code
from arancel_mx.consumer.wco_support import WcoCite, cite_chapter


CsvSchema = Literal["tariff", "search", "suggest", "provenance", "dataset", "ficha", "compare"]

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
_SEARCH_FIELDS = ("score", "match_kind", *_TARIFF_FIELDS, "scorer_version", "confidence")
_SUGGEST_FIELDS = (*_SEARCH_FIELDS, "disclaimer")
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
_FICHA_FIELDS = (
    "section_roman",
    "section_name",
    "code",
    "formatted_code",
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
)
_DATASET_FIELDS = ("dataset", "scope")
_COMPARE_FIELDS = (
    "code",
    "level",
    "field",
    "dataset",
    "other",
    "other_source",
    "match",
    "note",
)
_CSV_SCHEMA_FIELDS: dict[CsvSchema, tuple[str, ...]] = {
    "tariff": _TARIFF_FIELDS,
    "search": _SEARCH_FIELDS,
    "suggest": _SUGGEST_FIELDS,
    "provenance": _PROVENANCE_FIELDS,
    "dataset": _DATASET_FIELDS,
    "ficha": _FICHA_FIELDS,
    "compare": _COMPARE_FIELDS,
}


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


_LEVEL_LABELS = {
    "hs2": "Capítulo",
    "hs4": "Partida",
    "hs6": "Subpartida",
    "fraccion8": "Fracción",
    "nico10": "NICO",
}


def _hit_banner(index: int, total: int, result: SearchResult) -> str:
    return (
        f"--- {index}/{total}  {result.record.code}  score={result.score}  "
        f"confidence={result.confidence}  scorer={result.scorer_version} ---"
    )


def _ficha_row(ficha: Ficha) -> dict[str, object]:
    record = ficha.record
    section = ficha.section
    return {
        "section_roman": None if section is None else section.roman,
        "section_name": None if section is None else section.name,
        "code": record.code,
        "formatted_code": ficha.formatted_code,
        "level": record.level,
        "description": record.description,
        "unit_name": record.unit_name,
        "igi_text": record.igi_text,
        "igi_kind": record.igi_kind,
        "igi_value": record.igi_value,
        "ige_text": record.ige_text,
        "ige_kind": record.ige_kind,
        "ige_value": record.ige_value,
        "parent_code": record.parent_code,
        "dataset_version": record.dataset_version,
        "schema_version": record.schema_version,
    }


def _render_ficha_table(ficha: Ficha) -> str:
    record = ficha.record
    lines = [
        f"{'Código':<12}{ficha.formatted_code}",
        f"{'Nivel':<12}{_LEVEL_LABELS.get(record.level, record.level)}",
    ]
    if ficha.section is not None:
        lines.append(f"{'Sección':<12}{ficha.section.roman}  {ficha.section.name}")
    for node in ficha.hierarchy:
        label = _LEVEL_LABELS.get(node.level, node.level)
        lines.append(f"{label:<12}{format_code(node.code)}  {node.description}")
    if record.unit_name:
        lines.append(f"{'UM':<12}{record.unit_name}")
    if record.igi_text:
        lines.append(f"{'IGI':<12}{record.igi_text}")
    if record.ige_text:
        lines.append(f"{'IGE':<12}{record.ige_text}")
    if ficha.children:
        lines.append(f"{'Hijos':<12}{len(ficha.children)}")
        for child in ficha.children:
            label = _LEVEL_LABELS.get(child.level, child.level)
            lines.append(f"{label:<12}{format_code(child.code)}  {child.description}")
    return "\n".join(lines)


def _render_suggest_table(hits: Sequence[SuggestHit]) -> str:
    blocks = [hits[0].disclaimer]
    total = len(hits)
    for index, hit in enumerate(hits, start=1):
        record = hit.search.record
        blocks.append(_hit_banner(index, total, hit.search))
        blocks.append(_render_ficha_table(hit.ficha))
        if hit.national_notes:
            blocks.append("Notas nacionales")
            for note in hit.national_notes:
                blocks.append(f"{note.note_number}  {note.text}")
        else:
            blocks.append("Notas nacionales  (none)")
        cite = cite_chapter(record.hs2 or record.code[:2])
        blocks.append(f"WCO support  {cite.url}")
        if cite.local_path:
            blocks.append(f"WCO cache    {cite.local_path}")
    return "\n".join(blocks)


def _render_search_table(results: Sequence[SearchResult]) -> str:
    total = len(results)
    lines: list[str] = []
    for index, result in enumerate(results, start=1):
        record = result.record
        nivel = _LEVEL_LABELS.get(record.level, record.level)
        lines.append(_hit_banner(index, total, result))
        lines.append(f"{format_code(record.code)}  {nivel}  {record.description}")
    return "\n".join(lines)


def _tariff_row(record: TariffRecord) -> dict[str, object]:
    return {field: _plain(getattr(record, field)) for field in _TARIFF_FIELDS}


def _csv_row(value: object) -> tuple[tuple[str, ...], dict[str, object]]:
    if isinstance(value, SearchResult):
        row = _tariff_row(value.record)
        return (
            _SEARCH_FIELDS,
            {
                "score": value.score,
                "match_kind": value.match_kind,
                **row,
                "scorer_version": value.scorer_version,
                "confidence": value.confidence,
            },
        )
    if isinstance(value, SuggestHit):
        fields, row = _csv_row(value.search)
        return (*fields, "disclaimer"), {**row, "disclaimer": value.disclaimer}
    if isinstance(value, Ficha):
        return _FICHA_FIELDS, {key: _plain(item) for key, item in _ficha_row(value).items()}
    if isinstance(value, CompareRow):
        return _COMPARE_FIELDS, {field: _plain(getattr(value, field)) for field in _COMPARE_FIELDS}
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


def render_csv(value: object, *, empty_schema: CsvSchema | None = None) -> str:
    """Render stable CSV headers and LF line endings for supported public values."""

    items = _sequence(value)
    rows: list[dict[str, object]] = []
    if not items:
        if empty_schema is None:
            return ""
        fields = _CSV_SCHEMA_FIELDS[empty_schema]
    else:
        fields, first = _csv_row(items[0])
        rows.append(first)
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


def _render_wco_cite_table(cite: WcoCite) -> str:
    cache = cite.local_path if cite.local_path else "(none)"
    return "\n".join(
        (
            f"WCO support  {cite.url}",
            f"WCO cache    {cache}",
            cite.disclaimer,
        )
    )


def render_table(value: object, *, empty_csv_schema: CsvSchema | None = None) -> str:
    """Render a compact human table; this is intentionally not a machine contract."""

    if isinstance(value, WcoCite):
        return _render_wco_cite_table(value)
    if isinstance(value, Ficha):
        return _render_ficha_table(value)
    items = _sequence(value)
    if items and all(isinstance(item, SuggestHit) for item in items):
        return _render_suggest_table(tuple(items))
    if items and all(isinstance(item, SearchResult) for item in items):
        return _render_search_table(tuple(items))
    if not items:
        if empty_csv_schema == "suggest":
            return f"{SUGGEST_DISCLAIMER}\nNo results."
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


def render(
    value: object,
    *,
    format_name: str,
    empty_csv_schema: CsvSchema | None = None,
) -> str:
    """Dispatch one public value to the selected stable output format."""

    if format_name == "json":
        return render_json(value)
    if format_name == "csv":
        return render_csv(value, empty_schema=empty_csv_schema)
    if format_name == "table":
        return render_table(value, empty_csv_schema=empty_csv_schema)
    raise ValueError(f"unsupported output format: {format_name}")
