"""
Catalogo de series del SIE de Banco de Mexico - Comercio Exterior
==================================================================

IDs de serie VERIFICADOS extraidos del cuadro CE125 del SIE
("Balanza comercial de mercancias de Mexico", periodicidad mensual,
unidad: miles de dolares).

Fuente del cuadro:
https://www.banxico.org.mx/SieInternet/consultarDirectorioInternetAction.do?accion=consultarCuadro&idCuadro=CE125&sector=1&locale=es

Cada serie se consulta con la API REST del SIE:
https://www.banxico.org.mx/SieAPIRest/service/v1/series/{idSerie}/datos
"""

# -----------------------------------------------------------------------------
# Series de la Balanza Comercial (mensual, miles de USD) - cuadro CE125
# -----------------------------------------------------------------------------
SERIES = {
    # ---- EXPORTACIONES ----
    "SE36593": {"nombre": "Exportaciones totales",            "flujo": "exportacion", "grupo": "total"},
    "SE32150": {"nombre": "Exportaciones petroleras",         "flujo": "exportacion", "grupo": "petrolero"},
    "SE36566": {"nombre": "Exp. petroleo crudo",              "flujo": "exportacion", "grupo": "petrolero"},
    "SE32149": {"nombre": "Exp. petroleras - otras",          "flujo": "exportacion", "grupo": "petrolero"},
    "SE35397": {"nombre": "Exportaciones no petroleras",      "flujo": "exportacion", "grupo": "no_petrolero"},
    "SE33538": {"nombre": "Exp. agropecuarias",               "flujo": "exportacion", "grupo": "industria"},
    "SE30348": {"nombre": "Exp. extractivas",                 "flujo": "exportacion", "grupo": "industria"},
    "SE35398": {"nombre": "Exp. manufactureras",              "flujo": "exportacion", "grupo": "industria"},

    # ---- IMPORTACIONES ----
    "SE36595": {"nombre": "Importaciones totales",            "flujo": "importacion", "grupo": "total"},
    "SE32189": {"nombre": "Importaciones petroleras",         "flujo": "importacion", "grupo": "petrolero"},
    "SE35399": {"nombre": "Importaciones no petroleras",      "flujo": "importacion", "grupo": "no_petrolero"},
    "SE36597": {"nombre": "Imp. bienes de consumo",           "flujo": "importacion", "grupo": "uso"},
    "SE30373": {"nombre": "Imp. consumo petroleras",          "flujo": "importacion", "grupo": "uso"},
    "SE30374": {"nombre": "Imp. consumo no petroleras",       "flujo": "importacion", "grupo": "uso"},
    "SE36598": {"nombre": "Imp. bienes de uso intermedio",    "flujo": "importacion", "grupo": "uso"},
    "SE35400": {"nombre": "Imp. intermedio petroleras",       "flujo": "importacion", "grupo": "uso"},
    "SE35401": {"nombre": "Imp. intermedio no petroleras",    "flujo": "importacion", "grupo": "uso"},
    "SE36599": {"nombre": "Imp. bienes de capital",           "flujo": "importacion", "grupo": "uso"},

    # ---- BALANZA ----
    "SE28294": {"nombre": "Balanza comercial total",          "flujo": "balanza", "grupo": "balanza"},
    "SE35402": {"nombre": "Balanza sin exp. petroleras",      "flujo": "balanza", "grupo": "balanza"},
    "SE36600": {"nombre": "Balanza comercial petrolera",      "flujo": "balanza", "grupo": "balanza"},
    "SE35403": {"nombre": "Balanza comercial no petrolera",   "flujo": "balanza", "grupo": "balanza"},
}

# Agrupaciones utiles para el dashboard / analisis
INDUSTRIAS_EXPORTACION = {
    "Agropecuarias":  "SE33538",
    "Extractivas":    "SE30348",
    "Manufactureras": "SE35398",
    "Petroleras":     "SE32150",
}

IMPORTACION_POR_USO = {
    "Bienes de consumo":       "SE36597",
    "Bienes de uso intermedio":"SE36598",
    "Bienes de capital":       "SE36599",
}

TOTALES = {
    "Exportaciones totales": "SE36593",
    "Importaciones totales": "SE36595",
    "Balanza comercial":     "SE28294",
}

def todas_las_series():
    return list(SERIES.keys())
