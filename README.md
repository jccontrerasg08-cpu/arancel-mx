# arancel-mx

[![CI](https://github.com/jccontrerasg08-cpu/arancel-mx/actions/workflows/ci.yml/badge.svg)](https://github.com/jccontrerasg08-cpu/arancel-mx/actions)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue?logo=python&style=flat-square)](https://www.python.org)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)

Herramientas abiertas en Python para capturar, normalizar, reconciliar y publicar datos arancelarios de México con procedencia verificable.

---

## Demo & animaciones

Se puede mejorar la portada con una pequeña animación o GIF que muestre el uso de la CLI (ej.: un corto GIF que muestre `python -m arancel_mx build ...`) y badges animados. Para mantener el repositorio ligero y reproducible, aquí hay pasos recomendados y un marcador de posición:

- Generar una grabación de terminal con asciinema y convertirla en GIF:

```bash
# grabar terminal (requiere asciinema)
asciinema rec demo.cast --command "python -m arancel_mx build --database data/arancel.duckdb --output-dir out/release"
# convertir a GIF (requiere asciinema2gif / ffmpeg / imagemagick)
asciinema2gif demo.cast docs/demo.gif
```

- Alternativa: usar terminalizer para grabar y exportar GIF.

- Subir el GIF a `docs/demo.gif` y reemplazar la referencia siguiente por la ruta local:

```markdown
![Demo de arancel-mx](docs/demo.gif)
```

Si prefieres, puedo generar y añadir un GIF de ejemplo automáticamente y/o configurar una GitHub Action que convierta grabaciones `.cast` a GIF en cada release. Indica si quieres que lo añada.

---

## Propósito

El proyecto convierte documentos oficiales de la LIGIE y NICO en registros normalizados, una base DuckDB consultable y artefactos deterministas con manifiestos y sumas SHA-256.

## Alcance

`arancel-mx` se limita al dominio arancelario: jerarquía HS, fracciones de ocho dígitos, NICO, tasas de importación y exportación, vigencia, evidencia legal y procedencia. No pretende cubrir toda la operación de comercio exterior.

## Estado del proyecto

El paquete está en desarrollo inicial (`0.x`). Las interfaces, el esquema y los artefactos pueden cambiar hasta una versión estable. Los cambios se revisan mediante issues y pull requests públicos.

## Fuentes oficiales y aviso sobre los datos

La Cámara de Diputados, el Diario Oficial de la Federación y la Secretaría de Economía/SNICE son las fuentes oficiales principales. El registro versionado está incluido en `src/arancel_mx/sources/source_registry.json`.

Fuentes registradas (URLs)

- diputados_ligie — Cámara de Diputados (registro LIGIE): https://www.diputados.gob.mx/LeyesBiblio/ref/ligie_2022.htm
- ligie — SNICE (índice LIGIE / publicaciones oficiales): https://www.snice.gob.mx/cs/avi/snice/ligie.info22.html
- nico — SNICE (NICO / identificaciones comerciales): https://www.snice.gob.mx/cs/avi/snice/ligie.nico2022.html
- nico_proposals — SNICE (propuestas y solicitudes NICO): https://www.snice.gob.mx/cs/avi/snice/ligie.nico2022.html
- national_notes — SNICE (Notas nacionales y contexto): https://www.snice.gob.mx/cs/avi/snice/ligie.notasnac22.html
- weighted_tariff_indicators — SNICE (indicadores ponderados y metodologías): https://www.snice.gob.mx/cs/avi/snice/ligie.indicaranc22.html

Puedes consultar `src/arancel_mx/sources/source_registry.json` para ver el registro completo, las familias de archivos esperadas y las reglas de clasificación por nombre de fichero.

Este proyecto es independiente y no está afiliado ni respaldado por una autoridad mexicana. Los datos generados pueden contener errores o quedar desactualizados. Su contenido es informativo y no constituye asesoría legal, aduanera, fiscal ni profesional. Verifica siempre la publicación oficial aplicable.

## Instalación

Requiere Python 3.11 o posterior.

```bash
python -m venv .venv
python -m pip install -e ".[dev]"
```

En PowerShell puedes activar el entorno con `.\.venv\Scripts\Activate.ps1`; en Linux o macOS, con `source .venv/bin/activate`.

## Inicio rápido de la CLI

```bash
python -m arancel_mx --help

# Exportar una base DuckDB ya validada
python -m arancel_mx build --database data/arancel.duckdb --output-dir out/release

# Comparar el ledger oficial con el último estado local
python -m arancel_mx update --state-path data/update_state/ligie.json --report-path out/update.json

# Reconciliar tres conjuntos de evidencia JSON
python -m arancel_mx reconcile --ledger-json ledger.json --dof-json dof.json --snice-json snice.json

# Verificar y preparar artefactos locales de publicación
python -m arancel_mx release --release-dir out/release --source-dir data/raw/release --latest-dir out/latest
```

La comprobación `update` consulta una página oficial. Las pruebas y la construcción del paquete no requieren red.

## Uso desde Python

```python
from arancel_mx.sources import load_source_registry

registry = load_source_registry()
for entry in registry:
    print(entry.dataset_key, entry.canonical_page)
```

Las APIs de normalización están en `arancel_mx.domain`; las de captura y descubrimiento en `arancel_mx.sources`; y los flujos de materialización en `arancel_mx.pipeline`.

## Estructura del repositorio

```text
src/arancel_mx/domain/    Modelo y normalización canónica
src/arancel_mx/sources/   Registro, captura y adaptadores oficiales
src/arancel_mx/parsers/   Lectores offline de XLS/XLSX/PDF
src/arancel_mx/storage/   Esquema DuckDB arancelario
src/arancel_mx/pipeline/  Construcción, conciliación y actualización
src/arancel_mx/release/   Verificación y empaquetado local
tests/                    Pruebas y fixtures deterministas
docs/                     Modelo, fuentes y proceso de publicación
```

## Pruebas

```bash
python -m pytest -q
python -m build
git diff --check
```

## Seguridad

No publiques credenciales, datos personales ni documentos privados. Reporta vulnerabilidades según [SECURITY.md](SECURITY.md).

## Contribuir

Se aceptan issues, forks y pull requests. Lee [CONTRIBUTING.md](CONTRIBUTING.md) y conserva procedencia, hashes y fixtures offline al modificar fuentes o parsers.

## Licencia

El código original se distribuye bajo [Apache-2.0](LICENSE). Consulta [NOTICE](NOTICE) para atribución y avisos sobre fuentes.

## Atribución

Los documentos y datos oficiales pertenecen a sus autoridades de origen y conservan sus condiciones aplicables. Su referencia no implica respaldo de ninguna autoridad.
