"""
Comercio Exterior de Mexico - Dashboard Profesional
App Plotly Dash conectada a API en vivo del Banxico SIE
"""
import os
import json
import time
from functools import lru_cache
from src.env import load_env

load_env()
import plotly.graph_objects as go
import re
import unicodedata
from dash import Dash, dcc, html, Input, Output, State, ctx, callback

from src.data_service import DataService
from src.charts import COUNTRY_COORDS, pie_chart, ranking_chart, serie_chart
from src.components import kpi, card, header, tabs
from src.utils import COLORS, PALETTE, fmt, mdd, mdp, pct
from src.comex.dashboard_sql import AnalysisContext, country_balance_rows, customs_revenue_rows
from src.comex.cartera import cartera_summary
from src.comex.dof import dof_status
from src.comex.etl import etl_status
from src.comex.groq_assistant import ask_groq, groq_status
from src.comex.paths import DB_PATH
from src.comex.db import db_status, record_error
from src.comex.catalogs import (
    HS_CHAPTERS,
    HS_SECTIONS,
    catalog_summary,
    hs_autocomplete,
    hs_explorer_detail,
    search_tigie,
    tariff_operational_file,
)
from src.comex.forecast import forecast_monthly, forecast_text
from src.comex.watchers import recent_alerts
from src.comex.warehouse import customs_revenue_rows_sql

COUNTRY_ISO2 = {
    "ARG": "ar", "AUS": "au", "BEL": "be", "BRA": "br", "CAN": "ca",
    "CHL": "cl", "CHN": "cn", "COL": "co", "CRI": "cr", "DEU": "de",
    "DNK": "dk", "ESP": "es", "FRA": "fr", "GBR": "gb", "GTM": "gt",
    "HKG": "hk", "IDN": "id", "IND": "in", "ISR": "il", "ITA": "it",
    "JPN": "jp", "MYS": "my", "NLD": "nl", "NZL": "nz", "PAN": "pa",
    "PER": "pe", "PHL": "ph", "PRT": "pt", "SGP": "sg", "SLV": "sv",
    "THA": "th", "TWN": "tw", "USA": "us", "VEN": "ve",
}


# ==================== CONFIGURACION ====================
app = Dash(
    __name__,
    title="Comercio Exterior de Mexico",
    suppress_callback_exceptions=True
)
server = app.server

# Servicio de datos con refresh en vivo
data_service = DataService()
LINKEDIN_URL = "https://www.linkedin.com/in/juan-carlos-c-a19132211/"
ASSISTANT_QUICK_PROMPTS = {
    "assistant-quick-balance": "Explica el saldo de la balanza comercial actual con los datos del tablero.",
    "assistant-quick-dof": "Resume publicaciones recientes del DOF relacionadas con comercio exterior.",
    "assistant-quick-tigie": "Ayudame a revisar una fraccion TIGIE/NICO y que datos necesito validar.",
    "assistant-quick-aduanas": "Dime cuales aduanas debo revisar por recaudacion y riesgo operativo.",
    "assistant-quick-next": "Dame el siguiente paso operativo con base en el contexto actual del tablero.",
}


def display_updated(value):
    """Fecha visible: solo fecha y hora."""
    return data_service.display_datetime(value)


def series_date_extent(data):
    """Rango global de fechas disponible en las series mensuales CE125."""
    fechas = [
        fecha
        for serie in (data.series or [])
        for fecha in (serie.fechas or [])
        if fecha
    ]
    if not fechas:
        return None, None
    return min(fechas), max(fechas)


def month_label(value):
    """Convierte YYYY-MM-DD/YYY-MM a etiqueta mensual compacta."""
    if not value:
        return "n.d."
    text = str(value)
    year = text[:4]
    month = text[5:7] if len(text) >= 7 else ""
    months = {
        "01": "ene", "02": "feb", "03": "mar", "04": "abr",
        "05": "may", "06": "jun", "07": "jul", "08": "ago",
        "09": "sep", "10": "oct", "11": "nov", "12": "dic",
    }
    return f"{months.get(month, month)} {year}".strip()


def strip_accents(value):
    text = unicodedata.normalize("NFKD", str(value or ""))
    return "".join(ch for ch in text if not unicodedata.combining(ch))


def ce125_range_text(data):
    start, end = series_date_extent(data)
    if not start or not end:
        return "CE125 sin fechas mensuales disponibles en el cache actual."
    return f"CE125 disponible de {month_label(start)} a {month_label(end)}."


def annual_period_label(data):
    return str((data.anual or {}).get("anio") or "")


def accumulated_period_label(data):
    acumulado = data.acumulado or {}
    periodo = acumulado.get("periodo", "")
    years = sorted(k for k in acumulado.keys() if str(k).isdigit())
    if periodo and years:
        return f"{periodo} {years[-1]}"
    return periodo or "n.d."


def operational_status() -> dict:
    status = etl_status()
    status["catalog"] = catalog_summary()
    status["dof"] = dof_status()
    status["cartera"] = cartera_summary()
    status["alerts"] = recent_alerts(10)
    return status


@lru_cache(maxsize=2)
def operational_status_cached(_minute: int) -> dict:
    return operational_status()


def table_from_records(records, columns, empty="Sin datos"):
    """Renderiza una tabla Dash sencilla desde diccionarios."""
    if not records:
        return html.Div(empty, className="callout")
    head = html.Tr([html.Th(label) for _, label in columns])
    body = [
        html.Tr([html.Td(str(row.get(key, ""))) for key, _ in columns])
        for row in records
    ]
    return html.Table([head] + body, className="dt")


def chips(values, empty="Sin datos"):
    if not values:
        return html.Div(empty, className="muted")
    return html.Div([html.Span(str(value), className="chip") for value in values], className="chip-row")


def hs_trend_figure(data):
    """Grafica compacta de tendencia con series reales agregadas disponibles."""
    fig = go.Figure()
    preferred = [
        serie for serie in (data.series or [])
        if str(getattr(serie, "flujo", "")).lower() in {"exportaciones", "importaciones"}
    ][:2]
    if not preferred:
        preferred = (data.series or [])[:2]
    for serie in preferred:
        fechas = (serie.fechas or [])[-36:]
        valores = (serie.valores or [])[-36:]
        if fechas and valores:
            fig.add_trace(go.Scatter(
                x=fechas,
                y=valores,
                mode="lines",
                name=serie.flujo or serie.nombre,
                line={"width": 2},
            ))
    fig.update_layout(
        height=230,
        margin={"l": 36, "r": 12, "t": 8, "b": 30},
        template="plotly_white",
        legend={"orientation": "h", "y": -0.28, "x": 0},
        xaxis={"showgrid": False},
        yaxis={"gridcolor": "#e8f0ec", "tickformat": ".2s"},
    )
    return fig


def hs_explorer_placeholder():
    return html.Div([
        html.Div("Sin seleccion", className="tigie-panel-kicker"),
        html.Div("Busca un codigo o descripcion para abrir el expediente.", className="tigie-detail-title"),
        html.Div("El detalle muestra jerarquia LIGIE, descripcion, fuente, NICO relacionados, impuestos y regulaciones cuando existan en la base local.", className="tigie-note-box"),
    ], className="hs-empty-panel")


def hs_section_for_chapter(code):
    chapter = int(code) if str(code).isdigit() else 0
    for number, title, first, last in HS_SECTIONS:
        if first <= chapter <= last:
            return {"number": number, "title": title, "range": f"{first:02d}-{last:02d}"}
    return {"number": "", "title": "Sin seccion", "range": ""}


def hs_section_options():
    return [{"label": "Todas las secciones", "value": "all"}] + [
        {"label": f"Seccion {number} Â· {title}", "value": number}
        for number, title, _first, _last in HS_SECTIONS
    ]


def hs_chapter_catalog_view(section_filter="all", text_filter=""):
    query = strip_accents(str(text_filter or "")).lower().strip()
    visible = []
    for code, title in HS_CHAPTERS:
        section = hs_section_for_chapter(code)
        haystack = strip_accents(f"{code} {title} {section['number']} {section['title']}").lower()
        if section_filter and section_filter != "all" and section["number"] != section_filter:
            continue
        if query and query not in haystack:
            continue
        visible.append((code, title, section))

    if not visible:
        return html.Div("No hay capitulos con esos filtros.", className="tigie-empty-state")

    rows = [
        html.Div([
            html.Div(">", className="chapter-caret"),
            html.Div([
                html.Div(f"Cap. {code}", className="chapter-code"),
                html.Div(f"Seccion {section['number']}", className="chapter-section"),
            ], className="chapter-code-stack"),
            html.Div([
                html.Div(title, className="chapter-title"),
                html.Div(section["title"], className="chapter-subtitle"),
            ], className="chapter-copy"),
            html.Div(section["range"], className="chapter-range"),
        ], className="chapter-row")
        for code, title, section in visible
    ]
    return html.Div([
        html.Div([
            html.Div(f"{len(visible)} capitulos", className="tigie-count"),
            html.Div("Usa el buscador superior para abrir partida, subpartida, fraccion o NICO.", className="tigie-list-note"),
        ], className="tigie-list-toolbar"),
        html.Div(rows, className="chapter-list"),
    ], className="tigie-list-wrap")


def hs_detail_panel(detail):
    if not detail:
        return hs_explorer_placeholder()
    meta = [
        {"label": "Ambito", "value": detail.get("scope", "n.d.")},
        {"label": "Fuente", "value": detail.get("source", "n.d.")},
        {"label": "Nivel", "value": str(detail.get("level", "n.d."))},
    ]
    section = detail.get("section", {})
    return html.Div([
        html.Div("Detalle seleccionado", className="tigie-panel-kicker"),
        html.Div(detail.get("display_code", ""), className="tigie-detail-code"),
        html.Div(detail.get("description", ""), className="tigie-detail-title"),
        html.Div([
            html.Div(f"Seccion {section.get('number', 'n.d.')}", className="tigie-section-pill"),
            html.Div(section.get("title", "n.d."), className="tigie-section-text"),
        ], className="tigie-section-line"),
        html.Div([
            html.Div([
                html.Div(item["label"], className="tigie-meta-label"),
                html.Div(item["value"], className="tigie-meta-value"),
            ], className="tigie-meta-item")
            for item in meta
        ], className="tigie-meta-grid"),
        html.Div("Terminos del catalogo", className="tigie-subhead"),
        chips(detail.get("typical_products") or detail.get("synonyms")),
        html.Div("Notas de fuente", className="tigie-subhead"),
        html.Div(detail.get("notes", "Sin notas estructuradas para este registro."), className="tigie-note-box"),
    ], className="hs-panel")


def hs_hierarchy_view(detail):
    if not detail:
        return hs_chapter_catalog_view()
    hierarchy = detail.get("hierarchy", [])
    rows = [
        html.Div([
            html.Div(row.get("step", ""), className="hs-step"),
            html.Div(row.get("display_code", ""), className="hs-code"),
            html.Div(row.get("description", ""), className="hs-desc"),
            html.Div(row.get("source", ""), className="hs-source"),
        ], className="hs-node")
        for row in hierarchy
    ]
    children = detail.get("children", [])
    return html.Div([
        html.Div("Jerarquia LIGIE", className="tigie-panel-kicker"),
        html.Div(rows, className="hs-tree"),
        html.Div("Siguientes niveles", className="tigie-subhead"),
        table_from_records(
            children,
            [("display_code", "Codigo"), ("description", "Descripcion"), ("scope", "Ambito"), ("source", "Fuente")],
            "No hay niveles hijos indexados para este codigo."
        ),
    ])


def tariff_dossier_view(dossier):
    if not dossier:
        return html.Div(
            "Sin expediente operativo para este codigo. Reindexa el catalogo SQL o selecciona una fraccion/NICO.",
            className="callout",
        )
    meta = [
        {"campo": "Codigo", "valor": dossier.get("display_code", dossier.get("code", ""))},
        {"campo": "Fraccion", "valor": dossier.get("fraccion8", "")},
        {"campo": "NICO", "valor": dossier.get("nico10") or "n.d."},
        {"campo": "HS6", "valor": dossier.get("hs6") or "n.d."},
        {"campo": "Ambito", "valor": dossier.get("scope", "n.d.")},
        {"campo": "Fuente", "valor": dossier.get("source_code", "n.d.")},
    ]
    rates = dossier.get("rates") or []
    regulations = dossier.get("regulations") or []
    nicos = dossier.get("nicos") or []
    return html.Div([
        html.Div([
            html.Div([
                html.Div("Expediente operativo", className="lab"),
                html.Div(dossier.get("display_code", dossier.get("code", "")), className="val"),
                html.Div(dossier.get("description", ""), className="sub"),
            ], className="mini-kpi"),
            table_from_records(meta, [("campo", "Campo"), ("valor", "Valor")]),
        ], className="grid"),
        html.H3("NICO relacionados"),
        table_from_records(
            nicos[:12],
            [("nico10", "NICO 10"), ("nico", "NICO"), ("description", "Descripcion"), ("source", "Fuente")],
            "No hay NICO relacionados indexados para esta fraccion."
        ),
        html.H3("Impuestos / unidades"),
        table_from_records(
            rates,
            [
                ("tax_code", "Clave"),
                ("tax_name", "Impuesto"),
                ("import_rate", "Importacion"),
                ("export_rate", "Exportacion"),
                ("unit_name", "Unidad"),
                ("source", "Fuente"),
            ],
            "Pendiente: carga tablas TIGIE/IGI/IGE/IVA/DTA estructuradas en tariff_rate."
        ),
        html.H3("Regulaciones"),
        table_from_records(
            regulations,
            [
                ("type", "Tipo"),
                ("code", "Clave"),
                ("title", "Titulo"),
                ("scope_note", "Acotacion"),
                ("authority", "Autoridad"),
            ],
            "Pendiente: carga NOMs, permisos, cuotas, padrones y tratados en tariff_regulation."
        ),
    ])


def country_flag_url(iso3, width=40):
    iso2 = COUNTRY_ISO2.get(str(iso3 or "").upper())
    return f"https://flagcdn.com/w{width}/{iso2}.png" if iso2 else ""


def country_cell(name, iso3, width=24):
    flag = country_flag_url(iso3, 40)
    children = []
    if flag:
        children.append(html.Img(src=flag, className="country-flag", alt=f"Bandera {name}"))
    children.append(html.Span(str(name or "")))
    return html.Div(children, className="country-cell")


def slugify_anam(value):
    text = unicodedata.normalize("NFD", str(value or "").lower())
    text = "".join(ch for ch in text if unicodedata.category(ch) != "Mn")
    text = re.sub(r"[^a-z0-9]+", "-", text).strip("-")
    return text


def customs_url(name):
    slug = slugify_anam(name)
    return f"https://www.anam.gob.mx/aduana-{slug}/" if slug else "https://www.anam.gob.mx/"


def customs_link(name):
    return html.A(str(name or ""), href=customs_url(name), target="_blank", rel="noopener noreferrer")


def dashboard_assistant_context(data):
    annual = data.anual or {}
    acumulado = data.acumulado or {}
    rec = data.recaudacion_aduanas or {}
    top_countries = sorted(
        (data.paises_balanza or []),
        key=lambda row: abs(float(row[2] or 0)) if len(row) > 2 else 0,
        reverse=True,
    )[:8]
    top_customs = (rec.get("aduanas") or [])[:8]
    lines = [
        f"Fuente: {data.fuente}",
        f"Actualizado: {display_updated(data.actualizado)}",
        f"CE125: {ce125_range_text(data)}",
        (
            f"Anual {annual.get('anio', 'n.d.')}: exportaciones {annual.get('exportaciones', 0)} MDD, "
            f"importaciones {annual.get('importaciones', 0)} MDD, balanza {annual.get('balanza', 0)} MDD."
        ),
        f"Acumulado disponible: {accumulated_period_label(data)}.",
        f"Recaudacion aduanera: {(rec.get('periodo_actual') or {}).get('etiqueta', 'n.d.')}.",
        "Paises con mayor saldo absoluto: "
        + "; ".join(f"{row[0]} ({row[1]}): {row[2]} MDD" for row in top_countries if len(row) >= 3),
        "Aduanas principales por recaudacion: "
        + "; ".join(f"{row.get('aduana')}: {row.get('total')} MDP" for row in top_customs),
    ]
    try:
        status = operational_status_cached(int(time.time() // 60))
        catalog = status.get("catalog", {})
        manifest = status.get("manifest", {})
        dof = status.get("dof", {})
        db_status = status.get("db", {})
        tables = db_status.get("tables", {})
        lines.extend([
            (
                "Catalogo operativo: "
                f"{catalog.get('items', 0)} registros; "
                f"MX {catalog.get('by_scope', {}).get('MX', 0)}; "
                f"HS global {catalog.get('by_scope', {}).get('GLOBAL', 0)}."
            ),
            "Fuentes locales: VUCEM/TIGIE, SNICE NICO, HS global, ANAM corpus, VUCEM notificaciones.",
            f"Manifest ETL: {manifest.get('total', 0)} artefactos descargados.",
            f"Publicaciones DOF comercio exterior indexadas: {dof.get('items', 0)}.",
            f"Documentos DOF tratados/acuerdos ANAM indexados: {tables.get('anam_trade_agreements', 0)}.",
            "Normativa a validar fuera del contexto local cuando aplique: Ley Aduanera, RLA, RGCE, Anexo 22, NOMs, DOF, SAT, ANAM, VUCEM y SNICE.",
        ])
    except Exception as exc:
        lines.append(f"Contexto operativo no disponible: {exc}")
    return "\n".join(line for line in lines if line and not line.endswith(": "))


def assistant_messages_view(messages):
    if not messages:
        return html.Div([
            html.Div("Hola. Soy Comex Bot.", className="assistant-empty-title"),
            html.Div("Pregunta sobre balanza, aduanas, TIGIE/NICO, DOF, Banxico o fuentes del tablero.", className="assistant-empty-sub"),
        ], className="assistant-empty")
    return [
        html.Div([
            html.Div("Tu" if item.get("role") == "user" else "Comex Bot", className="assistant-role"),
            (
                html.Div(str(item.get("content") or ""), className="assistant-text")
                if item.get("role") == "user"
                else dcc.Markdown(
                    str(item.get("content") or ""),
                    className="assistant-text assistant-markdown",
                    dangerously_allow_html=False,
                    link_target="_blank",
                )
            ),
        ], className=f"assistant-msg {item.get('role', 'assistant')}")
        for item in messages
    ]


def comex_bot_widget():
    status = groq_status()
    status_text = (
        f"Groq listo: {status.get('model')}"
        if status.get("configured")
        else "Configura GROQ_API_KEY para respuestas con IA"
    )
    return html.Div([
        dcc.Store(id="assistant-history", data=[]),
        dcc.Store(id="assistant-widget-state", data={"open": False, "expanded": False}),
        html.Button([
            html.Div([
                html.Div(className="comex-eye-shine"),
                html.Div(className="comex-eye-pupil"),
            ], className="comex-eye", **{"aria-hidden": "true"}),
            html.Div([
                html.Div("Comex Bot", className="bot-launch-title"),
                html.Div("Chat operativo", className="bot-launch-sub"),
            ]),
        ], id="assistant-toggle", className="assistant-launcher", title="Abrir Comex Bot"),
        html.Div([
            html.Div([
                html.Div([
                    html.Div([
                        html.Div(className="comex-eye-shine"),
                        html.Div(className="comex-eye-pupil"),
                    ], className="comex-eye", **{"aria-hidden": "true"}),
                    html.Div([
                        html.Div("Comex Bot", className="comex-bot-title"),
                        html.Div(status_text, className="comex-bot-sub"),
                    ], className="comex-bot-copy"),
                ], className="comex-bot-headline"),
                html.Div([
                    html.Button("Expandir", id="assistant-expand", className="bot-icon-btn", title="Abrir en grande"),
                    html.Button("Cerrar", id="assistant-close", className="bot-icon-btn", title="Cerrar chat"),
                ], className="bot-panel-actions"),
            ], className="bot-panel-head"),
            html.Div([
                html.Span("Contexto activo", className="assistant-context-label"),
                html.Span("Comercio exterior MX Â· DOF Â· TIGIE/NICO Â· Aduanas", className="assistant-context-value"),
            ], className="assistant-context-strip"),
            html.Div(id="assistant-chat", children=assistant_messages_view([]), className="assistant-chat"),
            html.Div([
                html.Button("Saldo actual", id="assistant-quick-balance", className="assistant-chip"),
                html.Button("DOF reciente", id="assistant-quick-dof", className="assistant-chip"),
                html.Button("TIGIE/NICO", id="assistant-quick-tigie", className="assistant-chip"),
                html.Button("Aduanas", id="assistant-quick-aduanas", className="assistant-chip"),
                html.Button("Siguiente paso", id="assistant-quick-next", className="assistant-chip"),
            ], className="assistant-quick-row"),
            html.Div([
                dcc.Textarea(
                    id="assistant-question",
                    placeholder="Ej. Explica la balanza actual, revisa una fraccion o resume aduanas.",
                    className="assistant-input",
                    value="",
                ),
                html.Div([
                    html.Button("Enviar", id="assistant-send", className="dl"),
                    html.Button("Limpiar", id="assistant-clear", className="refresh-btn assistant-clear"),
                ], className="assistant-actions"),
            ], className="assistant-compose"),
        ], id="assistant-widget-panel", className="assistant-widget closed"),
    ], className="assistant-layer")


def triggered_id():
    """Devuelve el disparador Dash si existe un contexto de callback."""
    try:
        return ctx.triggered_id
    except Exception:
        return None


def world_context(selected=None, period="", metric="balance"):
    return AnalysisContext.from_selection("country", selected, period, metric)


def customs_context(selected=None, period="", metric="recaudacion"):
    return AnalysisContext.from_selection("customs", selected, period, metric)


def world_period_options(data):
    options = []
    annual = annual_period_label(data)
    if annual:
        options.append({"label": f"Anual {annual}", "value": f"annual:{annual}"})
    acumulado = data.acumulado or {}
    periodo = acumulado.get("periodo", "")
    for year in sorted((k for k in acumulado.keys() if str(k).isdigit()), reverse=True):
        label = f"{periodo} {year}" if periodo else str(year)
        options.append({"label": label, "value": f"acc:{year}"})
    return options or [{"label": "Periodo actual", "value": "annual:"}]


def world_period_metrics(data, period_value):
    kind, _, year = str(period_value or "").partition(":")
    if kind == "acc" and year:
        row = (data.acumulado or {}).get(year, {})
        label = f"{(data.acumulado or {}).get('periodo', '').strip()} {year}".strip()
        return {
            "label": label or year,
            "exports": row.get("exportaciones", 0),
            "imports": row.get("importaciones", 0),
            "balance": row.get("balanza", 0),
        }
    annual = data.anual or {}
    label = str(annual.get("anio") or year or "n.d.")
    return {
        "label": f"Anual {label}" if label != "n.d." else label,
        "exports": annual.get("exportaciones", 0),
        "imports": annual.get("importaciones", 0),
        "balance": annual.get("balanza", 0),
    }


def world_rows(data, ctx=None):
    ctx = ctx or world_context(period=data.anual.get("anio", ""))
    return country_balance_rows(data, ctx)


def world_geo_figure(data, ctx=None):
    ctx = ctx or world_context(period=f"annual:{annual_period_label(data)}", metric="balance")
    rows = [d for d in data.paises_balanza if len(d) >= 3 and d[1] in COUNTRY_COORDS]
    selected = set(ctx.values or [])
    balances = [float(balance or 0) for _, _, balance in rows]
    max_abs = max((abs(v) for v in balances), default=1)
    names = [name for name, _, _ in rows]
    locations = [iso3 for _, iso3, _ in rows]
    hover = [f"{name} ({iso3})<br>Balanza pais: {mdd(balance)}<br>Click para seleccionar" for name, iso3, balance in rows]
    color_scale = [
        [0.0, "#e0454f"],
        [0.48, "#7b2e35"],
        [0.5, "#d8a93a"],
        [0.52, "#25684e"],
        [1.0, "#27c07e"],
    ]
    fig = go.Figure(go.Choropleth(
        locations=locations,
        z=balances,
        locationmode="ISO-3",
        text=names,
        customdata=locations,
        colorscale=color_scale,
        zmin=-max_abs,
        zmax=max_abs,
        marker_line_color="#8fb6a5",
        marker_line_width=0.85,
        colorbar=dict(
            title=dict(text="Balanza", font=dict(color="#d8e7df")),
            tickfont=dict(color="#d8e7df"),
            bgcolor="rgba(6,18,13,.72)",
            outlinecolor="rgba(143,182,165,.35)",
        ),
        hovertext=hover,
        hoverinfo="text",
    ))
    selected_rows = [row for row in rows if row[1] in selected]
    if selected_rows:
        fig.add_trace(go.Choropleth(
            locations=[iso3 for _, iso3, _ in selected_rows],
            z=[float(balance or 0) for _, _, balance in selected_rows],
            locationmode="ISO-3",
            text=[name for name, _, _ in selected_rows],
            customdata=[iso3 for _, iso3, _ in selected_rows],
            colorscale=color_scale,
            zmin=-max_abs,
            zmax=max_abs,
            marker_line_color=COLORS["oro"],
            marker_line_width=3,
            showscale=False,
            hoverinfo="skip",
        ))
    fig.update_geos(
        projection_type="natural earth",
        showland=True,
        landcolor="#153326",
        showcountries=True,
        countrycolor="#5f8274",
        showocean=True,
        oceancolor="#06120d",
        showlakes=True,
        lakecolor="#06120d",
        bgcolor="#06120d",
        lataxis_range=[-60, 80],
    )
    fig.update_layout(
        margin=dict(t=0, r=0, b=0, l=0),
        paper_bgcolor="#06120d",
        plot_bgcolor="#06120d",
        height=520,
        clickmode="event+select",
        font=dict(family="Segoe UI", color="#eaf7f0"),
    )
    return fig


def customs_rows(data, ctx=None):
    ctx = ctx or customs_context(period=(data.recaudacion_aduanas or {}).get("periodo_actual", {}).get("etiqueta", "actual"))
    rows = customs_revenue_rows_sql(ctx.values, ctx.period)
    return rows or customs_revenue_rows(data, ctx)


def customs_map_config(data, metric="recaudacion", period="actual"):
    rows = customs_rows(data, customs_context(period=period, metric=metric))
    features = []
    for row in rows:
        lat = row.get("lat")
        lon = row.get("lon")
        if lat is None or lon is None:
            continue
        key = str(row.get("cve") or row.get("aduana"))
        total = row.get("total") or 0
        props = {
            "id": key,
            "kind": "customs",
            "name": row.get("aduana", key),
            "url": customs_url(row.get("aduana", key)),
            "cve": row.get("cve", ""),
            "tipo": row.get("tipo", ""),
            "total": total,
            "iva": row.get("iva", 0),
            "igi": row.get("igi", 0),
            "dta": row.get("dta", 0),
            "ieps": row.get("ieps", 0),
            "isan": row.get("isan", 0),
            "otros": row.get("otros", 0),
            "variation": row.get("variacion_nominal_pct", 0),
            "metric": metric,
            "period": period,
        }
        features.append({
            "type": "Feature",
            "id": key,
            "properties": props,
            "geometry": {"type": "Point", "coordinates": [lon, lat]},
        })
    return {
        "kind": "customs",
        "metric": metric,
        "period": period,
        "center": [-102.5, 23.8],
        "zoom": 4.25,
        "points": {"type": "FeatureCollection", "features": features},
    }


def map_shell(map_id, event_id, clear_id, config):
    return html.Div([
        html.Div(id=map_id, className="maplibre-map", **{"data-config": json.dumps(config, ensure_ascii=False)}),
        dcc.Input(id=event_id, type="hidden", value="", style={"display": "none"}),
        html.Button("Limpiar seleccion", id=clear_id, className="dl map-clear", **{"data-map-clear": config["kind"]}),
    ], className="map-shell")


def world_summary(data, ctx=None):
    ctx = ctx or world_context(period=f"annual:{annual_period_label(data)}", metric="balance")
    rows = world_rows(data, ctx)
    total = sum(d[2] for d in rows)
    period_metrics = world_period_metrics(data, ctx.period)
    national_exports = period_metrics["exports"]
    national_imports = period_metrics["imports"]
    national_balance = period_metrics["balance"]
    period_label = period_metrics["label"]

    kpis = html.Div([
        kpi(f"Exportaciones {period_label}", f"${fmt(national_exports)} MDD", "total nacional", COLORS["verde2"]),
        kpi(f"Importaciones {period_label}", f"${fmt(national_imports)} MDD", "total nacional", COLORS["rojo"]),
        kpi(f"Balanza {period_label}", mdd(national_balance), "exportaciones - importaciones", COLORS["verde2"] if national_balance >= 0 else COLORS["rojo"]),
        kpi("Balanza por pais", mdd(total), "suma de paises visibles", COLORS["verde2"] if total >= 0 else COLORS["rojo"]),
    ], className="kpis")

    detail_rows = sorted(rows, key=lambda x: abs(x[2]), reverse=True)
    selected_note = "Selecciona paises en el mapa para verlos aqui y filtrar rankings y tabla."
    if ctx.values:
        selected_note = f"{len(rows)} pais(es) seleccionados."
    selected_cards = []
    if ctx.values:
        for name, iso3, balance in sorted(rows, key=lambda item: abs(item[2]), reverse=True)[:6]:
            selected_cards.append(html.Div([
                html.Div(country_cell(name, iso3), className="lab"),
                html.Div(mdd(balance), className="val", style={"color": COLORS["verde2"] if balance >= 0 else COLORS["rojo"]}),
                html.Div("balanza por pais", className="sub"),
            ], className="mini-kpi"))
    else:
        selected_cards.append(html.Div([
            html.Div("Sin seleccion", className="lab"),
            html.Div("Elige uno o mas paises", className="val"),
            html.Div("usa click sobre el pais en el mapa", className="sub"),
        ], className="mini-kpi"))
    details = html.Div([
        html.H3("Detalle de pais"),
        html.P(selected_note, className="desc"),
        *selected_cards,
    ], className="map-panel-inner")

    rows_html = [html.Tr([
        html.Td(country_cell(d[0], d[1])),
        html.Td(d[1]),
        html.Td(mdd(d[2]), style={"color": COLORS["verde2"] if d[2] >= 0 else COLORS["rojo"], "textAlign": "right"}),
    ]) for d in sorted(detail_rows, key=lambda x: -x[2])]
    table = html.Table([
        html.Tr([
            html.Th("Pais"),
            html.Th("ISO3"),
            html.Th("Balanza", style={"textAlign": "right"}),
        ])
    ] + rows_html, className="dt")
    lower = html.Div([
        card("Mayores superavit", dcc.Graph(figure=ranking_chart(rows, True)), "Mexico exporta mas de lo que importa."),
        card("Mayores deficit", dcc.Graph(figure=ranking_chart(rows, False)), "Mexico importa mas de lo que exporta."),
        card("Tabla por pais", html.Div(table, className="table-scroll"), full=True),
    ], className="grid map-results-grid")
    return kpis, details, lower


def customs_summary(data, ctx=None):
    ctx = ctx or customs_context(period=(data.recaudacion_aduanas or {}).get("periodo_actual", {}).get("etiqueta", "actual"))
    rows = customs_rows(data, ctx)
    total = sum((r.get("total") or 0) for r in rows)
    top = max(rows, key=lambda r: r.get("total") or 0) if rows else {}
    variation_rows = [r for r in rows if r.get("variacion_nominal_pct") is not None]
    avg_variation = sum(r.get("variacion_nominal_pct") or 0 for r in variation_rows) / len(variation_rows) if variation_rows else 0

    kpis = html.Div([
        kpi("Periodo", ctx.period or "actual", f"{len(rows)} aduana(s) filtradas", COLORS["oro"]),
        kpi("Total visible", mdp(total), "recaudacion filtrada", COLORS["verde2"]),
        kpi("Variacion prom.", pct(avg_variation), "vs. mismo periodo previo", COLORS["verde2"] if avg_variation >= 0 else COLORS["rojo"]),
        kpi("Principal", top.get("aduana", "n.d."), mdp(top.get("total", 0)) if top else "sin dato", COLORS["verde2"]),
    ], className="kpis")

    tax_scope = f"{len(rows)} aduana(s) seleccionadas" if ctx.values else "todas las aduanas visibles"
    details = html.Div([
        html.Div([
            html.Div("IVA", className="lab"),
            html.Div(mdp(sum(r.get("iva") or 0 for r in rows)), className="val"),
            html.Div(tax_scope, className="sub"),
        ], className="mini-kpi tax-kpi"),
        html.Div([
            html.Div("IGI", className="lab"),
            html.Div(mdp(sum(r.get("igi") or 0 for r in rows)), className="val"),
            html.Div(tax_scope, className="sub"),
        ], className="mini-kpi tax-kpi"),
        html.Div([
            html.Div("IEPS", className="lab"),
            html.Div(mdp(sum(r.get("ieps") or 0 for r in rows)), className="val"),
            html.Div(tax_scope, className="sub"),
        ], className="mini-kpi tax-kpi"),
    ], className="customs-tax-strip")

    sort_key = (
        (lambda r: abs(r.get("variacion_nominal_pct") or 0))
        if ctx.metric == "variation"
        else (lambda r: r.get("total") or 0)
    )
    rows_html = [html.Tr([
        html.Td(customs_link(r.get("aduana", ""))),
        html.Td(r.get("tipo", "")),
        html.Td(mdp(r.get("total", 0)), style={"textAlign": "right"}),
        html.Td(pct(r.get("variacion_nominal_pct", 0) or 0), style={"textAlign": "right"}),
    ]) for r in sorted(rows, key=sort_key, reverse=True)]
    table = html.Table([
        html.Tr([
            html.Th("Aduana"),
            html.Th("Tipo"),
            html.Th("Total", style={"textAlign": "right"}),
            html.Th("Var.", style={"textAlign": "right"}),
        ])
    ] + rows_html, className="dt")
    lower = card(
        "Ranking de aduanas",
        html.Div(table, className="table-scroll"),
        "Tabla filtrada por seleccion del mapa y ordenada por la metrica activa.",
        True,
    )
    return kpis, details, html.Div(lower, className="grid")


def format_count(value):
    try:
        return f"{int(value):,}"
    except (TypeError, ValueError):
        return str(value or 0)


def operational_table_groups(tables):
    groups = {
        "Dashboard": [
            "warehouse_snapshot",
            "dim_banxico_series",
            "fact_banxico_series_monthly",
            "fact_dashboard_annual",
            "fact_dashboard_accumulated",
            "fact_country_balance",
            "dim_customs",
            "fact_customs_revenue",
            "fact_trade_component",
        ],
        "Catalogo arancelario": [
            "catalog_item",
            "tariff_fraction",
            "tariff_nico",
            "tariff_rate",
            "tariff_regulation",
            "tariff_fraction_regulation",
            "vucem_tigie_items",
            "dim_nico_catalog",
        ],
        "Operacion": [
            "load_run",
            "etl_file_registry",
            "vucem_notifications",
            "anam_public_pages",
            "anam_trade_agreements",
            "pedimento",
            "pedimento_item",
        ],
    }
    rows = []
    for group_name, names in groups.items():
        total = sum(int(tables.get(name, 0) or 0) for name in names)
        active = sum(1 for name in names if int(tables.get(name, 0) or 0) > 0)
        rows.append({
            "grupo": group_name,
            "tablas": f"{active}/{len(names)}",
            "registros": format_count(total),
        })
    return rows


def operational_source_rows(sources, manifest):
    by_source = manifest.get("by_source", {}) or {}
    return [
        {
            "fuente": row.get("name", ""),
            "artefactos": format_count(by_source.get(row.get("name", ""), 0)),
            "descripcion": row.get("description", ""),
        }
        for row in sources
    ]


def operational_run_rows(runs):
    rows = []
    for row in runs:
        rows.append({
            "source": row.get("source", ""),
            "status": row.get("status", ""),
            "records_loaded": format_count(row.get("records_loaded", 0)),
            "finished_at": row.get("finished_at") or row.get("started_at", ""),
            "message": row.get("message", ""),
        })
    return rows


# ==================== HEALTH CHECK ====================
@server.get("/healthz")
def healthz():
    """Health check endpoint para Kubernetes/Load Balancers"""
    data = data_service._memory_cache
    ready = bool(data or DB_PATH.exists() or data_service.CACHE_FILE.exists())
    status = db_status() if DB_PATH.exists() else {}
    recent_errors = status.get("recent_errors", [])[:3]
    return {
        "status": "ok" if ready else "degraded",
        "updated": display_updated(data.actualizado) if data else "unknown",
        "series": len(data.series) if data else 0,
        "complete": data.completo if data else False,
        "recent_errors": recent_errors,
    }, 200 if ready else 503


# ==================== LAYOUT ====================
def create_layout():
    """Crea layout del dashboard con datos en vivo"""
    try:
        # Cargar datos EN VIVO
        data = data_service.get_data()
    except Exception as e:
        record_error("app.create_layout", e)
        return html.Div([
            html.Div(f"[ERROR] No se pudieron cargar datos: {e}", className="callout"),
        ], className="wrap")

    return html.Div([
        html.Div(header(display_updated(data.actualizado)), id="header-container"),
        tabs(),
        dcc.Interval(id="api-bootstrap-refresh", interval=1000, max_intervals=1),
        dcc.Loading(
            html.Div(id="content", className="wrap"),
            type="circle", color=COLORS["verde2"]
        ),
        comex_bot_widget(),
    ])


app.layout = create_layout


@callback(
    Output("header-container", "children"),
    Output("content", "children"),
    Input("tabs", "value"),
    Input("btn-refresh-api", "n_clicks"),
    Input("api-bootstrap-refresh", "n_intervals"),
    prevent_initial_call=False
)
def render_tab(tab_value, refresh_clicks, bootstrap_intervals):
    """Renderiza contenido de pestana con datos FRESCOS cada vez"""
    trigger = triggered_id()
    force_refresh = (
        trigger == "btn-refresh-api"
        or (
            trigger == "api-bootstrap-refresh"
            and data_service.LIVE_BOOTSTRAP
            and bool(bootstrap_intervals)
        )
    )
    try:
        data = data_service.get_data(force_refresh=force_refresh)
    except Exception as e:
        record_error("app.render_tab", e)
        return header("n.d."), html.Div(f"[ERROR] {e}", className="callout")

    header_child = header(display_updated(data.actualizado))

    # ==================== MAPA MUNDIAL ====================
    if tab_value == "mapa":
        period_options = world_period_options(data)
        period = period_options[0]["value"]
        metric = "balance"
        world_ctx = world_context(period=period, metric=metric)
        kpis_child, details_child, lower_child = world_summary(data, world_ctx)

        return header_child, [
            html.Div([
                html.Div([
                    html.Div("Comercio exterior operativo", className="trust-eyebrow"),
                    html.Div("Datos, clasificacion y cumplimiento en un solo tablero", className="trust-title"),
                ], className="trust-copy"),
                html.Div([
                    html.Div([html.Div("Banxico SIE", className="trust-value"), html.Div("series oficiales", className="trust-label")], className="trust-item"),
                    html.Div([html.Div("TIGIE/NICO", className="trust-value"), html.Div("catalogo SQL local", className="trust-label")], className="trust-item"),
                    html.Div([html.Div("DOF/ANAM", className="trust-value"), html.Div("fuentes indexadas", className="trust-label")], className="trust-item"),
                ], className="trust-stats"),
            ], className="trust-strip"),
            dcc.Store(id="world-selected-store", data=[]),
            html.Div([
                html.Div([html.Label("Periodo"), dcc.Dropdown(
                    id="world-period",
                    options=period_options,
                    value=period,
                    clearable=False,
                    style={"width": "280px"}
                )]),
                html.Div([html.Label("Metrica"), dcc.Dropdown(
                    id="world-metric",
                    options=[
                        {"label": "Balanza por pais", "value": "balance"},
                    ],
                    value=metric,
                    clearable=False,
                    style={"width": "280px"}
                )]),
            ], className="controls"),
            html.Div(kpis_child, id="world-kpis"),
            html.Div([
                card("Comercio por pais", html.Div([
                    dcc.Graph(
                        id="world-geo-map",
                        figure=world_geo_figure(data, world_ctx),
                        config={"displayModeBar": False, "responsive": True},
                        className="world-geo-graph",
                    ),
                    html.Button("Limpiar seleccion", id="world-clear", className="dl map-clear"),
                ], className="map-shell"), "Click para seleccionar paises; el panel muestra exportaciones, importaciones y balanza en ese orden."),
                html.Div(details_child, id="world-details", className="map-panel"),
            ], className="map-layout"),
            html.Div(lower_child, id="world-lower"),
        ]

    # ==================== ADUANAS ====================
    elif tab_value == "aduanas":
        rec = data.recaudacion_aduanas or {}
        period = rec.get("periodo_actual", {}).get("etiqueta", "actual")
        kpis_child, details_child, lower_child = customs_summary(data)

        return header_child, [
            html.Div([
                html.Div([html.Label("Periodo"), dcc.Dropdown(
                    id="customs-period",
                    options=[{"label": period, "value": period}],
                    value=period,
                    clearable=False,
                    style={"width": "210px"}
                )]),
                html.Div([html.Label("Metrica"), dcc.Dropdown(
                    id="customs-metric",
                    options=[
                        {"label": "Recaudacion total", "value": "recaudacion"},
                        {"label": "Variacion nominal", "value": "variation"},
                    ],
                    value="recaudacion",
                    clearable=False,
                    style={"width": "210px"}
                )]),
            ], className="controls"),
            html.Div(kpis_child, id="customs-kpis"),
            html.Div([
                card("Aduanas y recaudacion ANAM", html.Div([
                    map_shell(
                        "customs-maplibre",
                        "customs-map-event",
                        "customs-map-clear",
                        customs_map_config(data, "recaudacion", period)
                    ),
                    html.Div(details_child, id="customs-details"),
                ], className="customs-map-card-body"), "Click para seleccionar aduanas; KPIs, impuestos y tabla consultan DuckDB con el mismo filtro.", True),
            ], className="customs-map-layout"),
            html.Div(lower_child, id="customs-lower"),
        ]

    # ==================== FRACCIONES / NICO ====================
    elif tab_value == "fracciones":
        return header_child, [
            html.Div([
                html.Div([
                    html.Div([
                        html.Div("T", className="tariff-book-mark"),
                        html.Div([
                            html.Div("TIGIE 2026", className="tariff-app-title"),
                            html.Div("Consulta por capitulo, partida, subpartida, fraccion o NICO con una interfaz limpia y consistente.", className="tariff-app-subtitle"),
                        ]),
                    ], className="tariff-titlebar-copy"),
                ], className="tariff-titlebar"),
                html.Div([
                    html.Div([
                        html.Div("Buscar en LIGIE", className="tariff-search-label"),
                        html.Div("Ejemplos: 0101, 2106.90, cafe tostado, tornillo de acero", className="tariff-search-help"),
                    ], className="tariff-search-head"),
                    html.Div([
                        dcc.Dropdown(
                            id="hs-code-select",
                            options=[],
                            placeholder="Codigo, fraccion, NICO o descripcion...",
                            searchable=True,
                            clearable=True,
                            className="tariff-select",
                        ),
                        html.Button("Buscar", id="btn-hs-search", className="tariff-primary-search"),
                    ], className="tariff-searchbar"),
                ], className="tariff-search-strip"),
                html.Div([
                    html.Div([
                        html.Div([
                            html.Label("Seccion"),
                            dcc.Dropdown(
                                id="tigie-section-filter",
                                options=hs_section_options(),
                                value="all",
                                clearable=False,
                                className="tigie-filter-dropdown",
                            ),
                        ], className="tigie-filter-field"),
                        html.Div([
                            html.Label("Filtrar capitulos"),
                            dcc.Input(
                                id="tigie-chapter-filter",
                                type="text",
                                placeholder="Capitulo o palabra clave",
                                debounce=True,
                                className="tigie-filter-input",
                            ),
                        ], className="tigie-filter-field tigie-filter-grow"),
                        html.Div([
                            html.Div("Flujo", className="tigie-flow-label"),
                            html.Div([
                                html.Span("1 Buscar", className="tigie-flow-step active"),
                                html.Span("2 Revisar jerarquia", className="tigie-flow-step"),
                                html.Span("3 Ver expediente", className="tigie-flow-step"),
                            ], className="tigie-flow-row"),
                        ], className="tigie-flow"),
                    ], className="tigie-filter-bar"),
                    html.Div([
                        dcc.Input(
                            id="fraccion-query",
                            type="text",
                            placeholder="Busqueda por descripcion: cafe tostado, pantalon de algodon, tornillo de acero...",
                            debounce=True,
                            className="tariff-advanced-input",
                        ),
                        html.Button("Buscar texto", id="btn-buscar-fraccion", className="tariff-advanced-button"),
                    ], className="tariff-advanced-search"),
                    html.Div(id="fraccion-results", className="tigie-search-results"),
                    html.Div([
                        html.Div([
                            html.Div("Catalogo de capitulos", className="tariff-section-title"),
                            html.Div("Vista ligera para navegar secciones. Busca arriba para abrir el detalle real.", className="muted"),
                        ], className="tariff-panel-head"),
                        html.Div(id="hs-drilldown", children=hs_chapter_catalog_view()),
                    ], className="tariff-panel tariff-main"),
                    html.Div([
                        html.Div(id="hs-side-panel", children=hs_explorer_placeholder(), className="tariff-panel tariff-side"),
                        html.Div(id="tariff-dossier", className="tariff-panel tariff-dossier"),
                    ], className="tigie-detail-grid"),
                ], className="tariff-workspace"),
            ], className="tariff-shell"),
        ]

    # ==================== CONFIGURACION ====================
    elif tab_value == "operaciones":
        try:
            status = operational_status()
            db_status = status.get("db", {})
            manifest = status.get("manifest", {})
            cartera = status.get("cartera", {})
            alerts = status.get("alerts", [])
            tables = db_status.get("tables", {}) or {}
            runs = operational_run_rows(db_status.get("last_runs", []))
            source_rows = operational_source_rows(status.get("sources", []), manifest)
            group_rows = operational_table_groups(tables)
            catalog_records = tables.get("catalog_item", 0)
            tariff_records = tables.get("tariff_fraction", 0)
            nico_records = tables.get("tariff_nico", 0)
            last_run = runs[0] if runs else {}
            db_initialized = db_status.get("initialized")
            config_rows = [
                {"clave": "Proyecto", "valor": "Comercio Exterior de Mexico"},
                {"clave": "Creador", "valor": "Juan Carlos C."},
                {"clave": "Datos", "valor": "Banxico SIE, TIGIE/NICO, DOF/ANAM, DuckDB local"},
                {"clave": "Base local", "valor": "data/comex.duckdb"},
                {"clave": "Ejecucion", "valor": "python run.py --no-install"},
            ]
            flow_rows = [
                {"paso": "1", "proceso": "Ingesta", "detalle": "Descarga fuentes publicas y conserva artefactos en manifest."},
                {"paso": "2", "proceso": "Normalizacion", "detalle": "Carga catalogos, series y aduanas a DuckDB."},
                {"paso": "3", "proceso": "Dashboard", "detalle": "Consulta cache local y renderiza mapas, TIGIE, series y diagnosticos."},
            ]

            return header_child, [
                html.Div([
                    html.Div([
                        html.Div("Configuracion", className="settings-eyebrow"),
                        html.Div("Sistema, diagnosticos y fuentes", className="settings-title"),
                        html.Div("Todo lo operativo del tablero en un solo lugar: como corre, quien lo hizo, estado de datos y base local.", className="settings-subtitle"),
                    ]),
                    html.A(
                        "Perfil del creador",
                        href=LINKEDIN_URL,
                        target="_blank",
                        rel="noopener noreferrer",
                        className="settings-link",
                    ),
                ], className="settings-hero"),
                html.Div([
                    kpi("DuckDB", "OK" if db_initialized else "Sin init", "data/comex.duckdb",
                        COLORS["verde2"] if db_initialized else COLORS["oro"]),
                    kpi("Catalogo", format_count(catalog_records), f"{format_count(tariff_records)} fracciones / {format_count(nico_records)} NICO", COLORS["verde2"]),
                    kpi("Manifest", format_count(manifest.get("total", 0)), f"ultimo artefacto {manifest.get('latest', 'n.d.')}", COLORS["oro"]),
                    kpi("Cartera RFC", str(cartera.get("count", 0)), "clientes vigilados", COLORS["verde2"]),
                    kpi("Alertas", str(len(alerts)), "ultimas en JSONL",
                        COLORS["rojo"] if alerts else COLORS["verde2"]),
                ], className="kpis"),
                html.Div([
                    card("Como funciona", table_from_records(
                        flow_rows,
                        [("paso", "Paso"), ("proceso", "Proceso"), ("detalle", "Detalle")]
                    )),
                    card("Informacion del sistema", table_from_records(
                        config_rows,
                        [("clave", "Clave"), ("valor", "Valor")]
                    )),
                    card("Ultima corrida", html.Div([
                        html.Div([
                            html.Div(last_run.get("source", "Sin runs"), className="op-run-source"),
                            html.Div(last_run.get("status", "n.d."), className=f"op-status {str(last_run.get('status', '')).lower()}"),
                        ], className="op-run-head"),
                        html.Div(last_run.get("finished_at", ""), className="muted"),
                        html.Div(last_run.get("message") or "Sin mensajes de error.", className="op-run-message"),
                    ], className="op-run-card")),
                    card("Base de datos",
                         table_from_records(group_rows, [("grupo", "Grupo"), ("tablas", "Tablas activas"), ("registros", "Registros")])),
                    card("Fuentes ETL",
                         html.Div(table_from_records(
                             source_rows,
                             [("fuente", "Fuente"), ("artefactos", "Artefactos"), ("descripcion", "Descripcion")],
                             "Sin fuentes configuradas"
                         ), className="table-scroll"),
                         "Artefactos descargados por fuente publica."),
                    card("Diagnosticos de ejecucion", html.Div(table_from_records(
                        runs,
                        [("source", "Fuente"), ("status", "Estado"), ("records_loaded", "Registros"), ("finished_at", "Termino"), ("message", "Mensaje")],
                        "Sin runs"
                    ), className="table-scroll"), full=True),
                    card("Configuracion de cartera", html.Div(table_from_records(
                        cartera.get("clientes", []),
                        [("rfc", "RFC"), ("razon", "Razon"), ("email", "Email"), ("whatsapp", "WhatsApp")],
                        "Sin RFCs registrados"
                    ), className="table-scroll")),
                    card("Alertas recientes", html.Div(table_from_records(
                        alerts,
                        [("created_at", "Fecha"), ("rfc", "RFC"), ("title", "Titulo"), ("dry_run", "Dry-run")],
                        "Sin alertas"
                    ), className="table-scroll")),
                ], className="grid ops-grid"),
            ]
        except Exception as e:
            return header_child, html.Div(f"Capa operativa no disponible: {e}", className="callout")

    # ==================== SERIES MENSUALES ====================
    elif tab_value == "series":
        n_max = max((len(s.fechas) for s in data.series), default=0)
        first_series = data.series[0] if data.series else None
        first_forecast = forecast_monthly(first_series.fechas, first_series.valores) if first_series else {}
        anio = annual_period_label(data) or "n.d."
        nota = (f"El SIE aporta hasta {n_max} meses de historia mensual. {ce125_range_text(data)}" if data.completo
                else f"El SIE aporta {n_max} meses reales. {ce125_range_text(data)} Corre `python banxico_sie.py` para historia completa.")

        return header_child, [
            html.Div(nota, className="callout"),
            html.Div([
                html.Label("Serie"),
                dcc.Dropdown(
                    id="select-serie",
                    options=[{"label": s.nombre, "value": s.nombre} for s in data.series],
                    value=data.series[0].nombre if data.series else "",
                    clearable=False,
                    style={"width": "300px"}
                )
            ], className="controls"),
            html.Div(
                card(
                    "Serie mensual",
                    dcc.Graph(figure=serie_chart(first_series.fechas, first_series.valores, first_forecast)),
                    (f"Observaciones reales de {month_label(first_series.fechas[0])} a {month_label(first_series.fechas[-1])} (miles USD)."
                     if first_series.fechas else "Sin observaciones disponibles.")
                    + " "
                    + forecast_text(first_forecast),
                    True,
                ) if first_series else html.Div("Sin series CE125 disponibles.", className="callout"),
                id="serie-chart-container",
                className="grid",
            ),
            html.Div([
                card(f"Exportaciones por industria ({anio})",
                     dcc.Graph(figure=pie_chart(data.industrias_exportacion, PALETTE)),
                     "Composicion del valor exportado."),
                card(f"Importaciones por tipo de bien ({anio})",
                     dcc.Graph(figure=pie_chart(data.importaciones_uso, [COLORS["rojo"], "#e88a90", "#f2c0c3"])),
                     "Consumo, intermedio y capital."),
            ], className="grid series-industry-grid"),
        ]

    return header_child, html.Div("Selecciona una pestana del tablero.", className="callout")


def selected_from_event(value, expected_kind):
    if not value:
        return []
    try:
        payload = json.loads(value)
    except (TypeError, ValueError):
        return []
    if payload.get("kind") != expected_kind:
        return []
    return payload.get("selected") or []


@callback(
    Output("customs-maplibre", "data-config"),
    Input("customs-period", "value"),
    Input("customs-metric", "value"),
    prevent_initial_call=True
)
def update_customs_map_config(period, metric):
    data = data_service.get_data()
    return json.dumps(customs_map_config(data, metric or "recaudacion", period or "actual"), ensure_ascii=False)


@callback(
    Output("world-selected-store", "data"),
    Input("world-geo-map", "clickData"),
    Input("world-clear", "n_clicks"),
    State("world-selected-store", "data"),
    prevent_initial_call=True
)
def update_world_selected(click_data, _clear_clicks, selected):
    trigger = triggered_id()
    if trigger == "world-clear":
        return []
    selected = list(selected or [])
    if trigger == "world-geo-map" and click_data:
        point = (click_data.get("points") or [{}])[0]
        iso3 = point.get("customdata") or point.get("location")
        if iso3:
            if iso3 in selected:
                selected.remove(iso3)
            else:
                selected.append(iso3)
    return selected


@callback(
    Output("world-geo-map", "figure"),
    Output("world-kpis", "children"),
    Output("world-details", "children"),
    Output("world-lower", "children"),
    Input("world-selected-store", "data"),
    Input("world-period", "value"),
    Input("world-metric", "value"),
    prevent_initial_call=True
)
def update_world_selection(selected, _period, _metric):
    data = data_service.get_data()
    world_ctx = world_context(selected or [], _period, _metric)
    kpis_child, details_child, lower_child = world_summary(data, world_ctx)
    return world_geo_figure(data, world_ctx), kpis_child, details_child, lower_child


@callback(
    Output("customs-kpis", "children"),
    Output("customs-details", "children"),
    Output("customs-lower", "children"),
    Input("customs-map-event", "value"),
    Input("customs-period", "value"),
    Input("customs-metric", "value"),
    prevent_initial_call=True
)
def update_customs_selection(event_value, _period, _metric):
    data = data_service.get_data()
    selected = selected_from_event(event_value, "customs")
    return customs_summary(data, customs_context(selected, _period, _metric))


# ==================== SERIE TEMPORAL ====================
@callback(
    Output("serie-chart-container", "children"),
    Input("select-serie", "value"),
    prevent_initial_call=True
)
def update_serie_chart(serie_name):
    """Actualiza grafico de serie seleccionada"""
    data = data_service.get_data()
    serie = next((s for s in data.series if s.nombre == serie_name), None)
    if not serie:
        return html.Div("Serie no encontrada", className="callout")
    forecast = forecast_monthly(serie.fechas, serie.valores)

    return card(
        "Serie mensual",
        dcc.Graph(figure=serie_chart(serie.fechas, serie.valores, forecast)),
        (f"Observaciones reales de {month_label(serie.fechas[0])} a {month_label(serie.fechas[-1])} (miles USD)."
         if serie.fechas else "Sin observaciones disponibles.")
        + " "
        + forecast_text(forecast),
        True
    )


@callback(
    Output("fraccion-results", "children"),
    Input("btn-buscar-fraccion", "n_clicks"),
    State("fraccion-query", "value"),
    prevent_initial_call=True
)
def update_fraccion_results(_n, query):
    """Busca fracciones TIGIE/NICO desde la capa comex."""
    if not query or not query.strip():
        return html.Div("Escribe una descripcion o codigo para buscar.", className="callout")
    try:
        rows = search_tigie(query, 12)
    except Exception as e:
        return html.Div(f"No se pudo buscar en el catalogo: {e}", className="callout")
    return table_from_records(
        rows,
        [
            ("code", "Codigo"),
            ("description", "Descripcion"),
            ("scope", "Ambito"),
            ("level", "Nivel"),
            ("source", "Fuente"),
            ("score", "Score"),
            ("source_file", "Archivo"),
        ],
        "Sin coincidencias. Ejecuta `python comex.py etl run vucem-tigie` para descargar e indexar el catalogo."
    )


@callback(
    Output("hs-code-select", "options"),
    Input("hs-code-select", "search_value"),
    State("hs-code-select", "value"),
    prevent_initial_call=False
)
def update_hs_autocomplete(search_value, selected_value):
    query = search_value or selected_value
    if not str(query).strip():
        return []
    try:
        return hs_autocomplete(query, 20)
    except Exception:
        return []


@callback(
    Output("hs-drilldown", "children"),
    Output("hs-side-panel", "children"),
    Output("tariff-dossier", "children"),
    Input("hs-code-select", "value"),
    Input("btn-hs-search", "n_clicks"),
    Input("tigie-section-filter", "value"),
    Input("tigie-chapter-filter", "value"),
    State("hs-code-select", "search_value"),
    prevent_initial_call=False
)
def update_hs_explorer(code, _search_clicks, section_filter, chapter_filter, search_value):
    if ctx.triggered_id == "btn-hs-search" and search_value:
        code = search_value
    if ctx.triggered_id in {"tigie-section-filter", "tigie-chapter-filter"}:
        code = None
    if not code:
        return hs_chapter_catalog_view(section_filter, chapter_filter), hs_explorer_placeholder(), html.Div()
    try:
        detail = hs_explorer_detail(code)
        dossier = tariff_operational_file(code)
    except Exception as e:
        return (
            html.Div(f"No se pudo cargar el codigo HS: {e}", className="callout"),
            hs_explorer_placeholder(),
            html.Div(),
        )
    if not detail:
        return (
            html.Div("Sin detalle para ese codigo en el catalogo local.", className="callout"),
            hs_explorer_placeholder(),
            tariff_dossier_view(dossier),
        )
    return hs_hierarchy_view(detail), hs_detail_panel(detail), tariff_dossier_view(dossier)


@callback(
    Output("assistant-widget-state", "data"),
    Output("assistant-widget-panel", "className"),
    Output("assistant-expand", "children"),
    Input("assistant-toggle", "n_clicks"),
    Input("assistant-close", "n_clicks"),
    Input("assistant-expand", "n_clicks"),
    State("assistant-widget-state", "data"),
    prevent_initial_call=False
)
def update_assistant_widget(_toggle, _close, _expand, state):
    state = dict(state or {"open": False, "expanded": False})
    trigger = triggered_id()
    if trigger == "assistant-toggle":
        state["open"] = not state.get("open", False)
        if not state["open"]:
            state["expanded"] = False
    elif trigger == "assistant-close":
        state = {"open": False, "expanded": False}
    elif trigger == "assistant-expand":
        state["open"] = True
        state["expanded"] = not state.get("expanded", False)

    classes = ["assistant-widget"]
    if not state.get("open", False):
        classes.append("closed")
    if state.get("expanded", False):
        classes.append("expanded")
    expand_label = "Reducir" if state.get("expanded", False) else "Expandir"
    return state, " ".join(classes), expand_label


@callback(
    Output("assistant-history", "data"),
    Output("assistant-chat", "children"),
    Output("assistant-question", "value"),
    Input("assistant-send", "n_clicks"),
    Input("assistant-clear", "n_clicks"),
    Input("assistant-quick-balance", "n_clicks"),
    Input("assistant-quick-dof", "n_clicks"),
    Input("assistant-quick-tigie", "n_clicks"),
    Input("assistant-quick-aduanas", "n_clicks"),
    Input("assistant-quick-next", "n_clicks"),
    State("assistant-question", "value"),
    State("assistant-history", "data"),
    prevent_initial_call=True
)
def update_assistant(
    _send_clicks,
    _clear_clicks,
    _quick_balance,
    _quick_dof,
    _quick_tigie,
    _quick_aduanas,
    _quick_next,
    question,
    history,
):
    trigger = triggered_id()
    if trigger == "assistant-clear":
        return [], assistant_messages_view([]), ""
    history = list(history or [])
    question = ASSISTANT_QUICK_PROMPTS.get(trigger, str(question or "").strip())
    if not question:
        return history, assistant_messages_view(history), ""

    visible_history = history + [{"role": "user", "content": question}]
    try:
        data = data_service.get_data()
        answer = ask_groq(question, history, dashboard_assistant_context(data))
    except Exception as e:
        record_error("app.update_assistant", e)
        answer = f"No pude consultar Groq: {e}"
    updated = visible_history + [{"role": "assistant", "content": answer}]
    return updated, assistant_messages_view(updated), ""


app.index_string = """<!DOCTYPE html><html><head>{%metas%}<title>{%title%}</title>{%favicon%}{%css%}</head><body><div class="bg"></div>{%app_entry%}<footer>{%config%}{%scripts%}{%renderer%}</footer></body></html>"""


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8050))
    app.run(host="0.0.0.0", port=port, debug=False, use_reloader=False, threaded=True)
