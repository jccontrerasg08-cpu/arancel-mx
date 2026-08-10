"""
Utilidades para formateo y conversion de datos
"""

def fmt(value: float) -> str:
    """Formatea numero con separadores de miles en espanol"""
    return f"{round(value):,}".replace(",", " ")


def mdd(value: float) -> str:
    """Formatea en Millones de Dolares"""
    sign = "+" if value >= 0 else ""
    return f"{sign}${fmt(value)} MDD"


def mdp(value: float) -> str:
    """Formatea en Millones de Pesos"""
    return f"${fmt(value)} MDP"


def pct(value: float) -> str:
    """Formatea porcentaje"""
    sign = "+" if value >= 0 else ""
    return f"{sign}{value:.1f}%"


# Colores corporativos
COLORS = {
    "verde": "#1f8a5b",
    "verde2": "#27c07e",
    "rojo": "#e0454f",
    "oro": "#d8a93a",
    "tinta": "#0f2b22",
}

PALETTE = [
    "#1f8a5b", "#27c07e", "#5bbf8a", "#d8a93a",
    "#e0454f", "#3a86a8", "#9a7bb0", "#c98a2b"
]

# Configuraciones de graficos
MAP_HOVER = dict(
    bgcolor=COLORS["tinta"],
    bordercolor=COLORS["oro"],
    font=dict(family="Segoe UI", size=12, color="#fff")
)
