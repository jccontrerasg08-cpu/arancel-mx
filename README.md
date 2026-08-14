<div align="center">

<img src="docs/assets/arancel-mx-banner.svg" alt="arancel-mx - datos arancelarios de México reproducibles, auditables y trazables" width="100%" />

# arancel-mx

### Datos arancelarios de México, reproducibles, auditables y trazables

Herramientas abiertas en Python para capturar, normalizar, reconciliar y publicar datos arancelarios de México con procedencia verificable.

<p>
  <strong>Español</strong> · <a href="./README.en.md">English</a>
</p>

[![CI](https://github.com/jccontrerasg08-cpu/arancel-mx/actions/workflows/ci.yml/badge.svg)](https://github.com/jccontrerasg08-cpu/arancel-mx/actions)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue?logo=python&style=flat-square)](https://www.python.org)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![DuckDB](https://img.shields.io/badge/DuckDB-embedded-FFF000?logo=duckdb&logoColor=000)](https://duckdb.org/)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

**[Instalación](#instalación)** · **[CLI](#uso-rápido-cli)** · **[Python](#uso-desde-python)** · **[Consumo externo](docs/external-consumption.md)** · **[Datos](#modelo-de-datos)** · **[Fuentes](#fuentes-oficiales)** · **[Automatización](#pipeline-oficial-autónomo)** · **[Certificación](docs/production-certification.md)** · **[Contribuir](#contribución)**

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

<sub>Los enlaces `/releases/latest/download/...` apuntan automáticamente a los assets de la release pública marcada como más reciente. GitHub muestra el tamaño de cada asset en esa página; la identidad es `SHA256SUMS`, no el megabyte.</sub>

</div>

```bash
sha256sum -c SHA256SUMS
```

---

<p align="center">
  <img alt="arancel-mx demo" src="docs/demo.gif" style="max-width:100%; border-radius:8px; box-shadow:0 8px 30px rgba(2,6,23,0.6)" />
</p>

<p align="center"><strong>Captura · Reconcilia · Normaliza · Valida · Publica</strong></p>

---

## Alcance

`arancel-mx` es un proyecto público enfocado en construir una capa de datos abierta, reproducible y auditable para la LIGIE, NICO y sus fuentes oficiales. El núcleo público prioriza datos, procedencia documental, validación, DuckDB y artefactos reproducibles; no pretende reemplazar un sistema comercial completo de comercio exterior.

Licencia del proyecto: **Apache-2.0**.

> [!IMPORTANT]
> `arancel-mx` es una herramienta técnica y de datos. **No constituye asesoría legal.** Para decisiones de clasificación arancelaria, cumplimiento regulatorio, importación o exportación deben consultarse las fuentes oficiales aplicables y, cuando corresponda, profesionales especializados.

## Resumen rápido

- Captura snapshots registrados de Diputados, DOF y SNICE con SHA256 y `retrieved_at` real.
- Reconcilia evidencia legal antes de permitir que un candidato sea publicable.
- Normaliza HS2, HS4, HS6, fracción MX de 8 dígitos y NICO de 10 dígitos.
- Materializa un warehouse DuckDB y exporta CSV, JSON y manifest schema v2.
- Detecta `no_change` sin crear releases redundantes.
- Ejecuta una **revisión diaria automatizada** y hace **publicación automática** sólo cuando el dataset cambió y todos los gates pasaron.
- Abre o actualiza un **GitHub Issue** cuando cualquier stage de producción falla.
- Usa releases `data-YYYY.MM.DD` y un contrato exacto de seis assets verificables.
- Mantiene una certificación manual aislada para probar permisos de release/Issue y verificar rollback sin tocar releases `data-*`.

## Por qué es diferente

| Propiedad | Cómo se implementa |
|---|---|
| Procedencia | Cada fuente conserva autoridad, URL, identidad, hash y tiempo de captura |
| Evidencia legal | El ledger de Diputados se reconcilia contra DOF y fuentes registradas |
| Fail-closed | Una discrepancia, parser dudoso o validación fallida bloquea publicación |
| Reproducibilidad | Dependencias de producción exactas y manifest schema v2 |
| Determinismo | Exportaciones canónicas, checksums y archive de fuentes |
| Auditabilidad | El release enlaza registry, commit, run de GitHub y artifact exacto |
| Recuperación | Alertas deterministas se cierran sólo tras una ejecución saludable posterior |

## De HS a fracción MX y NICO

```text
HS 2
  ↓
HS 4
  ↓
HS 6
  ↓
Fracción MX 8 dígitos
  ↓
NICO 10 dígitos
```

<p align="center">
  <img src="docs/assets/hs-mx-nico-flow.svg" alt="Flujo conceptual HS a fracción mexicana y NICO" width="900" />
</p>

La base valida relaciones padre-hijo para evitar que una fracción quede sin HS6 o que un NICO quede sin su fracción vigente.

## Arquitectura

```text
fuentes oficiales → captura → reconciliación legal → parseo → validación
→ sin cambios: termina en verde
→ cambio válido: release inmutable verificado
→ cualquier fallo: bloquea la publicación + GitHub Issue
```

En términos de componentes:

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
 DuckDB canónico
    ↙       ↓       ↘
  CSV      JSON    manifest.json
          ↓
 six-asset verified bundle
          ↓
 GitHub Release data-YYYY.MM.DD
```

<p align="center">
  <img src="docs/assets/pipeline.svg" alt="Pipeline de fuentes oficiales a DuckDB, CSV, JSON y release" width="950" />
</p>

## Instalación

Requiere Python 3.11 o superior.

### Consumo del dataset publicado

`arancel-mx==0.2.0` está publicado en PyPI (carga del 2026-08-12 vía Trusted Publishing). La matriz externa de SO/Python no fue un gate bloqueante de esa carga. `0.2.1` bloquea PyPI con Ubuntu/Windows/macOS × CPython 3.11–3.13 después de TestPyPI. La guía canónica para aplicaciones aguas abajo es [`docs/external-consumption.md`](docs/external-consumption.md).

```bash
pip install arancel-mx==0.2.0
arancel-mx --version
arancel-mx doctor
```

El paquete y los datasets se versionan por separado. Fijar el paquete no fija el dataset. `arancel-mx --version` muestra la versión del paquete Python; cada dataset usa una release inmutable `data-YYYY.MM.DD`.

### Desarrollo del repositorio

Para contribuir o ejecutar el pipeline desde el checkout:

```bash
python -m venv .venv
# PowerShell: .\.venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -e ".[dev]"
python -m arancel_mx --help
```

Los builds oficiales y CI usan el entorno reproducible definido por `requirements/production-build.txt`:

```bash
python -m pip install pip==26.2.1
python -m pip install -c requirements/production-build.txt -e ".[dev]"
```

## Consumo externo

Las aplicaciones aguas abajo deben fijar, instalar, verificar y consultar `arancel-mx` como paquete de datos. La guía canónica es [`docs/external-consumption.md`](docs/external-consumption.md).

## Uso rápido CLI

El flujo para consumidores parte del dataset publicado y no requiere clonar el repositorio:

```bash
arancel-mx doctor
arancel-mx data download
arancel-mx lookup 01012101
arancel-mx ficha 01012101
arancel-mx compare 01012101
arancel-mx chapters
arancel-mx search "refrigeradores"
arancel-mx data verify
```

Después de descargar y verificar una release, las consultas pueden operar en modo offline estricto:

```bash
arancel-mx lookup 01012101 --offline --format json
arancel-mx data verify --offline --format json
```

También se puede fijar una release exacta con `--dataset data-YYYY.MM.DD`. Consulta [`docs/consumer-cli.md`](docs/consumer-cli.md) para `data status/list/update/path/verify`, formatos JSON/CSV, variables de entorno, integridad del cache y el contrato de `doctor`.

### Comandos para consumidores

| Comando | Uso |
|---|---|
| `doctor` | Diagnostica instalación, cache, dataset, DuckDB y acceso remoto |
| `data download` | Descarga y promueve al cache sólo una release verificada |
| `data status` / `data list` | Muestra versiones locales y, cuando se solicita, releases remotas válidas |
| `data update` | Descarga la release válida más reciente sin borrar versiones anteriores |
| `data path` | Imprime únicamente la ruta del DuckDB seleccionado |
| `data verify` | Revalida integridad local y opcionalmente el bundle remoto |
| `lookup` / `search` | Consulta por código exacto o texto |
| `ficha` | Ficha jerárquica capítulo → fracción/NICO con UM, IGI e IGE |
| `compare` | Diff HS6 / MX8 / NICO del dataset GitHub contra VUCEM (informativo) |
| `chapters` | Lista los capítulos HS2 vigentes |
| `parent` / `children` | Navega la jerarquía HS2 → HS4 → HS6 → MX8 → NICO10 |
| `provenance` | Muestra trazabilidad documental del código seleccionado |

### Comandos de mantenimiento del repositorio

Los mantenedores conservan los comandos de construcción y publicación:

```bash
# exportar artefactos desde una base DuckDB validada
python -m arancel_mx build --database data/arancel.duckdb --output-dir out/release

# revisar el ledger oficial y escribir un reporte de cambios
python -m arancel_mx check-updates --state-path data/update_state/ligie.json --report-path out/update.json

# reconciliar evidencia
python -m arancel_mx reconcile --ledger-json ledger.json --dof-json dof.json --snice-json snice.json

# verificar y preparar un bundle local
python -m arancel_mx release --release-dir out/release --source-dir data/raw/release --latest-dir out/latest
```

## Uso desde Python

```python
from arancel_mx import Dataset

dataset = Dataset.latest()
card = dataset.ficha("01012101")
print(card.formatted_code, card.record.description, card.record.igi_text)
for chapter in dataset.chapters():
    print(chapter.code, chapter.description)
```

`Dataset.open("arancel_mx.duckdb")` abre un archivo local ya validado estructuralmente. `ficha` y `chapters` usan el dataset oficial verificado; no scrapean SIICEX-CAAAREM ni dumps como tigies-mx.

## Modelo de datos

DuckDB separa clasificación, tasas, vigencia y procedencia. Las tablas principales incluyen `source_registry`, `source_document`, `hs_code`, `tariff_fraction`, `nico`, `tariff_rate`, `canonical_record`, `record_provenance` y `dataset_release`.

El manifest de release usa schema v2 y conserva, entre otros, `registry_sha256`, `git_commit_sha`, `github_run_id`, `github_run_attempt`, `github_workflow_ref` y `github_artifact_name`.

Consulta [`docs/data-model.md`](docs/data-model.md) para la semántica de `retrieved_at`, `generated_at` y `dataset_release.release_metadata_json`.

## Artefactos y reproducibilidad

Una release pública válida contiene exactamente:

```text
release/
├── arancel_mx.duckdb
├── arancel_mx.csv
├── arancel_mx.json
├── manifest.json
├── SHA256SUMS
└── official-sources.tar.gz
```

`manifest.json` conserva versión, procedencia, reconciliación, conteos y hashes. `SHA256SUMS` cubre los otros cinco assets. `official-sources.tar.gz` conserva los bytes oficiales capturados y su `source_capture.json`.

La representación lógica es reproducible. El archivo físico DuckDB se verifica por SHA256 para esa construcción concreta, sin asumir que dos archivos DuckDB creados por procesos distintos sean byte a byte idénticos.

## Construcción end-to-end de dataset oficial

El entrypoint público sigue disponible:

```bash
python scripts/build_official_dataset.py \
  --work-dir data/embedded/official-build \
  --output-dir out/release \
  --effective-as-of 2026-08-10 \
  --dataset-version 2026.08.10
```

Para producción, `scripts/run_official_pipeline.py` añade comparación contra el manifest anterior, diagnóstico estructurado y semántica `no_change`.

## Pipeline oficial autónomo

El workflow **Official data pipeline** está definido en [`.github/workflows/official-data-pipeline.yml`](.github/workflows/official-data-pipeline.yml).

- Schedule: `17 11 * * *`, una **revisión diaria automatizada** en UTC.
- `workflow_dispatch`: disponible para dry-run y ejecución mantenida; `publish=false` es el valor manual por defecto.
- Build: `contents: read` y tests offline antes de tocar la red.
- Publish: `contents: write` sólo si `main` produjo `built` y la ejecución está autorizada para mutar.
- Notify: `issues: write` únicamente para el lifecycle de alertas.
- Canario: [`.github/workflows/published-bundle-canary.yml`](.github/workflows/published-bundle-canary.yml) (`47 12 * * *`) verifica el contrato público de seis assets; `contents: read`, sin extras `[hs]`/`[dev]`.

La **publicación automática** ocurre sólo para un cambio válido y verificado. **Cualquier falla bloquea la publicación**. Si no hubo cambios, `no_change` termina en verde y el publisher queda `skipped`.

Antes de publicar, el bundle se verifica localmente, se vuelve a verificar después de descargar el artifact y se sube a una release draft. Los seis assets remotos se comprueban antes de hacer pública la release. Un tag `data-YYYY.MM.DD` existente nunca se sobrescribe.

Consulta [`docs/release-process.md`](docs/release-process.md) para el contrato exacto y [`docs/production-certification.md`](docs/production-certification.md) para el runbook de certificación de permisos y rollback.

## Fuentes oficiales

El registro versionado vive en `src/arancel_mx/sources/source_registry.json`.

Fuentes principales:

- [Diputados, LIGIE](https://www.diputados.gob.mx/LeyesBiblio/ref/ligie_2022.htm)
- [SNICE, LIGIE](https://www.snice.gob.mx/cs/avi/snice/ligie.info22.html)
- [SNICE, NICO y propuestas NICO](https://www.snice.gob.mx/cs/avi/snice/ligie.nico2022.html)
- [SNICE, notas nacionales](https://www.snice.gob.mx/cs/avi/snice/ligie.notasnac22.html)
- [SNICE, indicadores](https://www.snice.gob.mx/cs/avi/snice/ligie.indicaranc22.html)
- [Diario Oficial de la Federación, publicación relacionada](https://dof.gob.mx/nota_detalle.php?codigo=5656249&fecha=27/06/2022)

`docs/sources.md` explica cómo el ledger registrado de Diputados se usa como ancla y cómo la evidencia DOF participa como gate antes de publicar. SIICEX-CAAAREM y dumps como tigies-mx no son fuentes oficiales.

## Proceso y calendario visual

### Calendario DOF, parte 1

<p align="center">
  <img alt="Calendario de publicaciones DOF y plazos, parte 1" src="docs/dof_timeline.png" style="max-width:85%" />
</p>

### Calendario DOF, parte 2

<p align="center">
  <img alt="Calendario de publicaciones DOF y plazos, parte 2" src="docs/dof_timeline2.png" style="max-width:85%" />
</p>

### Flujo NICO / DOF

<p align="center">
  <img alt="Flujo de publicación NICO y DOF" src="docs/nico_flow.png" style="max-width:85%" />
</p>

Estas imágenes son contexto documental y no un indicador dinámico del estado del dataset.

## Estructura del repositorio

```text
.github/
├── workflows/
│   ├── ci.yml
│   ├── official-data-pipeline.yml
│   ├── publish-python-package.yml
│   └── production-certification.yml
└── dependabot.yml
requirements/
└── production-build.txt
src/arancel_mx/
├── certification/
├── consumer/
├── domain/
├── parsers/
├── pipeline/
├── release/
├── sources/
│   └── source_registry.json
└── storage/
scripts/
├── build_official_dataset.py
├── run_official_pipeline.py
├── check_documented_urls.py
├── certify_package_install.py
├── check_duckdb_compat.py
├── certify_github_release.py
├── certify_github_issue.py
├── fetch_previous_release.py
├── publish_release.py
└── data_alert.py
docs/
tests/
LICENSE
NOTICE
```

El repositorio incluye pruebas de distribución que buscan credenciales y rutas privadas. Los datos generados, snapshots, DuckDB locales y tokens permanecen fuera de Git.

## Pruebas

```bash
python -m pytest -q
python -m build
git diff --check
```

El workflow se muestra como **CI** y el contexto exacto requerido por el ruleset de `main` es **`test`**. Un PR normal no hace live-update de fuentes ni publica releases.

La certificación live de permisos GitHub se ejecuta aparte mediante el workflow manual **Production certification**. El run `31450616908` sobre `a14c57ee3aeeb982e6aa7077ae1b34582585db8b` terminó verde y dejó cero drafts/tags de certificación; consulta [`docs/production-certification.md`](docs/production-certification.md).

## Seguridad y supply chain

- Actions externas fijadas por SHA completo.
- Dependencias de producción restringidas por `requirements/production-build.txt`.
- Dependabot abre PRs semanales para Python y GitHub Actions.
- El pipeline de producción usa permisos por job, no `write-all`.
- No usa PAT para releases.
- La certificación de write-boundaries usa namespaces `certification-*` y `[CERTIFICATION ALERT]`, separados de producción.

El runbook de configuración de producción está en [`docs/operations/github-settings.md`](docs/operations/github-settings.md). Ahí se documentan release immutability, el ruleset de `main`, el required check `test`, permisos de Actions y controles de Advanced Security que deben verificarse en la UI.

Ver [`SECURITY.md`](SECURITY.md), [`CONTRIBUTING.md`](CONTRIBUTING.md) y [`docs/production-certification.md`](docs/production-certification.md).

## Estado del proyecto

| Capacidad | Estado |
|---|---|
| Parsers XLS/XLSX/PDF | Disponible |
| Normalización y jerarquía | Disponible |
| DuckDB + CSV + JSON | Disponible |
| Source registry | Disponible |
| Reconciliación legal bloqueante | Disponible |
| Manifest schema v2 | Disponible |
| Build oficial end-to-end | Disponible |
| Detección automática de cambios | Disponible |
| Publicación automática verificada | Disponible |
| GitHub Issue alerts y recovery | Disponible |
| Certificación live de release/Issue write-boundaries | Disponible |
| API de búsqueda estable | Disponible |
| Ficha TIGIE (`ficha` / `chapters`) | Disponible |
| Compare HS6 / MX8 / NICO vs VUCEM | Disponible (informativo, no identidad legal) |
| Notas nacionales LIGIE | Parser y vista `arancel_mx_national_notes`; el snapshot actual puede dejarla vacía |
| Publicación en PyPI | Publicado: `arancel-mx==0.2.0` (`0.2.1` in-tree, no en PyPI hasta `pkg-v0.2.1`) |

## Contribución

Las contribuciones de la **comunidad de código abierto** son bienvenidas. Consulta [`CONTRIBUTING.md`](CONTRIBUTING.md), [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md), [`SECURITY.md`](SECURITY.md), `LICENSE` y `NOTICE` antes de enviar cambios.

Para cambios de fuentes, parsers, reconciliación o release contract, agrega fixtures/pruebas offline del caso esperado. Para cambios del build oficial, actualiza el lock/constraints en el mismo PR cuando corresponda.

## Notas de procedencia

El proyecto conserva capture manifests y hashes para que una release pueda relacionarse con los snapshots observados. La presencia de una fuente o registro en el dataset describe evidencia técnica observada; no sustituye la publicación oficial ni una interpretación jurídica especializada.
