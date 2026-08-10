"""
Componentes UI para Dash
"""
from typing import Any, Optional

from dash import dcc, html


def kpi(label: str, value: str, subtitle: str, color: str) -> html.Div:
    """Componente KPI"""
    return html.Div([
        html.Div(label, className="lab"),
        html.Div(value, className="val", style={"color": color}),
        html.Div(subtitle, className="sub"),
    ], className="kpi")


def card(title: str, child: Any, desc: Optional[str] = None, full: bool = False) -> html.Div:
    """Componente tarjeta"""
    body = [html.H3(title)]
    if desc:
        body.append(html.P(desc, className="desc"))
    body.append(child)
    return html.Div(body, className="card" + (" full" if full else ""))


def header(actualizado: str) -> html.Div:
    """Encabezado del dashboard"""
    return html.Div([
        html.Div([
            html.Img(src="assets/bandera.svg", className="flag"),
            html.Div([
                html.H1("Comercio Exterior de Mexico"),
                html.P("Balanza comercial de mercancias, Banco de Mexico (SIE), sin estimaciones")
            ], className="brand-copy"),
        ], className="brand"),
        html.Div([
            html.Span(actualizado, className="upd"),
            html.Button("Actualizar", id="btn-refresh-api", className="refresh-btn", title="Actualizar datos desde Banxico"),
            html.A(
                "Creador",
                href="https://www.linkedin.com/in/juan-carlos-c-a19132211/",
                target="_blank",
                rel="noopener noreferrer",
                className="community-btn",
                title="Abrir creador / perfil de LinkedIn",
            ),
            html.Div("MX", className="avatar"),
        ], className="top-actions"),
    ], className="hdr")


def tabs() -> dcc.Tabs:
    """Navegacion de pestanas"""
    return dcc.Tabs(id="tabs", value="mapa", children=[
        dcc.Tab(label="Mapa por pais", value="mapa"),
        dcc.Tab(label="Aduanas y recaudacion", value="aduanas"),
        dcc.Tab(label="Fracciones/NICO", value="fracciones"),
        dcc.Tab(label="Configuracion", value="operaciones"),
        dcc.Tab(label="Series mensuales", value="series"),
    ])
