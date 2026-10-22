# Arquitectura

Este documento describe cómo está construido `arancel-mx` hoy: primero la vista general (qué piezas existen y por dónde fluyen los datos) y después cada módulo, script y workflow. La decisión que fija esta forma es la [decisión 0002](decisions/0002-arquitectura-github-primero.md).

**Regla central:** GitHub guarda y sirve los datos, GitHub Actions hace todo el cómputo y Vercel sólo sirve el frontend estático. La GitHub Release verificada es la única fuente de verdad. Cualquier otra superficie es una proyección de esa release.

## 1. Vista general

```text
Fuentes oficiales                    GitHub Actions (cómputo)                 GitHub (almacenamiento)            Consumo
─────────────────                    ────────────────────────                 ──────────────────────             ───────
Diputados (ledger LIGIE)  ┐                                                                                     ┌ pip + CLI + Dataset
SNICE (LIGIE, NICO,       ├─ captura ─► Official data pipeline (diario) ─► Release data-YYYY.MM.DD ─────────────┤   (descarga y verifica)
  notas nacionales)       │            build → certificación → atestación     6 assets inmutables              │
DOF / SIDOF               ┘            → publicación                                    │                       ├ DuckDB / CSV / JSON
                                              │                                         ▼                       │
                                              ├──► API estática ──────────► rama gh-pages → GitHub Pages ───────┼ /data/v1 (vía Vercel)
                                              │    static_api.py                 /arancel-mx/v1/                │
                                              └──► vigilancia SIDOF ───────► issues «dof-candidate»            └ frontend en Vercel
                                                   watch_dof.py                 (revisión humana)
```

| Pieza | Dónde vive | Qué hace | Estado |
|---|---|---|---|
| Pipeline oficial | `.github/workflows/official-data-pipeline.yml` | Captura, reconcilia, construye, certifica, atestigua y publica. | Vigente, diario (`17 11 * * *`). |
| Release de datos | GitHub Releases `data-YYYY.MM.DD` | `arancel_mx.duckdb`, `.csv`, `.json`, `manifest.json`, `SHA256SUMS`, `official-sources.tar.gz`. | Vigente. Fuente de verdad. |
| API estática | rama `gh-pages`, servida por GitHub Pages | JSON por capítulo HS2, índice de búsqueda y manifest con SHA-256 por archivo. | Vigente. |
| Paquete Python | PyPI `arancel-mx` | Cliente `Dataset`, CLI y servidor FastAPI opcional. | Vigente. |
| Frontend | Vercel (`website/`) | Sitio y explorador; leen `/data/v1`, que Vercel reescribe hacia Pages. | Vigente. |
| Vigilancia del DOF | job `notify` del pipeline | Consulta SIDOF y abre un issue por instrumento candidato. | Vigente. |
| API dinámica `/v1` | Funciones de Vercel sobre Neon | Proyección operacional de la release. | **Deprecada**, se retira el 2027-01-31. |

## 2. Flujo de una publicación

1. **Disparo.** El cron diario o un `workflow_dispatch` inicia el **Official data pipeline**. Las ejecuciones que publican comparten un grupo de concurrency y nunca se solapan.
2. **`build-and-verify`** (sólo lectura).
   - Ejecuta las pruebas.
   - Obtiene la release anterior (`scripts/fetch_previous_release.py`).
   - Construye el candidato con `scripts/run_official_pipeline.py`. Si las fuentes no cambiaron, termina como `no_change` y no publica nada.
   - Certifica el bundle (`arancel_mx.certification`) y emite la atestación SLSA.
3. **`publish`** (`contents: write`, `pages: write`, `attestations: write`, `id-token: write`).
   - `scripts/publish_release.py` crea la release inmutable.
   - Después, `scripts/build_static_pages.py` descarga esa misma release mediante el cliente público, que verifica manifest y checksums.
   - Genera `v1/` y verifica cada archivo contra su manifest.
   - Publica el árbol en la rama `gh-pages` y pide a Pages que lo despliegue.
   - Si este paso falla, la release ya publicada no se toca y el workflow deja una advertencia.
4. **`notify`** (`issues: write`).
   - `scripts/watch_dof.py` revisa los últimos siete días del DOF en SIDOF y abre un issue `dof-candidate` por cada nota arancelaria nueva.
   - `scripts/data_alert.py` abre o cierra el issue de falla del pipeline.

Cada permiso de escritura vive sólo en el job que lo necesita. `tests/test_workflow_hardening.py` lo comprueba sin red.

## 3. Superficies de consumo

| Superficie | Contrato | Documento |
|---|---|---|
| Archivos de release | Seis assets, `manifest.json` schema v2, `SHA256SUMS`. | [Modelo de datos](data-model.md) |
| Python | `Dataset.version("data-YYYY.MM.DD")`, `Dataset.latest()`, `Dataset.open(path)`. | [Consumo externo](external-consumption.md) |
| CLI | `arancel-mx doctor`, `data …`, `lookup`, `search`, `ficha`, `provenance`, etc. | [CLI de consumo](consumer-cli.md) |
| API estática | `GET /data/v1/meta.json`, `records/{hs2}.json`, `search-index.json`… | [Consumo externo](external-consumption.md#api-http-pública) |
| Servidor propio | `uvicorn arancel_mx.api.app:app` con `ARANCEL_MX_API_DATASET`. | [Consumo externo](external-consumption.md) |
| `/v1` en Vercel | Deprecada; responde con `Deprecation`, `Sunset` y `Link`. | [Retiro de la API dinámica](operations/v1-sunset.md) |

### Archivos de la API estática

| Archivo | Contenido |
|---|---|
| `meta.json` | Identidad del dataset, versión del exportador y `release_verified`. |
| `sections.json`, `chapters.json` | Secciones HS y capítulos HS2. |
| `records/{hs2}.json` | Todos los registros vigentes del capítulo, con el mismo modelo que `/v1/lookup`. Resuelve `lookup`, `ficha`, `parent` y `children`. |
| `provenance/{hs2}.json` | Fuentes del capítulo y enlaces código → fuente. |
| `national-notes/{hs2}.json` | Notas nacionales del capítulo. |
| `search-index.json` | Pares `[código, descripción normalizada]` para `search` y `suggest`. |
| `manifest.json` | SHA-256 y tamaño de cada archivo, más la release de origen. |

Un archivo por capítulo en lugar de uno por código reduce el árbol de unos 133,000 archivos a menos de 300 y la generación de una hora a segundos. Hay tres implementaciones que leen el árbol, y `tests/test_static_api.py` comprueba que coincidan entre sí:

- `frontend/src/static-api.js`, en el navegador;
- `arancel_mx.static_api.StaticApi`, en Python;
- el `Dataset` original.

## 4. Módulos del paquete (`src/arancel_mx/`)

| Módulo | Responsabilidad | Entradas principales |
|---|---|---|
| `cli.py` | CLI de mantenimiento y registro de los comandos de consumo. | `build`, `check-updates`, `reconcile`, `release`, `static-api build\|verify` |
| `static_api.py` | Exporta y verifica la API estática; lector `StaticApi`. | `build_static_api`, `verify_static_api` |
| `sources/` | Registro de fuentes, descarga con allowlist de hosts, captura con SHA-256, SIDOF, ledger de Diputados, evidencia DOF, validación de páginas HTML. | `registry.py`, `http.py`, `capture.py`, `sidof.py`, `diputados.py`, `legal_evidence.py`, `html_pages.py`, `dof_pdf.py` |
| `parsers/` | Lectura offline de libros SNICE (LIGIE, NICO), notas nacionales y PDF de jerarquía. | `workbooks.py`, `profiles.py`, `documents.py` |
| `domain/` | Normalización de códigos, identidad de registro y hash semántico. | `normalization.py` |
| `pipeline/` | Orquesta el build oficial: captura, jerarquía, cobertura NICO, reconciliación legal y exportación. | `official_dataset.py`, `official_sources.py`, `build.py`, `hierarchy.py`, `reconcile.py`, `update.py` |
| `storage/` | Esquema y conexión DuckDB. | `duckdb.py` |
| `release/` | Empaquetado de release, verificación de bundle e identidad de fuentes. | `package.py`, `metadata.py` |
| `certification/` | Certificación del bundle y del DuckDB antes de publicar. | `bundle.py`, `consumer.py`, `reports.py` |
| `consumer/` | Cliente público: descarga, caché, verificación, consultas, CLI de consumo, errores tipados. | `dataset.py`, `manager.py`, `release_api.py`, `query.py`, `integrity.py`, `cli.py` |
| `api/` | Servidor FastAPI de sólo lectura; también sirve el sitio y `/data/v1`. | `app.py`, `routes.py`, `models.py`, `config.py` |
| `operational/` | Proyección en Neon para la API dinámica de Vercel. **Se retira con `/v1`.** | `sync.py`, `query.py` |
| `benchmark/` | Evaluación offline de recuperación sobre un conjunto etiquetado. | `classification.py` |

Las fronteras de importación (por ejemplo, que `consumer` no dependa de `pipeline`) se prueban en `tests/test_import_boundaries.py`.

## 5. Scripts (`scripts/`)

| Script | Lo usa |
|---|---|
| `run_official_pipeline.py`, `fetch_previous_release.py`, `workflow_diagnostics.py`, `publish_release.py`, `build_static_pages.py`, `watch_dof.py`, `data_alert.py` | Official data pipeline |
| `check_documented_urls.py`, `validate_ligie_html_pages.py`, `check_duckdb_compat.py`, `certify_package_install.py` | CI |
| `validate_package_tag.py`, `certify_testpypi_candidate.py` | Publicación del paquete |
| `certify_github_release.py`, `certify_github_issue.py` | Certificación de producción |
| `check_public_service.py` | Canario diario del bundle publicado |
| `github_api.py`, `package_consumer_probe.py` | Bibliotecas compartidas por los scripts anteriores |
| `build_official_dataset.py` | Build local de punta a punta, sin comparar contra la release anterior |
| `capture_instrument_research.py` | Captura local de instrumentos para el [inventario](research/ligie-instrument-inventory.md) |
| `dependency_compatibility_probe.py` | Pruebas de compatibilidad de dependencias |
| `promote_operational_release.py` | Promoción manual a Neon; se retira con `/v1` |
| `build-frontend.mjs`, `sync-frontend-static.mjs` | `npm run build:frontend` y mantenimiento del frontend |

## 6. Workflows (`.github/workflows/`)

| Workflow | Disparo | Qué hace |
|---|---|---|
| `ci.yml` | PR y push | `test` (ruff, mypy, presupuesto de tipos, pytest con cobertura ≥ 87 %, URLs documentadas, build y smoke de instalación), `api-runtime` (servidor FastAPI sobre Python 3.13), `browser-smoke` (Playwright). El check requerido en `main` es `test`. |
| `official-data-pipeline.yml` | Diario y manual | Sección 2. |
| `published-bundle-canary.yml` | Diario y manual | Descarga y verifica la última release como lo haría un consumidor. |
| `publish-python-package.yml` | Tags `pkg-v*` | TestPyPI, matriz de certificación y PyPI con Trusted Publishing. Ver [release del paquete](package-release.md). |
| `production-certification.yml` | Manual | Certifica los límites de permisos de escritura. Ver [certificación de producción](production-certification.md). |

## 7. Frontend

- **Fuente:** `frontend/` (Vite + React). Las rutas se declaran en `frontend/src/routes.js` y el contenido en `frontend/src/content.js`.
- **Build:** `npm run build:frontend` compila con Vite y `sync-frontend-static.mjs` copia el resultado, con nombre por hash de contenido, a dos destinos:
  - `website/`, que publica Vercel;
  - `src/arancel_mx/api/static/site/`, que sirve FastAPI.
- **Datos:** el navegador llama a `/data/v1/...`. En Vercel esa ruta se reescribe a GitHub Pages; en un servidor FastAPI local, `app.py` genera el árbol desde el dataset activo la primera vez que se pide.
- **Scripts estables** en `website/assets/` (no generados por Vite):
  - `site-bridge.js` muestra la release activa leyendo `meta.json` y sólo reescribe `.release-window code`;
  - `hub-interactions.js` y `trade-desk.js` usan el mismo cliente `static-api.js`.
- **Caché en `vercel.json`:**
  - los bundles `index-*` llevan nombre por hash y son `immutable`;
  - los demás assets usan `max-age=0, must-revalidate`.
- **Enrutamiento:** el *fallback* de SPA excluye `assets/`, `data/`, `api/`, `v1/` y `docs/`, para que un archivo inexistente responda 404 y no la página principal.
- **Pruebas:**
  - Playwright en `tests/e2e/*.spec.mjs`, sobre uvicorn;
  - contratos de build en `tests/e2e/*.test.mjs`;
  - paridad del cliente estático en `tests/frontend/static_api_parity.mjs`.

Detalle en [fuente mantenible del frontend](frontend-source.md).

## 8. Invariantes

Si un cambio rompe uno de estos puntos, el cambio está mal aunque las pruebas locales pasen:

1. **Una sola fuente de verdad.** Ninguna superficie publica datos que no estén en una release verificada.
2. **Fail-closed.** Una discrepancia legal, un parser ambiguo o una verificación fallida bloquean la publicación. Nunca se corrigen datos en silencio.
3. **Releases inmutables.** Un tag `data-YYYY.MM.DD` publicado no se reescribe; una colisión falla con `release_tag_collision`.
4. **Mínimo privilegio.** Los permisos de escritura viven en un solo job cada uno; las acciones se fijan por SHA.
5. **Sólo lectura hacia fuera.** Ninguna superficie pública acepta escrituras ni requiere credenciales.
6. **Recuperar, no clasificar.** `search` y `suggest` recuperan evidencia; el proyecto no clasifica mercancías ni da asesoría legal.

## 9. Configuración que no vive en el código

| Ajuste | Dónde |
|---|---|
| Protección de `main`, inmutabilidad de releases, permisos de Actions | [Configuración de GitHub](operations/github-settings.md) |
| GitHub Pages desde la rama `gh-pages` | Settings → Pages (se crea con la primera publicación) |
| Variables de Neon y `CRON_SECRET` | Vercel, sólo hasta el retiro de `/v1` |

## Relacionado

- [Decisión 0002](decisions/0002-arquitectura-github-primero.md): por qué esta arquitectura.
- [Proceso de release](release-process.md): el pipeline paso a paso.
- [Fuentes y reconciliación](sources.md): qué se captura y cómo se valida.
- [Programa de profundidad](depth-program.md): hacia dónde va el modelo de datos.
