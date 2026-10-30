"""Rate validity (vigencia) for each fraction from the LIGIE 2022 instruments.

The official snapshot from SNICE gives each fraction's current IGI/IGE but not
since when it applies. ``legal_instruments.json`` holds the Tarifa rows of the
base LIGIE 2022 and of every later DOF instrument that set general rates, with
their entry into force and, when temporary, their last day of validity.

For a fraction, the rate in force on a date is the row of the most recent
instrument in force that day. The rate's validity starts where the final
unbroken run of the same IGI/IGE begins: the entry into force of the instrument
that set it, or the day after a temporary rate ended and the earlier rate came
back. It ends on the governing instrument's last day, if it has one.

The answer is only given when it is certain. A fraction gets no dates when the
instruments disagree with the snapshot (reported as a discrepancy) or when an
instrument the registry does not model (staged rates, exemption decrees)
mentions it and the base text would otherwise govern.
"""

from __future__ import annotations

from collections import defaultdict
from dataclasses import dataclass
from datetime import date, timedelta
from decimal import Decimal
import hashlib
from importlib.resources import files
import json
from typing import Any, Iterable, Mapping, MutableMapping

from arancel_mx.domain.normalization import parse_duty

_RESOURCE = "legal_instruments.json"

Duty = tuple[str | None, Decimal | None]


@dataclass(frozen=True)
class Instrument:
    id: str
    kind: str
    title: str
    dof_date: date
    entry_into_force: date
    validity_end: date | None
    source_url: str
    sha256: str


@dataclass(frozen=True)
class RateValidity:
    rate_effective_from: date
    rate_effective_to: date | None
    instrument_id: str


@dataclass(frozen=True)
class Registry:
    version: str
    sha256: str
    instruments: tuple[Instrument, ...]
    rows: Mapping[str, tuple[tuple[Instrument, Duty, Duty], ...]]
    unmodeled: Mapping[str, tuple[str, ...]]


def _duty(text: object) -> Duty:
    kind, value, _ = parse_duty(text)
    return kind, value


def load_registry(raw: bytes | None = None) -> Registry:
    """Load the packaged registry, or ``raw`` bytes with the same format."""
    data = (
        raw
        if raw is not None
        else files("arancel_mx.sources").joinpath(_RESOURCE).read_bytes()
    )
    payload = json.loads(data)
    instruments: list[Instrument] = []
    rows: dict[str, list[tuple[Instrument, Duty, Duty]]] = defaultdict(list)
    for item in payload["instruments"]:
        end = item.get("validity_end")
        instrument = Instrument(
            id=item["id"],
            kind=item["kind"],
            title=item["title"],
            dof_date=date.fromisoformat(item["dof_date"]),
            entry_into_force=date.fromisoformat(item["entry_into_force"]),
            validity_end=date.fromisoformat(end) if end else None,
            source_url=item["source_url"],
            sha256=item["sha256"],
        )
        instruments.append(instrument)
        for code, igi, ige in item["rows"]:
            rows[code].append((instrument, _duty(igi), _duty(ige)))
    unmodeled: dict[str, list[str]] = defaultdict(list)
    for item in payload.get("unmodeled", []):
        for code in item["codes"]:
            unmodeled[code].append(item["id"])
    return Registry(
        version=payload["version"],
        sha256=hashlib.sha256(data).hexdigest(),
        instruments=tuple(instruments),
        rows={code: tuple(items) for code, items in rows.items()},
        unmodeled={code: tuple(ids) for code, ids in unmodeled.items()},
    )


def _in_force(instrument: Instrument, day: date) -> bool:
    return instrument.entry_into_force <= day and (
        instrument.validity_end is None or day <= instrument.validity_end
    )


def _governing(
    entries: Iterable[tuple[Instrument, Duty, Duty]], day: date
) -> tuple[Instrument, Duty, Duty] | None:
    active = [entry for entry in entries if _in_force(entry[0], day)]
    if not active:
        return None
    # The latest instrument in force wins; the base text is always the oldest.
    return max(
        active, key=lambda entry: (entry[0].entry_into_force, entry[0].kind != "base")
    )


def rate_validity(
    registry: Registry,
    code: str,
    igi_text: object,
    ige_text: object,
    as_of: date,
) -> RateValidity | str:
    """Return the validity of ``code``'s current rate, or why it is unknown."""
    entries = registry.rows.get(code, ())
    if not entries:
        return "not_in_instruments"
    current = _governing(entries, as_of)
    if current is None:
        return "no_instrument_in_force"
    instrument, igi, ige = current
    if (igi, ige) != (_duty(igi_text), _duty(ige_text)):
        return "snapshot_disagrees"
    if code in registry.unmodeled:
        if instrument.kind == "base":
            return "unmodeled_instrument"
        # An unmodeled instrument may have changed the rate before the governing
        # one, so the run is only known from the governing instrument's entry.
        return RateValidity(
            rate_effective_from=instrument.entry_into_force,
            rate_effective_to=instrument.validity_end,
            instrument_id=instrument.id,
        )

    changes = sorted(
        {entry[0].entry_into_force for entry in entries}
        | {
            entry[0].validity_end + timedelta(days=1)
            for entry in entries
            if entry[0].validity_end
        }
    )
    start = instrument.entry_into_force
    for day in reversed([day for day in changes if day <= as_of]):
        governing = _governing(entries, day)
        if governing is None or (governing[1], governing[2]) != (igi, ige):
            break
        start = day
    return RateValidity(
        rate_effective_from=start,
        rate_effective_to=instrument.validity_end,
        instrument_id=instrument.id,
    )


def assign_rate_validity(
    rates: Iterable[MutableMapping[str, Any]],
    as_of: date,
    registry: Registry | None = None,
) -> dict[str, object]:
    """Fill ``rate_effective_from``/``rate_effective_to`` in place; return a report."""
    registry = registry or load_registry()
    by_instrument: dict[str, int] = defaultdict(int)
    unknown: dict[str, int] = defaultdict(int)
    discrepancies: list[dict[str, object]] = []
    for row in rates:
        code = str(row["code"])
        result = rate_validity(
            registry, code, row.get("igi_text"), row.get("ige_text"), as_of
        )
        if isinstance(result, RateValidity):
            row["rate_effective_from"] = result.rate_effective_from
            row["rate_effective_to"] = result.rate_effective_to
            by_instrument[result.instrument_id] += 1
            continue
        unknown[result] += 1
        if result == "snapshot_disagrees":
            governing = _governing(registry.rows[code], as_of)
            if governing is None:  # rate_validity only disagrees with a governing row
                raise RuntimeError(f"no governing instrument for {code}")
            discrepancies.append(
                {
                    "code": code,
                    "snapshot": {
                        "igi": row.get("igi_text"),
                        "ige": row.get("ige_text"),
                    },
                    "instrument": governing[0].id,
                    "instrument_duties": {
                        "igi": _render(governing[1]),
                        "ige": _render(governing[2]),
                    },
                }
            )
    return {
        "registry_version": registry.version,
        "registry_sha256": registry.sha256,
        "as_of": as_of.isoformat(),
        "dated": dict(sorted(by_instrument.items())),
        "undated": dict(sorted(unknown.items())),
        "discrepancies": sorted(discrepancies, key=lambda item: str(item["code"])),
        "instruments": [
            {
                "id": item.id,
                "dof_date": item.dof_date.isoformat(),
                "entry_into_force": item.entry_into_force.isoformat(),
                "validity_end": item.validity_end.isoformat()
                if item.validity_end
                else None,
                "source_url": item.source_url,
                "sha256": item.sha256,
            }
            for item in registry.instruments
        ],
    }


def _render(duty: Duty) -> str | None:
    kind, value = duty
    if kind == "exento":
        return "Ex."
    if kind == "prohibida":
        return "Prohibida"
    return None if value is None else format(value.normalize(), "f")
