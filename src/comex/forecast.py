"""Small monthly forecasting helpers for dashboard series."""

from __future__ import annotations

from datetime import datetime
from statistics import mean


def forecast_monthly(fechas: list[str], valores: list[float], horizon: int = 12, season: int = 12) -> dict:
    pairs = sorted(
        (str(date), float(value))
        for date, value in zip(fechas or [], valores or [])
        if date and value is not None
    )
    if len(pairs) < 2:
        return {"fechas": [], "valores": [], "lower": [], "upper": [], "method": "none", "note": "Sin datos suficientes."}

    dates = [date for date, _ in pairs]
    values = [value for _, value in pairs]
    horizon = max(1, min(int(horizon or 12), 24))
    method = _method(len(values), season)
    spread = _spread(values, season)
    forecast = []

    for step in range(1, horizon + 1):
        if len(values) >= 2 * season:
            idx = (step - 1) % season
            base = values[-season + idx]
            previous = values[-2 * season + idx]
            point = base + (base - previous) * ((step - 1) // season + 1)
        elif len(values) >= season:
            idx = (step - 1) % season
            trend = (values[-1] - values[-season]) / season
            point = values[-season + idx] + trend * step
        else:
            trend = mean([b - a for a, b in zip(values, values[1:])])
            point = values[-1] + trend * step
        forecast.append(point)

    future_dates = _future_months(dates[-1], horizon)
    return {
        "fechas": future_dates,
        "valores": [round(value, 4) for value in forecast],
        "lower": [round(value - spread, 4) for value in forecast],
        "upper": [round(value + spread, 4) for value in forecast],
        "method": method,
        "note": "Pronostico tecnico local; valida con fuente oficial antes de decidir.",
    }


def forecast_text(forecast: dict) -> str:
    if not forecast.get("fechas"):
        return "Pronostico no disponible."
    return f"Pronostico local {len(forecast['fechas'])} meses ({forecast.get('method')}). {forecast.get('note')}"


def _method(n: int, season: int) -> str:
    if n >= 2 * season:
        return "estacional interanual"
    if n >= season:
        return "estacional con deriva"
    return "tendencia lineal corta"


def _spread(values: list[float], season: int) -> float:
    if len(values) > season:
        residuals = [abs(values[i] - values[i - season]) for i in range(season, len(values))]
    else:
        residuals = [abs(b - a) for a, b in zip(values, values[1:])]
    return max(mean(residuals) if residuals else 0, abs(values[-1]) * 0.02)


def _future_months(last_date: str, horizon: int) -> list[str]:
    try:
        dt = datetime.fromisoformat(str(last_date)[:10])
    except ValueError:
        return [f"+{step}m" for step in range(1, horizon + 1)]
    months = []
    year = dt.year
    month = dt.month
    for _ in range(horizon):
        month += 1
        if month > 12:
            year += 1
            month = 1
        months.append(f"{year:04d}-{month:02d}-01")
    return months
