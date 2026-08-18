<div align="center">

<img src="docs/assets/arancel-mx-banner.svg" alt="arancel.mx - datos arancelarios abiertos de México" width="100%" />

# arancel-mx

## De publicaciones oficiales dispersas a datos arancelarios verificables y listos para usar

`arancel-mx` captura, reconcilia, normaliza y publica LIGIE/NICO con procedencia verificable para que puedas **consultar, integrar, analizar y auditar** datos arancelarios de México sin reconstruir el pipeline desde cero.

<p>
  <strong>Español</strong> · <a href="./README.en.md">English</a>
</p>

[![CI](https://github.com/jccontrerasg08-cpu/arancel-mx/actions/workflows/ci.yml/badge.svg)](https://github.com/jccontrerasg08-cpu/arancel-mx/actions)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue?logo=python&style=flat-square)](https://www.python.org)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![DuckDB](https://img.shields.io/badge/DuckDB-embedded-FFF000?logo=duckdb&logoColor=000)](https://duckdb.org/)
[![PRs Welcome](https://img.shields.io/badge/PRs-welcome-brightgreen.svg)](CONTRIBUTING.md)

**[Abrir el hub](https://arancel-mx.vercel.app/)** · **[Últimos datos](https://github.com/jccontrerasg08-cpu/arancel-mx/releases/latest)** · **[Instalar](#en-60-segundos)** · **[Quickstart](docs/consumer-quickstart.md)** · **[Documentación](docs/README.md)**

</div>

## Por qué existe

Los datos arancelarios mexicanos se publican en documentos, páginas y archivos que cumplen funciones distintas. Para construir una aplicación sobre ellos no basta con descargar un XLSX: hay que saber **qué fuente se observó, cuándo se capturó, qué evidencia legal la acompaña, cómo se normalizó y qué bytes produjeron el dataset final**.

`arancel-mx` nació para separar ese problema en una capa pública y reusable. Su responsabilidad es estrecha: convertir fuentes oficiales observadas en una representación canónica, reproducible y auditable. Interfaces analíticas, RAG, automatizaciones y productos de comercio exterior pueden consumir esa capa sin duplicar parsers ni inventar su propia versión de la LIGIE/NICO.

> **Idea central:** no tienes que confiar en que el README diga “está actualizado”. Puedes verificar la release, sus hashes, su manifest y las fuentes capturadas.

## Elige cómo usarlo

| Quiero... | Superficie | Primer paso |
|---|---|---|
| **Datos / DuckDB** para SQL, BI, notebooks o ETL | Releases inmutables: DuckDB, CSV y JSON | `arancel-mx data download` |
| **CLI** para consultar una fracción rápidamente | `lookup`, `search`, `ficha`, `chapters`, `provenance`, `compare` | `arancel-mx lookup 01012101` |
| **Python** para integrarlo en una aplicación | `Dataset` y tipos públicos | `from arancel_mx import Dataset` |
| **HTTP / API** read-only para servicios y UIs | `/v1`, `/docs`, `/readyz`; sin API key | `GET /v1/lookup/8517130100` |
| **Auditoría y reproducción** | `manifest.json`, `SHA256SUMS`, fuentes capturadas, `data verify` | `sha256sum -c SHA256SUMS` |

### En 60 segundos

```bash
pip install arancel-mx==0.2.0
arancel-mx doctor
arancel-mx data download
arancel-mx lookup 01012101
arancel-mx ficha 01012101
arancel-mx data verify
```

Para explorar más:

```bash
arancel-mx chapters
arancel-mx search "refrigeradores"
arancel-mx suggest "camisas de algodón de punto"
arancel-mx compare 01012101
arancel-mx wco cite 01
```

El paquete Python y el dataset tienen ciclos de versión separados. `arancel-mx --version` identifica el paquete; cada dataset publicado usa una release inmutable `data-YYYY.MM.DD`. Fijar el paquete **no** fija el dataset.

## Del documento oficial a una release verificable

```text
fuentes oficiales → captura → reconciliación legal → parseo → validación
→ sin cambios: termina en verde
→ cambio válido: release inmutable verificado
→ cualquier fallo: bloquea la publicación + GitHub Issue
```

La cadena de confianza completa conserva identidad de fuente, URL, SHA256, `retrieved_at`, evidencia de reconciliación, commit, run de GitHub Actions y manifest de release. El modelo es fail-closed: una discrepancia, parser dudoso o validación fallida no se “arregla” silenciosamente para publicar.

<p align="center">
  <img src="docs/assets/pipeline.svg" alt="Pipeline de fuentes oficiales a DuckDB, CSV, JSON y release" width="950" />
</p>

## Última versión del dataset

**Descarga siempre la release pública más reciente de `arancel-mx`.**

**[DuckDB](https://github.com/jccontrerasg08-cpu/arancel-mx/releases/latest/download/arancel_mx.duckdb)** ·
**[CSV](https://github.com/jccontrerasg08-cpu/arancel-mx/releases/latest/download/arancel_mx.csv)** ·
**[JSON](https://github.com/jccontrerasg08-cpu/arancel-mx/releases/latest/download/arancel_mx.json)** ·
[Manifest](https://github.com/jccontrerasg08-cpu/arancel-mx/releases/latest/download/manifest.json) ·
[SHA256SUMS](https://github.com/jccontrerasg08-cpu/arancel-mx/releases/latest/download/SHA256SUMS) ·
[Fuentes oficiales](https://github.com/jccontrerasg08-cpu/arancel-mx/releases/latest/download/official-sources.tar.gz) ·
**[Ver release](https://github.com/jccontrerasg08-cpu/arancel-mx/releases/latest)**

Los enlaces `/releases/latest/download/...` apuntan a los assets de la release pública marcada como más reciente. GitHub muestra el tamaño de cada asset en su página; la identidad verificable es `SHA256SUMS`, no el tamaño visual del archivo.

```bash
sha256sum -c SHA256SUMS
```

<p align="center">
  <img alt="arancel-mx demo" src="docs/demo.gif" style="max-width:100%; border-radius:8px; box-shadow:0 8px 30px rgba(2,6,23,0.6)" />
</p>

<p align="center"><strong>Captura · Reconcilia · Normaliza · Valida · Publica</strong></p>

## Alcance

`arancel-mx` es una capa pública de datos para la LIGIE, NICO y sus fuentes oficiales. Prioriza datos, procedencia documental, validación, DuckDB y artefactos reproducibles; no pretende reemplazar un sistema comercial completo de comercio exterior.

Licencia del proyecto: **Apache-2.0**.

> [!IMPORTANT]
> `arancel-mx` es una herramienta técnica y de datos. **No constituye asesoría legal.** Para decisiones de clasificación arancelaria, cumplimiento regulatorio, importación o exportación deben consultarse las fuentes oficiales aplicables y, cuando corresponda, profesionales especializados.

## Qué incluye

- Captura snapshots registrados de Diputados, DOF y SNICE con SHA256 y `retrieved_at` real.
- Puede evaluar candidatos LIGIE/NICO fechados descubiertos en el corpus SNICE_DOCS registrado, manteniendo parseo y reconciliación legal como gates bloqueantes.
- Normaliza HS2, HS4, HS6, fracción MX de 8 dígitos y NICO de 10 dígitos.
- Materializa DuckDB y exporta CSV, JSON y manifest schema v2.
- Detecta `no_change` sin crear releases redundantes.
- El **Official data pipeline** realiza una revisión programada semanal los lunes y hace **publicación automática** sólo cuando el dataset cambió y todos los gates pasaron.
- Abre o actualiza un **GitHub Issue** cuando un stage de producción falla.
- Publica releases `data-YYYY.MM.DD` con un contrato exacto de seis assets verificables.
- Mantiene certificación manual aislada para probar write-boundaries y rollback.

## Por qué es diferente

| Propiedad | Cómo se implementa |
|---|---|
| Procedencia | Cada fuente conserva autoridad, URL, identidad, hash y tiempo de captura |
| Evidencia legal | El ledger de Diputados se reconcilia contra DOF y fuentes registradas |
| Fail-closed | Una discrepancia, parser dudoso o validación fallida bloquea publicación |
| Reproducibilidad | Dependencias de producción exactas y manifest schema v2 |
| Determinismo | Exportaciones canónicas, checksums y archive de fuentes |
| Auditabilidad | La release enlaza registry, commit, run de GitHub y artifact exacto |
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

### Promoción rápida de fuentes sin debilitar la confianza

Los registros LIGIE y NICO pueden inspeccionar el corpus público SNICE_DOCS declarado explícitamente. Un documento sólo es elegible si proviene del índice registrado, coincide con una familia y tipo de medio permitidos, contiene fecha válida y es el candidato más reciente sin ambigüedad. Su origen de descubrimiento se conserva junto al SHA256; parseo, validación, reconciliación Diputados/DOF y certificación siguen siendo gates obligatorios.

<p align="center">
  <img src="docs/assets/source-promotion.png" alt="Páginas SNICE registradas y el corpus SNICE_DOCS convergen en un candidato fechado que pasa por gates de publicación" width="100%" />
</p>

Consulta la [política de promoción de fuentes](docs/source-promotion.md) para la allowlist, los límites NICO y el procedimiento de rollback.

## Instalación

Requiere Python 3.11 o superior.

### Consumo del dataset publicado

`arancel-mx==0.2.0` está publicado en PyPI desde 2026-08-12 vía Trusted Publishing. La matriz externa completa de SO/Python no fue un gate bloqueante de esa carga. `0.3.3` permanece in-tree y su flujo de publicación bloquea en Ubuntu/Windows/macOS × CPython 3.11–3.13 después de TestPyPI.

```bash
pip install arancel-mx==0.2.0
arancel-mx --version
arancel-mx doctor
```

La guía canónica para aplicaciones aguas abajo es [`docs/external-consumption.md`](docs/external-consumption.md).

### Desarrollo del repositorio

```bash
python -m venv .venv
# PowerShell: .\.venv\Scripts\Activate.ps1
# macOS/Linux: source .venv/bin/activate
python -m pip install -e ".[dev]"
python -m arancel_mx --help
```

Los builds oficiales y CI usan `requirements/production-build.txt`:

```bash
python -m pip install pip==26.2.1
python -m pip install -c requirements/production-build.txt -e ".[dev]"
```

## Consumo externo

Las aplicaciones aguas abajo deben fijar, instalar, verificar y consultar `arancel-mx` como paquete de datos. Empieza con [`docs/consumer-quickstart.md`](docs/consumer-quickstart.md), revisa los [roles de fuentes oficiales](docs/official-source-roles.md), la [jerarquía NICO/LIGIE](docs/nico-ligie-guide.md) y la guía completa [`docs/external-consumption.md`](docs/external-consumption.md).

### API HTTP pública

La **API HTTP pública** es **GET-only**, **read-only** y funciona **sin API key**. El contrato estable vive bajo `/v1`; `/docs` expone OpenAPI, `/readyz` reporta readiness y `/v1/meta` separa identidades de API, paquete y dataset.

```text
ARANCEL_MX_API_DATASET=data-2026.08.15
```

No existe fallback silencioso a `latest`. La capa HTTP reutiliza el `Dataset` verificado, **no clasifica** mercancías y no constituye **asesoría legal**.

El hub principal es [`https://arancel-mx.vercel.app`](https://arancel-mx.vercel.app). Desde la integración #132, Vercel sirve metadata y búsqueda operacional read-only (`/v1/meta`, `/v1/search`) desde su capa operacional sincronizada con releases verificadas. Las demás rutas `/v1/*`, `/docs` y `/readyz` se presentan bajo el mismo dominio y se proxifican al runtime FastAPI reusable en `arancel-mx.fastapicloud.dev`. La fuente de verdad sigue siendo la release verificada; la capa operacional no sustituye el pipeline de publicación.

Para una integración FastAPI independiente también se puede fijar la base URL explícitamente:

```bash
export ARANCEL_MX_API_URL="https://arancel-mx.fastapicloud.dev"
curl "$ARANCEL_MX_API_URL/v1/lookup/8517130100"
```

El contrato completo y los endpoints están en [`docs/external-consumption.md`](docs/external-consumption.md).

## Uso rápido CLI

```bash
arancel-mx doctor
arancel-mx data download
arancel-mx lookup 01012101
arancel-mx ficha 01012101
arancel-mx compare 01012101
arancel-mx chapters
arancel-mx search "refrigeradores"
arancel-mx suggest "camisas de algodón de punto"
arancel-mx wco cite 01
arancel-mx data verify
```

Después de descargar y verificar una release, las consultas pueden operar offline:

```bash
arancel-mx lookup 01012101 --offline --format json
arancel-mx data verify --offline --format json
```

Fija una release exacta con `--dataset data-YYYY.MM.DD`. Consulta [`docs/consumer-cli.md`](docs/consumer-cli.md) para formatos JSON/CSV, variables de entorno, cache e integridad.

### Comandos para consumidores

| Comando | Uso |
|---|---|
| `doctor` | Diagnostica instalación, cache, dataset, DuckDB y acceso remoto |
| `data download` | Descarga y promueve sólo una release verificada |
| `data status` / `data list` | Muestra versiones locales y releases remotas válidas |
| `data update` | Descarga la release válida más reciente sin borrar anteriores |
| `data path` | Imprime la ruta del DuckDB seleccionado |
| `data verify` | Revalida integridad local y opcionalmente remota |
| `lookup` / `search` | Consulta por código exacto o texto |
| `suggest` | Recupera ficha y notas nacionales de candidatos; no clasifica |
| `wco cite` / `wco download` | Referencia al PDF HS 2022 OMA; apoyo de lectura, no autoridad LIGIE/NICO |
| `ficha` | Ficha capítulo → fracción/NICO con UM, IGI e IGE |
| `compare` | Diff HS6 / MX8 / NICO contra VUCEM, informativo |
| `chapters` | Lista capítulos HS2 |
| `parent` / `children` | Navega HS2 → HS4 → HS6 → MX8 → NICO10 |
| `provenance` | Muestra trazabilidad documental |

### Comandos de mantenimiento del repositorio

```bash
python -m arancel_mx build --database data/arancel.duckdb --output-dir out/release
python -m arancel_mx check-updates --state-path data/update_state/ligie.json --report-path out/update.json
python -m arancel_mx reconcile --ledger-json ledger.json --dof-json dof.json --snice-json snice.json
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

`Dataset.open("arancel_mx.duckdb")` abre un archivo local validado estructuralmente. `ficha` y `chapters` usan el dataset oficial verificado; no scrapean SIICEX-CAAAREM ni dumps como tigies-mx.

## Modelo de datos

DuckDB separa clasificación, tasas, vigencia y procedencia. Tablas principales: `source_registry`, `source_document`, `hs_code`, `tariff_fraction`, `nico`, `tariff_rate`, `canonical_record`, `record_provenance` y `dataset_release`.

El manifest schema v2 conserva `registry_sha256`, `git_commit_sha`, `github_run_id`, `github_run_attempt`, `github_workflow_ref` y `github_artifact_name`. Consulta [`docs/data-model.md`](docs/data-model.md).

## Artefactos y reproducibilidad

Una release válida contiene exactamente:

```text
release/
├── arancel_mx.duckdb
├── arancel_mx.csv
├── arancel_mx.json
├── manifest.json
├── SHA256SUMS
└── official-sources.tar.gz
```

`manifest.json` conserva versión, procedencia, reconciliación, conteos y hashes. `SHA256SUMS` cubre los otros cinco assets. `official-sources.tar.gz` conserva los bytes oficiales capturados y `source_capture.json`.

## Construcción end-to-end de dataset oficial

```bash
python scripts/build_official_dataset.py \
  --work-dir data/embedded/official-build \
  --output-dir out/release \
  --effective-as-of 2026-08-10 \
  --dataset-version 2026.08.10
```

`scripts/run_official_pipeline.py` añade comparación contra el manifest anterior, diagnóstico estructurado y semántica `no_change`.

## Pipeline oficial autónomo

El workflow **Official data pipeline** vive en [`.github/workflows/official-data-pipeline.yml`](.github/workflows/official-data-pipeline.yml).

- Schedule vigente: `17 11 * * 1`, una **revisión semanal automatizada los lunes** en UTC.
- El cron anterior `17 11 * * *` correspondía a una **revisión diaria automatizada** y fue reemplazado por #132.
- `workflow_dispatch` permite dry-run y ejecución mantenida; `publish=false` es el valor manual por defecto.
- Build: `contents: read` y tests offline antes de tocar la red.
- Publish: `contents: write` sólo si `main` produjo `built` y la ejecución está autorizada.
- Notify: `issues: write` sólo para alertas y recovery.
- Canario: [`.github/workflows/published-bundle-canary.yml`](.github/workflows/published-bundle-canary.yml) verifica el contrato público de seis assets.

La **publicación automática** ocurre sólo para un cambio válido y verificado. **Cualquier falla bloquea la publicación**. Si no hubo cambios, `no_change` termina en verde y el publisher queda `skipped`.

Consulta [`docs/release-process.md`](docs/release-process.md) para el contrato exacto y [`docs/production-certification.md`](docs/production-certification.md) para la certificación de permisos y rollback.

## Fuentes oficiales

El registro versionado vive en `src/arancel_mx/sources/source_registry.json`.

Fuentes principales:

- [Diputados, LIGIE](https://www.diputados.gob.mx/LeyesBiblio/ref/ligie_2022.htm)
- [SNICE, LIGIE](https://www.snice.gob.mx/cs/avi/snice/ligie.info22.html)
- [SNICE, NICO y propuestas NICO](https://www.snice.gob.mx/cs/avi/snice/ligie.nico2022.html)
- [SNICE, notas nacionales](https://www.snice.gob.mx/cs/avi/snice/ligie.notasnac22.html)
- [SNICE, indicadores](https://www.snice.gob.mx/cs/avi/snice/ligie.indicaranc22.html)
- [Diario Oficial de la Federación, publicación relacionada](https://dof.gob.mx/nota_detalle.php?codigo=5656249&fecha=27/06/2022)

[`docs/sources.md`](docs/sources.md) explica cómo el ledger registrado de Diputados se usa como ancla y cómo la evidencia DOF participa como gate. SIICEX-CAAAREM y dumps como tigies-mx no son fuentes oficiales.

## Proceso y calendario visual

### Calendario DOF, parte 1

<p align="center"><img alt="Calendario de publicaciones DOF y plazos, parte 1" src="docs/dof_timeline.png" style="max-width:85%" /></p>

### Calendario DOF, parte 2

<p align="center"><img alt="Calendario de publicaciones DOF y plazos, parte 2" src="docs/dof_timeline2.png" style="max-width:85%" /></p>

### Flujo NICO / DOF

<p align="center"><img alt="Flujo de publicación NICO y DOF" src="docs/nico_flow.png" style="max-width:85%" /></p>

Estas imágenes son contexto documental, no un indicador dinámico del dataset.

## Estructura del repositorio

```text
.github/
├── workflows/
│   ├── ci.yml
│   ├── official-data-pipeline.yml
│   ├── publish-python-package.yml
│   └── production-certification.yml
└── dependabot.yml
api/
requirements/
└── production-build.txt
src/arancel_mx/
├── api/
├── certification/
├── consumer/
├── domain/
├── operational/
├── parsers/
├── pipeline/
├── release/
├── sources/
└── storage/
scripts/
website/
docs/
tests/
TERMS.md
LICENSE
NOTICE
```

El repositorio incluye pruebas que buscan credenciales y rutas privadas. Datos generados, snapshots, DuckDB locales y tokens permanecen fuera de Git.

## Pruebas

```bash
python -m pytest -q
python -m build
git diff --check
```

El workflow se muestra como **CI** y el required check de `main` es **`test`**. Un PR normal no publica releases.

El runbook de configuración está en [`docs/operations/github-settings.md`](docs/operations/github-settings.md). Ver también [`SECURITY.md`](SECURITY.md), [`CONTRIBUTING.md`](CONTRIBUTING.md) y [`docs/production-certification.md`](docs/production-certification.md).

## Seguridad y supply chain

- Actions externas fijadas por SHA completo.
- Dependencias de producción restringidas por `requirements/production-build.txt`.
- Dependabot propone actualizaciones de Python y GitHub Actions.
- El pipeline usa permisos mínimos por job, no `write-all`.
- Releases sin PAT.
- Certificación de write-boundaries separada de producción.

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
| Hub Vercel con metadata y búsqueda operacional | Disponible |
| API HTTP pública | Disponible (`/v1`, GET-only/read-only, sin API key) |
| Ficha TIGIE (`ficha` / `chapters`) | Disponible |
| Compare HS6 / MX8 / NICO vs VUCEM | Disponible, informativo |
| Notas nacionales LIGIE | Parser, captura oficial y vista `arancel_mx_national_notes`; `data-2026.08.15` contiene 266 registros de la fuente oficial DOF |
| Publicación en PyPI | Publicado: `arancel-mx==0.2.0` (`0.3.3` in-tree, no en PyPI hasta `pkg-v0.3.3`) |

## Contribución

Las contribuciones de la **comunidad de código abierto** son bienvenidas. Consulta [`CONTRIBUTING.md`](CONTRIBUTING.md), [`CODE_OF_CONDUCT.md`](CODE_OF_CONDUCT.md), [`SECURITY.md`](SECURITY.md), [`TERMS.md`](TERMS.md), [`opensource-checklist.md`](opensource-checklist.md), `LICENSE` y `NOTICE` antes de enviar cambios.

Para cambios de fuentes, parsers, reconciliación o release contract, agrega fixtures/pruebas offline del caso esperado. Para dependencias del build oficial, actualiza `requirements/production-build.txt` en el mismo PR cuando corresponda.

## Notas de procedencia

El proyecto conserva **capture manifests y hashes** para relacionar una release con los snapshots observados. Esa evidencia técnica no sustituye la publicación oficial ni una interpretación jurídica especializada.

[Español](README.md) · [English](README.en.md) · [Centro de documentación](docs/README.md) · [Fuentes](docs/sources.md) · [Política SNICE_DOCS](docs/source-promotion.md) · [Certificación](docs/production-certification.md) · [Contribuir](CONTRIBUTING.md) · [Seguridad](SECURITY.md)
