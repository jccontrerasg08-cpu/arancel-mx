import plotly.graph_objects as go
from typing import List
from ..utils import COLORS, MAP_HOVER


COUNTRY_COORDS = {
    "USA": (39.8, -98.6), "CAN": (56.1, -106.3), "CHN": (35.9, 104.2),
    "TWN": (23.7, 121.0), "JPN": (36.2, 138.3), "MYS": (4.2, 102.0),
    "THA": (15.9, 101.0), "DEU": (51.2, 10.4), "ITA": (41.9, 12.6),
    "IND": (20.6, 78.9), "BRA": (-14.2, -51.9), "FRA": (46.2, 2.2),
    "PHL": (12.9, 122.8), "IDN": (-0.8, 113.9), "ESP": (40.5, -3.7),
    "DNK": (56.3, 9.5), "SGP": (1.35, 103.8), "CHL": (-35.7, -71.5),
    "CRI": (9.7, -84.2), "ISR": (31.0, 35.0), "PRT": (39.4, -8.2),
    "NZL": (-40.9, 174.9), "PER": (-9.2, -75.0), "GBR": (55.4, -3.4),
    "COL": (4.6, -74.3), "HKG": (22.3, 114.2), "PAN": (8.5, -80.8),
    "GTM": (15.8, -90.2), "SLV": (13.8, -88.9), "AUS": (-25.3, 133.8),
    "NLD": (52.1, 5.3), "BEL": (50.5, 4.5), "ARG": (-38.4, -63.6),
    "VEN": (6.4, -66.6),
}

def base_style(fig: go.Figure, height: int = 340, y_title: str = "MDD") -> go.Figure:
    fig.update_layout(
        margin=dict(t=10, r=14, b=40, l=60),
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Segoe UI", size=12, color=COLORS["tinta"]),
        legend=dict(orientation="h", y=-0.2),
        hoverlabel=MAP_HOVER,
    )
    fig.update_yaxes(gridcolor="#eef2f0", title=y_title)
    fig.update_xaxes(gridcolor="#f4f6f5")
    return fig


def balance_chart(balanza_componentes: List[List]) -> go.Figure:
    fig = go.Figure(go.Bar(
        x=[d[0] for d in balanza_componentes],
        y=[d[1] for d in balanza_componentes],
        marker_color=[COLORS["verde2"] if d[1] >= 0 else COLORS["rojo"] for d in balanza_componentes],
        hovertemplate="%{x}: $%{y:,.0f} MDD<extra></extra>",
    ))
    return base_style(fig)


def ranking_chart(paises_balanza: List[List], positive: bool = True) -> go.Figure:
    sorted_data = sorted(
        [d for d in paises_balanza if (d[2] > 0) == positive],
        key=lambda d: d[2],
        reverse=positive,
    )[:10]
    sorted_data.reverse()
    fig = go.Figure(go.Bar(
        orientation="h",
        x=[d[2] for d in sorted_data],
        y=[d[0] for d in sorted_data],
        marker_color=COLORS["verde2"] if positive else COLORS["rojo"],
        hovertemplate="%{y}: $%{x:,.0f} MDD<extra></extra>",
    ))
    fig.update_layout(
        margin=dict(t=10, r=14, b=40, l=120),
        height=340,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="Segoe UI", size=12, color=COLORS["tinta"]),
    )
    fig.update_xaxes(title="MDD", gridcolor="#eef2f0")
    return fig


def pie_chart(data: List[List], colors: List[str], unit: str = "MDD") -> go.Figure:
    fig = go.Figure(go.Pie(
        labels=[d[0] for d in data],
        values=[d[1] for d in data],
        hole=.55,
        marker_colors=colors,
        textinfo="percent",
        hovertemplate=f"%{{label}}: $%{{value:,.0f}} {unit}<extra></extra>",
    ))
    fig.update_layout(
        height=340,
        margin=dict(t=10, r=10, b=10, l=10),
        paper_bgcolor="rgba(0,0,0,0)",
        legend=dict(orientation="h", y=-0.1),
    )
    return fig


def serie_chart(fechas: List[str], valores: List[float], forecast: dict | None = None) -> go.Figure:
    fig = go.Figure(go.Scatter(
        x=fechas,
        y=valores,
        name="Observado",
        mode="lines+markers",
        line=dict(color=COLORS["verde2"], width=2.5),
        marker=dict(size=7),
    ))
    if forecast and forecast.get("fechas"):
        fig.add_trace(go.Scatter(
            x=forecast["fechas"] + list(reversed(forecast["fechas"])),
            y=forecast["upper"] + list(reversed(forecast["lower"])),
            fill="toself",
            fillcolor="rgba(207, 164, 74, 0.16)",
            line=dict(color="rgba(207, 164, 74, 0)"),
            hoverinfo="skip",
            name="Rango tecnico",
        ))
        fig.add_trace(go.Scatter(
            x=forecast["fechas"],
            y=forecast["valores"],
            name="Pronostico",
            mode="lines+markers",
            line=dict(color=COLORS["oro"], width=2, dash="dash"),
            marker=dict(size=6),
        ))
    return base_style(fig, 460, "miles USD")
