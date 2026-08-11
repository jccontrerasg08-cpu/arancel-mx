<div align="center">

<img src="docs/assets/arancel-mx-banner.svg" alt="arancel-mx - datos arancelarios de México reproducibles, auditables y trazables" width="100%" />

# arancel-mx

### Datos arancelarios de México reproducibles, auditables y trazables

Herramientas abiertas en Python y releases de datos para LIGIE, fracciones MX8 y NICO10 con procedencia verificable.

<strong>Español</strong> · <a href="./README.en.md">English</a>

[![CI](https://github.com/jccontrerasg08-cpu/arancel-mx/actions/workflows/ci.yml/badge.svg)](https://github.com/jccontrerasg08-cpu/arancel-mx/actions)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue?logo=python&style=flat-square)](https://www.python.org)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![DuckDB](https://img.shields.io/badge/DuckDB-embedded-FFF000?logo=duckdb&logoColor=000)](https://duckdb.org/)

**[Empieza aquí](docs/getting-started.md)** · **[Verificar release](docs/verify-release.md)** · **[CLI](docs/cli.md)** · **[Dataset](docs/dataset.md)** · **[Fuentes](docs/sources.md)** · **[Soporte](SUPPORT.md)**

</div>

<div align="center">

## Última versión del dataset

**Descarga siempre la release pública más reciente de `arancel-mx`.**

**[DuckDB](https://github.com/jccontrerasg08-cpu/arancel-mx/releases/latest/download/arancel_mx.duckdb)** ·
**[CSV](https://github.com/jccontrerasg08-cpu/arancel-mx/releases/latest/download/arancel_mx.csv)** ·
**[JSON](https://github.com/jccontrerasg08-cpu/arancel-mx/releases/latest/download/arancel_mx.json)** ·
[Manifest](https://github.com/jccontrerasg08-cpu/arancel-mx/releases/latest/download/manifest.json) ·
[SHA256SUMS](https://github.com/jccontrerasg08-cpu/arancel-mx/releases/latest/download/SHA256SUMS) ·
[Fuentes oficiales](https://github.com/jccontrerasg08-cpu/arancel-mx/releases/latest/download/official-sources.tar.gz) ·
**[Ver release](https://github.com/jccontrerasg08-cpu/arancel-mx/releases/latest)**

<sub>Los enlaces `/releases/latest/download/...` apuntan automáticamente a los assets de la release pública marcada como más reciente.</sub>

</div>

---

<p align="center">
  <img alt="arancel-mx demo" src="docs/demo.gif" style="max-width:100%" />
</p>

## En 30 segundos

`arancel-mx` construye y publica una capa de datos abierta para la clasificación arancelaria mexicana. El pipeline captura fuentes oficiales, conserva hashes y tiempos reales de recuperación, reconcilia evidencia jurídica, valida la jerarquía HS2 → HS4 → HS6 → MX8 → NICO10 y sólo publica un cambio cuando todos los gates pasan.

Puedes usar el dataset **sin instalar Python** descargando CSV, JSON o DuckDB desde una release `data-YYYY.MM.DD`. Si quieres usar el CLI desde un checkout, ve a [`docs/getting-started.md`](docs/getting-started.md). Para comprobar una descarga de forma independiente, usa [`docs/verify-release.md`](docs/verify-release.md). Para preguntas o errores, consulta [`SUPPORT.md`](SUPPORT.md). Para citar el proyecto, usa [`CITATION.cff`](CITATION.cff).

> [!IMPORTANT]
> `arancel-mx` es una herramienta técnica y de datos. **No constituye asesoría legal.** Para decisiones de clasificación arancelaria, cumplimiento, importación o exportación consulta las fuentes oficiales aplicables y, cuando corresponda, profesionales especializados.

## Alcance

El proyecto público se enfoca en datos, procedencia documental, validación, DuckDB y artefactos reproducibles. No pretende reemplazar un sistema comercial completo de comercio exterior.

Licencia del proyecto: **Apache-2.0**.

### Qué publica

Una release válida contiene exactamente seis assets:

```text
arancel_mx.duckdb
arancel_mx.csv
arancel_mx.json
manifest.json
SHA256SUMS
official-sources.tar.gz
```

`manifest.json` conserva versión, conteos, reconciliación y procedencia. `SHA256SUMS` cubre los otros cinco assets. `official-sources.tar.gz` preserva los bytes oficiales capturados y `source_capture.json`.

## Arquitectura

```text
fuentes oficiales → captura → reconciliación legal → parseo → validación
→ sin cambios: termina en verde
→ cambio válido: release inmutable verificado
→ cualquier fallo: bloquea la publicación + GitHub Issue
```

Componentes principales:

```text
Diputados / DOF / SNICE
          ↓
 source_registry + discovery
          ↓
 capture + source_capture.json
          ↓
 SHA256 + retrieved_at
          ↓
 reconciliación legal
          ↓
 parsers offline XLS/XLSX/PDF
          ↓
 normalización + validación
          ↓
 DuckDB canónico → CSV / JSON / manifest.json
          ↓
 verified six-asset bundle
          ↓
 GitHub Release data-YYYY.MM.DD
```

<p align="center">
  <img src="docs/assets/pipeline.svg" alt="Pipeline de fuentes oficiales a release" width="950" />
</p>

## Instalación

### Consumidor del CLI

Mientras no exista publicación en PyPI, instala desde un checkout normal, no editable:

```bash
git clone https://github.com/jccontrerasg08-cpu/arancel-mx.git
cd arancel-mx
python -m venv .venv
# PowerShell: .\.venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install .
python -m arancel_mx --help
```

### Desarrollo y reproducción de CI

Los builds oficiales usan el entorno exacto definido por `requirements/production-build.txt`:

```bash
python -m pip install pip==26.2.1
python -m pip install -c requirements/production-build.txt -e ".[dev]"
```

La política es intencional: rangos compatibles en `pyproject.toml` para consumidores y pins exactos para CI/producción.

## Uso rápido CLI

```bash
python -m arancel_mx --help
python -m arancel_mx build --database data/arancel.duckdb --output-dir out/release
python -m arancel_mx check-updates --state-path data/update_state/ligie.json --report-path out/update.json
python -m arancel_mx reconcile --ledger-json ledger.json --dof-json dof.json --snice-json snice.json
python -m arancel_mx release --release-dir out/release --source-dir data/raw/release --latest-dir out/latest
```

Los comandos públicos preferidos son `build`, `check-updates`, `reconcile` y `release`. Durante 0.x, `update` permanece como alias obsoleto y read-only de `check-updates`.

Más detalle: [`docs/cli.md`](docs/cli.md).

## Uso desde Python

```python
import arancel_mx

print(arancel_mx.__version__)
```

La API pública de búsqueda y navegación todavía es roadmap. No se presentan interfaces internas como API estable. Consulta [`docs/python-api.md`](docs/python-api.md).

## Modelo de datos

Los niveles públicos son `hs2`, `hs4`, `hs6`, `fraccion8` y `nico10`. Una fracción requiere su padre HS6 y un NICO su fracción MX8. Las filas HS descriptivas no heredan tarifas de forma artificial.

DuckDB separa clasificación, tasas, vigencia y procedencia. Consulta [`docs/data-model.md`](docs/data-model.md) y [`docs/hs-mx-nico.md`](docs/hs-mx-nico.md).

## Fuentes oficiales

El registro versionado vive en `src/arancel_mx/sources/source_registry.json`.

Roles actuales:

- **DOF**: evidencia de publicación jurídica y vigencia aplicable.
- **Diputados**: ledger/compilación legislativa y texto consolidado registrado.
- **SNICE**: datasets estructurados de LIGIE, NICO, notas, indicadores y publicaciones relacionadas.
- **VUCEM**: se caracteriza por separado como cross-check operativo y todavía no es autoridad arancelaria ni publication gate.

Fuentes principales registradas:

- Diputados, LIGIE: https://www.diputados.gob.mx/LeyesBiblio/ref/ligie_2022.htm
- SNICE, LIGIE: https://www.snice.gob.mx/cs/avi/snice/ligie.info22.html
- SNICE, NICO y propuestas NICO: https://www.snice.gob.mx/cs/avi/snice/ligie.nico2022.html
- SNICE, notas nacionales: https://www.snice.gob.mx/cs/avi/snice/ligie.notasnac22.html
- SNICE, indicadores: https://www.snice.gob.mx/cs/avi/snice/ligie.indicaranc22.html
- Diario Oficial de la Federación: https://www.dof.gob.mx/nota_detalle.php?codigo=5656249&fecha=27/06/2022

Consulta [`docs/sources.md`](docs/sources.md), [`docs/provenance.md`](docs/provenance.md) y [`docs/vucem-characterization.md`](docs/vucem-characterization.md).

## Pipeline oficial autónomo

El workflow **Official data pipeline** vive en [`.github/workflows/official-data-pipeline.yml`](.github/workflows/official-data-pipeline.yml).

- Cron: `17 11 * * *`, una **revisión diaria automatizada** en UTC.
- `no_change`: termina en verde y no crea release redundante.
- **publicación automática**: sólo cuando existe un cambio válido y verificado.
- **cualquier falla bloquea la publicación** y expone diagnóstico para un GitHub Issue.
- `contents: write` sólo existe en el job publisher.
- `issues: write` sólo existe en el notifier.

El entrypoint público end-to-end permanece en `scripts/build_official_dataset.py`; `scripts/run_official_pipeline.py` añade detección de cambios y diagnóstico estructurado.

## Reproducibilidad y verificación

La representación lógica entre DuckDB, CSV y JSON se certifica independientemente. El archivo físico DuckDB se verifica por SHA256 para una construcción concreta, sin prometer identidad byte a byte entre procesos independientes.

CI también prueba instalación limpia de wheel y sdist fuera del checkout. La política de pins está en [`docs/reproducibility.md`](docs/reproducibility.md) y el procedimiento de consumidor en [`docs/verify-release.md`](docs/verify-release.md).

El proyecto conserva **capture manifests y hashes**. Una release puede relacionarse con las capturas concretas que la originaron.

La documentación web usa Docusaurus con dependencias fijadas por `website/package-lock.json`. `.github/workflows/docs-ci.yml` ejecuta `npm ci`, typecheck y builds independientes para español e inglés con permisos de solo lectura.

## Proceso y calendario visual

### Calendario DOF, parte 1

<img alt="Calendario DOF parte 1" src="docs/dof_timeline.png" width="85%" />

### Calendario DOF, parte 2

<img alt="Calendario DOF parte 2" src="docs/dof_timeline2.png" width="85%" />

### Flujo NICO / DOF

<img alt="Flujo NICO y DOF" src="docs/nico_flow.png" width="85%" />

Estas imágenes son contexto documental, no indicadores dinámicos de vigencia.

## Estructura del repositorio

```text
.github/        workflows, templates, CODEOWNERS, Dependabot
requirements/   entorno productivo exacto
src/arancel_mx/ paquete Python
scripts/        build, publicación, certificación y utilidades
docs/           documentación pública y de ingeniería
tests/          tests offline y contratos de producción
website/         sitio Docusaurus y lockfile npm reproducible
LICENSE
NOTICE
CITATION.cff
SUPPORT.md
```

Los datos generados, snapshots, bases locales y tokens permanecen fuera de Git.

## Pruebas

```bash
python -m pytest -q
python -m build
git diff --check
```

El required check de `main` es `test`. Un PR normal no publica releases ni ejecuta live-update de fuentes.

## Seguridad y comunidad

Las contribuciones de la **comunidad de código abierto** son bienvenidas. Lee [`CONTRIBUTING.md`](CONTRIBUTING.md), [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md), [`SECURITY.md`](SECURITY.md), [`SUPPORT.md`](SUPPORT.md), `LICENSE`, `NOTICE` y [`CITATION.cff`](CITATION.cff).

Las Actions externas se fijan por SHA completo. El pipeline usa permisos por job, no `write-all`, y no necesita PAT para publicar releases.

## Estado del proyecto

| Capacidad | Estado |
|---|---|
| Parsers XLS/XLSX/PDF | Disponible |
| Normalización y jerarquía | Disponible |
| DuckDB + CSV + JSON | Disponible |
| Source registry y procedencia | Disponible |
| Reconciliación legal bloqueante | Disponible |
| Detección `no_change` | Disponible |
| Publicación automática verificada | Disponible |
| GitHub Issue alerts y recovery | Disponible |
| Caracterización VUCEM no autoritativa | Disponible |
| Docusaurus ES/EN + CI read-only | Disponible en esta rama, pendiente de despliegue |
| API de búsqueda estable | Roadmap |
| Publicación en PyPI | Roadmap |

## Operación del repositorio

La configuración objetivo de Actions, releases, rulesets y seguridad está documentada en [`docs/operations/github-settings.md`](docs/operations/github-settings.md).

## Notas de procedencia

La presencia de un documento o registro describe evidencia técnica observada. No sustituye la publicación oficial ni una interpretación jurídica especializada.
