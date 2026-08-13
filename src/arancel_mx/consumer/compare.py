"""Compare official GitHub/CLI dataset rows with third-party classifier pages.

VUCEM sheets are informative. They are not legal identity. The ``dataset``
column is the verified ``data-*`` GitHub release as read by the CLI.
"""

from __future__ import annotations

from collections.abc import Callable
import re
from typing import Protocol

import requests

from arancel_mx.consumer.errors import InvalidCodeError
from arancel_mx.consumer.http import build_session
from arancel_mx.consumer.models import CompareRow, TariffRecord
from arancel_mx.consumer.query import normalize_code
from arancel_mx.sources.classifier_consistency import descriptions_consistent, normalize_duty
from arancel_mx.sources.vucem import VucemFractionSheet, fraction_sheet_url, parse_fraction_sheet

COMPARE_LEVELS = frozenset({"hs6", "fraccion8", "nico10"})
_NICO_TOKEN = re.compile(r"\d+")


class _DatasetView(Protocol):
    def lookup(self, code: str) -> TariffRecord: ...

    def children(self, code: str) -> tuple[TariffRecord, ...]: ...

    def parent(self, code: str) -> TariffRecord | None: ...


def _fetch_vucem(code8: str, *, timeout: float) -> VucemFractionSheet:
    url = fraction_sheet_url(code8)
    session = build_session()
    response = session.get(url, timeout=timeout)
    response.raise_for_status()
    return parse_fraction_sheet(response.text, base_url=url)


def _nico_code(fraccion8: str, token: str) -> str | None:
    digits = "".join(_NICO_TOKEN.findall(token))
    if len(digits) == 10:
        return digits
    if len(digits) == 2:
        return fraccion8 + digits
    return None


def _match_text(field: str, left: str | None, right: str | None) -> bool | None:
    if left is None or right is None:
        return None if left is None and right is None else False
    if field == "description":
        return descriptions_consistent(left, right)
    if field in {"igi", "ige"}:
        return normalize_duty(left) == normalize_duty(right)
    return left == right


def _row(
    code: str,
    level: str,
    field: str,
    dataset: str | None,
    other: str | None,
    *,
    other_source: str = "vucem",
    note: str = "",
    match: bool | None | object = ...,
) -> CompareRow:
    resolved = _match_text(field, dataset, other) if match is ... else match
    return CompareRow(
        code=code,
        level=level,
        field=field,
        dataset=dataset,
        other=other,
        other_source=other_source,
        match=resolved,
        note=note,
    )


def _sheet_failure(code: str, level: str, sheet: object) -> CompareRow:
    if sheet is None:
        return _row(
            code,
            level,
            "present",
            "yes",
            None,
            match=None,
            note="offline; third-party not fetched",
        )
    return _row(
        code,
        level,
        "present",
        "yes",
        None,
        match=False,
        note=str(sheet),
    )


def _compare_fraction(record: TariffRecord, sheet: VucemFractionSheet) -> list[CompareRow]:
    return [
        _row(record.code, record.level, "description", record.description, sheet.description),
        _row(record.code, record.level, "igi", record.igi_text, sheet.import_duty),
        _row(record.code, record.level, "ige", record.ige_text, sheet.export_duty),
    ]


def _nico_from_sheet(sheet: VucemFractionSheet, nico10: str, fraccion8: str) -> tuple[str, str | None, str | None] | None:
    for token, description, igi, ige in sheet.nico_rows:
        mapped = _nico_code(fraccion8, token)
        if mapped == nico10:
            return description, igi, ige
    return None


def _compare_nico(record: TariffRecord, sheet: VucemFractionSheet, fraccion8: str) -> list[CompareRow]:
    found = _nico_from_sheet(sheet, record.code, fraccion8)
    if found is None:
        return [
            _row(
                record.code,
                record.level,
                "present",
                "yes",
                None,
                match=False,
                note="vucem sheet has no matching NICO row",
            )
        ]
    description, igi, ige = found
    return [
        _row(record.code, record.level, "description", record.description, description),
        _row(record.code, record.level, "igi", record.igi_text, igi),
        _row(record.code, record.level, "ige", record.ige_text, ige),
    ]


def _load_sheet(
    code8: str,
    cache: dict[str, VucemFractionSheet | BaseException | None],
    *,
    fetch: bool,
    timeout: float,
    get_sheet: Callable[[str], VucemFractionSheet] | None,
) -> VucemFractionSheet | BaseException | None:
    if not fetch:
        return None
    if code8 in cache:
        return cache[code8]
    loader = get_sheet or (lambda code: _fetch_vucem(code, timeout=timeout))
    try:
        cache[code8] = loader(code8)
    except (OSError, ValueError, requests.RequestException) as exc:
        cache[code8] = exc
    return cache[code8]


def compare_code(
    dataset: _DatasetView,
    code: str,
    *,
    fetch: bool = True,
    timeout: float = 30,
    get_sheet: Callable[[str], VucemFractionSheet] | None = None,
) -> tuple[CompareRow, ...]:
    """Compare one HS6, MX8, or NICO code against VUCEM HTML sheets."""

    record = dataset.lookup(normalize_code(code))
    if record.level not in COMPARE_LEVELS:
        raise InvalidCodeError(
            f"compare requires hs6, fraccion8, or nico10: {record.code}"
        )
    cache: dict[str, VucemFractionSheet | BaseException | None] = {}
    rows: list[CompareRow] = []

    def sheet_for(code8: str) -> VucemFractionSheet | BaseException | None:
        return _load_sheet(
            code8, cache, fetch=fetch, timeout=timeout, get_sheet=get_sheet
        )

    if record.level == "hs6":
        rows.append(
            _row(
                record.code,
                record.level,
                "description",
                record.description,
                None,
                match=None,
                note="vucem has no hs6 page; children compared below",
            )
        )
        for child in dataset.children(record.code):
            rows.extend(_fraction_and_nicos(dataset, child, sheet_for(child.code)))
        return tuple(rows)
    if record.level == "fraccion8":
        return tuple(_fraction_and_nicos(dataset, record, sheet_for(record.code)))
    parent = dataset.parent(record.code)
    if parent is None or parent.level != "fraccion8":
        raise InvalidCodeError(f"nico10 compare needs a fraccion8 parent: {record.code}")
    loaded = sheet_for(parent.code)
    if not isinstance(loaded, VucemFractionSheet):
        return (_sheet_failure(record.code, record.level, loaded),)
    return tuple(_compare_nico(record, loaded, parent.code))


def _fraction_and_nicos(
    dataset: _DatasetView,
    record: TariffRecord,
    loaded: VucemFractionSheet | BaseException | None,
) -> list[CompareRow]:
    if not isinstance(loaded, VucemFractionSheet):
        return [_sheet_failure(record.code, record.level, loaded)]
    rows = _compare_fraction(record, loaded)
    for nico in dataset.children(record.code):
        rows.extend(_compare_nico(nico, loaded, record.code))
    return rows
