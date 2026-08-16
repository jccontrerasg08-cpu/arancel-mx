# Contrato de consumo externo

Guía canónica para aplicaciones que consumen `arancel-mx` como paquete de datos verificado o mediante su API HTTP pública de solo lectura (por ejemplo AduanaMap). No sustituye el pipeline interno ni convierte este repositorio en una plataforma aduanera.

El recorrido de ingesta esperado es:

```text
fijar arancel-mx==0.2.0
  -> pip install arancel-mx==0.2.0
  -> arancel-mx doctor
  -> descargar una release exacta data-YYYY.MM.DD
  -> verificar SHA256SUMS + manifest.json + DuckDB
  -> consultar IGI/IGE, jerarquía, vigencia y procedencia
  -> opcionalmente autoingerir CSV/JSON/DuckDB en el almacén del consumidor
```

## Qué es y qué no es arancel-mx

`arancel-mx` es un paquete de datos fail-closed de la LIGIE/NICO mexicana. Publica seis assets verificables en GitHub Releases, un paquete Python de consulta y, desde el contrato en desarrollo `0.3.0`, una API HTTP pública GET-only y read-only. No es asesoría legal, no es un clasificador arancelario y no es AduanaMap.

El software original se distribuye como `arancel-mx` (nombre en PyPI), se importa como `arancel_mx` y el comando de consola es `arancel-mx`. No existe la distribución `arancelmx`.

Tipos públicos documentados: `Dataset`, `TariffRecord`, `Ficha`, `ProvenanceRecord`, `SearchResult`, `DatasetInfo`, `HsSection` y `CompareRow`, más las excepciones exportadas desde `arancel_mx`.

## Instalar y fijar versiones

Python 3.11 o superior.

```bash
pip install arancel-mx==0.2.0
arancel-mx --version
arancel-mx doctor
```

`arancel-mx==0.2.0` ya está en PyPI (carga del 2026-08-12). El checkout declara `0.3.0`; esa versión no está en PyPI hasta `pkg-v0.3.0`. Las aplicaciones aguas abajo siguen fijando `arancel-mx==0.2.0`. La descripción larga en pypi.org es la del upload `0.2.0` (README congelado en esa rueda); los contratos vivos están en git. Fijar el paquete **no** fija el dataset. El dataset usa tags inmutables `data-YYYY.MM.DD` independientes de la versión PEP 440. `/releases/latest` resuelve hoy a `data-2026.08.15`.

```bash
arancel-mx data download --dataset data-YYYY.MM.DD
arancel-mx lookup 01012101 --dataset data-YYYY.MM.DD
```

En Python:

```python
from arancel_mx import Dataset

db = Dataset.version("data-YYYY.MM.DD")
```

`Dataset.latest()` resuelve la release pública más reciente, la verifica y la abre. No uses “lo que haya en git” como identidad de datos.

## API HTTP pública

El servicio HTTP conserva tres identidades separadas:

```text
API v1
package 0.3.0
dataset data-2026.08.15
```

El contrato `/v1` es GET-only, read-only y no requiere API key. La API usa exactamente el mismo `Dataset` verificado del paquete y no implementa su propia lógica de clasificación o tarifas. `search` y `suggest` son retrieve-only: la API no clasifica mercancías y no constituye asesoría legal.

La producción debe fijar una release inmutable de forma explícita:

```text
ARANCEL_MX_API_DATASET=data-2026.08.15
```

No existe fallback silencioso a `latest` durante el arranque del servicio. Si la configuración falta, la release no puede verificarse o el DuckDB no abre de forma válida, el servicio falla cerrado en vez de declarar readiness.

Mientras no se haya verificado el hostname de producción, los ejemplos usan `ARANCEL_MX_API_URL` y no inventan un dominio:

```bash
export ARANCEL_MX_API_URL="https://<deployment-host>"
curl "$ARANCEL_MX_API_URL/healthz"
curl "$ARANCEL_MX_API_URL/readyz"
curl "$ARANCEL_MX_API_URL/v1/meta"
curl "$ARANCEL_MX_API_URL/v1/lookup/8517130100"
```

En documentación y scripts, `ARANCEL_MX_API_URL` representa únicamente el origen HTTP ya desplegado y verificado. El ejemplo de lookup es `/v1/lookup/8517130100`.

Endpoints públicos iniciales:

```text
GET /
GET /healthz
GET /readyz
GET /v1/meta
GET /v1/lookup/{code}
GET /v1/ficha/{code}
GET /v1/search?q=...&limit=...
GET /v1/suggest?q=...&limit=...
GET /v1/chapters
GET /v1/chapters/{chapter}/national-notes
GET /v1/codes/{code}/parent
GET /v1/codes/{code}/children
GET /v1/codes/{code}/provenance
```

`/docs` y `/redoc` sirven la documentación interactiva generada desde OpenAPI. `/v1/meta` publica por separado la versión de API, la versión del paquete y la identidad del dataset cargado.

El límite de seguridad del servicio es deliberado: no ofrece endpoints HTTP de actualización, reconciliación ni publicación, tampoco expone captura oficial, `compare` live contra VUCEM ni descarga WCO. Esas funciones continúan fuera del servicio web público.

## Verificar

Orden de verificación para una release `data-YYYY.MM.DD`:

1. Resolver **un** tag exacto.
2. `arancel-mx doctor` — instalación, cache, DuckDB y acceso remoto.
3. `arancel-mx data download` — descarga a estado temporal; no promueve un cache parcial.
4. `arancel-mx data verify --bundle` — revalida integridad local y el contrato de seis assets.
5. `sha256sum -c SHA256SUMS` sólo si descargaste **todos** los assets de la GitHub Release al mismo directorio. No lo uses sobre el cache de `data download`: `SHA256SUMS` cubre cinco archivos y `data download` no los deja juntos.
6. Comprobar `manifest.json` **schema v2** (también lo cubre `data verify`).

Los seis assets, ni uno más ni uno menos:

```text
arancel_mx.duckdb
arancel_mx.csv
arancel_mx.json
manifest.json
SHA256SUMS
official-sources.tar.gz
```

`Dataset.open(path)` abre un DuckDB local tras validación estructural. Esa apertura **no** es `release_verified`: un archivo local que abre no hereda procedencia de release.

El modo `--offline` es estricto: no hay fallback de red. Si el dataset falta o falla la verificación local, el comando falla. Un código desconocido o no vigente levanta `RecordNotFoundError` (o fallo de CLI); no se inventa una fila.

## Consultar

Dos consultas de apoyo a la revisión. Ninguna publica una clasificación ni sustituye LIGIE/NICO. El dataset oficial verificado es la evidencia; WCO y VUCEM son únicamente fuentes informativas de apoyo.

1. **`search` (dos etapas, sin LLM, offline).** `arancel-mx search "camisas de algodón de punto"`. En consultas por descripción ordena primero los capítulos HS2 coincidentes y después las filas vigentes de esos capítulos. El ranking por código exacto o prefijo no cambia. Los resultados incluyen `scorer_version` (`"1"`; se incrementa si cambia el ranking) y un `confidence` de 0 a 1 para analítica. No es una clasificación.
2. **`suggest`.** `arancel-mx suggest "camisas de algodón de punto"` / `Dataset.suggest(text, limit=5)`. Mismo recorte. Imprime ficha y notas nacionales (`arancel_mx_national_notes` cuando la vista tiene filas; `data-2026.08.15` contiene 266 registros) para los N primeros, con preferencia por `fraccion8`. Retrieve-only: no afirma una clasificación. Una persona decide la clasificación; la evidencia permanece en el dataset oficial.

CLI:

```bash
arancel-mx lookup 01012101
arancel-mx ficha 01012101
arancel-mx compare 010121
arancel-mx compare 01012101
arancel-mx compare 0101210100
arancel-mx chapters
arancel-mx search "refrigeradores"
arancel-mx search "camisas de algodón de punto"
arancel-mx suggest "camisas de algodón de punto"
arancel-mx wco cite 61
arancel-mx parent 01012101
arancel-mx children 010121
arancel-mx provenance 01012101
arancel-mx lookup 01012101 --offline --format json
```

`wco cite`/`wco download` son apoyo de lectura HS 2022 de la OMA, no autoridad LIGIE/NICO ni consulta DuckDB. `cite` no descarga.

Python:

```python
from arancel_mx import Dataset

db = Dataset.latest()
record = db.lookup("01012101")
print(record.code, record.level, record.igi_text, record.ige_text)
card = db.ficha("01012101")
sources = db.provenance("01012101")  # Dataset.provenance
for chapter in db.chapters():
    print(chapter.code, chapter.description)
parent = db.parent("01012101")
children = db.children("01012101")
hits = db.search("raza pura")
db.suggest("camisas de algodón de punto", limit=5)  # retrieve-only; not a classification
rows = db.compare("01012101")  # Dataset.compare vs VUCEM; not legal identity
```

Consultas públicas: `lookup`, `search`, `suggest`, `ficha`, `chapters`, `parent`, `children`, `provenance`, `compare`.

IGI/IGE se muestran con los literales oficiales `igi_text` / `ige_text` (por ejemplo `10` o `Ex.`). No reescribas esos literales a `"16%"` ni trates `igi_value` como IVA.

Ejemplo de fixture de consumidor: la fracción vigente `01012101` (`fraccion8`) tiene `igi_text` `10` e `ige_text` `Ex.`; su NICO es `0101210100`.

Ejemplo documental SIICEX (no es una consulta live al DuckDB publicado): `11063001` **no está** en el snapshot oficial actual y `arancel-mx ficha 11063001` falla cerrado. `11062002` es la fracción documentada de sagú con IGI oficial `10`.

### Alias JSON de aplicaciones downstream

El CSV/JSON público y la vista `arancel_mx` usan las columnas canónicas `fraccion8` y `nico10`. Si una aplicación expone nombres en inglés:

- JSON `fraction8` corresponde a la columna `fraccion8` (8 dígitos).
- JSON `classification10` corresponde a la columna `nico10` (10 dígitos).

Nunca mapees 10 dígitos sobre `fraccion8`.

## Autoingesta

Una aplicación puede leer `arancel_mx.duckdb`, `arancel_mx.csv` o `arancel_mx.json` e insertarlos en su propio almacén (Postgres, API propia, etc.). Ese almacén del consumidor **no** es la verdad aguas arriba.

La identidad verificada sigue siendo la release `data-YYYY.MM.DD` con `SHA256SUMS` y `manifest.json` schema v2. No scrapees Diputados/DOF/SNICE en paralelo y trates ese scrape como equivalente a una release de `arancel-mx`.

## Mapeo de procedencia

No hay un séptimo asset `source_trace.json`. Una aplicación que necesite un objeto de trazabilidad lo compone de:

- columnas por fila `primary_source_document_id`, `primary_source_authority`, `primary_source_url`, `source_document_ids_json`, `source_count`;
- `Dataset.provenance(code)` / `arancel-mx provenance`;
- `manifest.json` (`source_documents`, `source_identity`);
- bytes oficiales y `source_capture.json` dentro de `official-sources.tar.gz`.

## Fuera de alcance

`arancel-mx` **no publica** las siguientes medidas ni servicios. No están publicados en el contrato de datos 0.2.x ni se deben inferir del API v1:

- IVA
- franja / región
- permisos
- NOM
- TLC / T-MEC
- PROSEC
- columnas de descripción en inglés
- Postgres hospedado
- API REST de escritura, administración o mutación. La API REST pública v1 permanece estrictamente GET-only/read-only.
- SIICEX-CAAAREM o HTML de VUCEM como identidad legal
- cola humana para promover capturas incompletas
- GIR, notas de sección/capítulo/subpartida o reglas complementarias (incluida la 10ª), y sugerencias HS6 WCO. Esos textos WCO no se publican como instrumento jurídico mexicano. Una caché local opcional de PDF WCO es sólo apoyo de lectura (copyright WCO; no es autoridad LIGIE/NICO). `suggest` es retrieve-only sobre el dataset oficial y no clasifica.
- RGCE Anexos 1–30, instructivos de pedimento y dumps TIGIE no oficiales (`tigieX`). El cruce es `fraccion8`/`nico10`; Anexo 9 no sustituye `igi_text`

Las notas nacionales LIGIE tienen tablas (`national_note*`, vista `arancel_mx_national_notes`) y un parser HTML. El pipeline oficial ya captura esa fuente oficial DOF. La release publicada `data-2026.08.15` contiene 266 registros. No se inventan instrumentos legales.

Una discrepancia, parser dudoso o gate fallido bloquea la publicación. No hay “publicar de todos modos”.

## Licencia y atribución

El código original del proyecto es **Apache-2.0**. Las publicaciones de la Cámara de Diputados, el DOF y SNICE conservan su propio estatus jurídico; el texto oficial **no** se reliquida como CC0.

La redistribución de bytes oficiales capturados en `official-sources.tar.gz` es para verificación, no una cesión de derechos de esas autoridades.

`arancel-mx` **no constituye asesoría legal**. Consulta las publicaciones oficiales y, cuando corresponda, profesionales especializados.

Véanse [`LICENSE`](../LICENSE), [`NOTICE`](../NOTICE) y [`TERMS.md`](../TERMS.md).

## Documentación relacionada

- [`docs/consumer-quickstart.md`](consumer-quickstart.md) — elegir CLI, Python, DuckDB o API HTTP
- [`docs/official-source-roles.md`](official-source-roles.md) — cuándo usar DOF, SNICE, VUCEM y una release verificable
- [`docs/nico-ligie-guide.md`](nico-ligie-guide.md) — jerarquía HS6, fracción de 8 dígitos y NICO
- [`docs/consumer-cli.md`](consumer-cli.md) — CLI, offline, formatos y `doctor`
- [`docs/data-model.md`](data-model.md) — columnas públicas, vigencia y schema v2
- [`docs/release-process.md`](release-process.md) — publicación fail-closed de `data-*`
- [`docs/sources.md`](sources.md) — Diputados, DOF, SNICE y el contraejemplo SIICEX
