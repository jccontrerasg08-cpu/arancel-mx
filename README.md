# arancel-mx

[![CI](https://github.com/jccontrerasg08-cpu/arancel-mx/actions/workflows/ci.yml/badge.svg)](https://github.com/jccontrerasg08-cpu/arancel-mx/actions)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue?logo=python&style=flat-square)](https://www.python.org)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

Herramientas abiertas en Python para capturar, normalizar, reconciliar y publicar datos arancelarios de México con procedencia verificable.

---

<!-- demo -->
<p align="center">
  <img alt="arancel-mx demo" src="docs/demo.gif" style="max-width:100%; border-radius:8px; box-shadow:0 8px 30px rgba(2,6,23,0.6)" />
</p>

## Resumen rápido ##

- Audita y materializa la LIGIE / NICO en una base DuckDB reproducible
- Normaliza códigos HS y tasas, conserva procedencia legal y evidencia
- Exporta artefactos deterministas: CSV, JSON, DuckDB y manifiesto con SHA256

## Por qué es diferente ##

- Procedencia: cada fila conserva la evidencia documental y el origen (DOF / SNICE / Diputados)
- Determinismo: exportaciones reproducibles con manifiestos y sumas de verificación
- Auditable: flujos de descubrimiento, captura, reconciliación y validación

## Características principales ##

- Parsers offline de XLS/XLSX/PDF para LIGIE y NICO
- Normalización canónica de códigos y tarifas
- Consolidación y versionado determinista de registros
- Flujos para capturar fuentes, verificar DOF y construir releases verificables

## Instalación rápida ##

```bash
python -m venv .venv
# PowerShell: .\.venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -e ".[dev]"
```

## Uso rápido (CLI) ##

```bash
# ver ayuda
python -m arancel_mx --help

# exportar artefactos desde una base DuckDB ya validada
python -m arancel_mx build --database data/arancel.duckdb --output-dir out/release

# actualizar estado desde el ledger oficial (requiere red)
python -m arancel_mx update --state-path data/update_state/ligie.json --report-path out/update.json

# reconciliar evidencia
python -m arancel_mx reconcile --ledger-json ledger.json --dof-json dof.json --snice-json snice.json

# preparar artefactos locales para publicación
python -m arancel_mx release --release-dir out/release --source-dir data/raw/release --latest-dir out/latest
```

## Documentación y ejemplos ##

- docs/: modelo de datos, proceso de publicación y guías de fuentes
- tests/: fixtures y casos de prueba que aseguran reproducibilidad

## Fuentes oficiales y URLs registradas ##

El registro versionado de fuentes está en `src/arancel_mx/sources/source_registry.json`. Fuentes principales:

- Diputados — LIGIE (registro y texto vigente): https://www.diputados.gob.mx/LeyesBiblio/ref/ligie_2022.htm
- SNICE — índice LIGIE / publicaciones oficiales: https://www.snice.gob.mx/cs/avi/snice/ligie.info22.html
- SNICE — NICO / identificaciones comerciales: https://www.snice.gob.mx/cs/avi/snice/ligie.nico2022.html
- SNICE — Propuestas NICO (envíos y solicitudes): https://www.snice.gob.mx/cs/avi/snice/ligie.nico2022.html
- SNICE — Notas nacionales: https://www.snice.gob.mx/cs/avi/snice/ligie.notasnac22.html
- SNICE — Indicadores ponderados: https://www.snice.gob.mx/cs/avi/snice/ligie.indicaranc22.html
- Diario Oficial de la Federación (DOF) — nota relacionada (publicación NICO 2022): https://www.dof.gob.mx/nota_detalle.php?codigo=5656249&fecha=27/06/2022

## Proceso y calendario (visual) ##

Las autoridades publican cronogramas y procedimientos asociados a la recepción, evaluación y publicación de solicitudes (NICO / reformas). A continuación se incluyen ilustraciones oficializadas que muestran el calendario de recepción/publicación y el flujo de envío y publicación de NICO/DOF.

<p align="center">
  <img alt="Calendario de publicaciones DOF y plazos" src="docs/dof_timeline2.png" style="max-width:85%; border-radius:6px; box-shadow:0 6px 20px rgba(0,0,0,0.25)" />
</p>
<p align="center">
  <img alt="Calendario de publicaciones DOF y plazos" src="docs/dof_timeline.png" style="max-width:85%; border-radius:6px; box-shadow:0 6px 20px rgba(0,0,0,0.25)" />
</p>

<p align="center">
  <em>Fuente: Diario Oficial de la Federación / SNICE — ver la nota oficial en DOF para detalles y fechas exactas.</em>
</p>

<p align="center">
  <img alt="Flujo de publicación NICO y DOF" src="docs/nico_flow.png" style="max-width:85%; border-radius:6px; box-shadow:0 6px 20px rgba(0,0,0,0.25)" />
</p>

Ver también `src/arancel_mx/sources/source_registry.json` para patrones de fichero y reglas de clasificación.

## Buenas prácticas para contribuciones ##

1. Abrir un issue describiendo el cambio o el bug
2. Crear una rama con nombre descriptivo (ej.: `feat/add-source-dof`) 
3. Añadir tests y fixtures offline cuando el cambio afecta parsers o transformaciones
4. Mantener trazabilidad de las fuentes (capture manifests y hashes)

Ejecuta las pruebas antes de proponer PRs

```bash
python -m pytest -q
python -m build
```

## Contribución / contacto ##

- Lee CONTRIBUTING.md y SECURITY.md antes de enviar PRs
- Usa issues para discutir cambios grandes o nuevos orígenes

## Licencia ##

Este proyecto se distribuye bajo la licencia Apache‑2.0. Consulta LICENSE y NOTICE para atribuciones.

##Agradecimientos##

Gracias a los equipos que publican y mantienen las fuentes oficiales (Diputados, SNICE, DOF) y a la comunidad de código abierto por sus plantillas y prácticas de documentación.
