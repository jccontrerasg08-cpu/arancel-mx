"""Small dashboard filters shared by Dash and tests."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable

from src.models import DatosComercio


@dataclass(frozen=True)
class AnalysisContext:
    dimension: str
    values: tuple[str, ...] = ()
    period: str = ""
    metric: str = ""

    @classmethod
    def from_selection(
        cls,
        dimension: str,
        selected: Iterable[object] | None = None,
        period: object = "",
        metric: object = "",
    ) -> "AnalysisContext":
        return cls(
            dimension=dimension,
            values=tuple(str(value) for value in (selected or []) if str(value)),
            period=str(period or ""),
            metric=str(metric or ""),
        )


def country_balance_rows(data: DatosComercio, ctx: AnalysisContext) -> list[list]:
    selected = set(ctx.values)
    rows = [
        [row[0], row[1], float(row[2] or 0)]
        for row in data.paises_balanza
        if len(row) >= 3 and (not selected or str(row[1]) in selected)
    ]
    return sorted(rows, key=lambda row: row[2], reverse=True)


def customs_revenue_rows(data: DatosComercio, ctx: AnalysisContext) -> list[dict]:
    selected = set(ctx.values)
    rec = data.recaudacion_aduanas or {}
    rows = rec.get("aduanas") or [
        {"aduana": item[0], "lat": item[1], "lon": item[2], "total": item[3], "cve": item[0]}
        for item in data.aduanas
        if len(item) >= 4
    ]
    filtered = [row for row in rows if not selected or str(row.get("cve") or row.get("aduana")) in selected]
    return sorted(filtered, key=lambda row: row.get("total") or 0, reverse=True)
