# Contrato de consumo externo

Esta es la guía canónica para aplicaciones que consumen `arancel-mx` mediante releases verificadas, Python, CLI o la API HTTP pública. El **front door público** es [`https://arancel-mx.vercel.app/`](https://arancel-mx.vercel.app/), mientras GitHub Releases conserva la identidad canónica del dataset.

**[Hub](https://arancel-mx.vercel.app/)** · **[OpenAPI](https://arancel-mx.vercel.app/docs)** · **[Metadata](https://arancel-mx.vercel.app/v1/meta)** · **[Última release](https://github.com/jccontrerasg08-cpu/arancel-mx/releases/latest)**

## Qué es y qué no es arancel-mx

`arancel-mx` es una capa técnica y reproducible para consultar LIGIE/NICO y su procedencia. Publica artefactos verificables, una API Python, una CLI y una API HTTP GET-only/read-only.

No es un motor de clasificación, una resolución aduanera ni asesoría legal. `search`, `suggest`, `compare` y las fuentes auxiliares ayudan a recuperar o contrastar evidencia; no convierten un resultado en una determinación jurídica.

| Necesidad | Contrato recomendado |
|---|---|
| SQL, BI, ETL o notebooks | DuckDB/CSV/JSON de una release `data-YYYY.MM.DD` |
| Aplicación Python | `Dataset.version("data-YYYY.MM.DD")` |
| Terminal o automatización local | CLI `arancel-mx` |
| Servicio o UI remota | `https://arancel-mx.vercel.app/v1/...` |
| Auditoría | `manifest.json`, `SHA256SUMS`, `provenance` y fuentes capturadas |

## Instalar y fijar versiones

Python 3.11 o superior:

```bash
python -m pip install arancel-mx
arancel-mx --version
arancel-mx doctor
arancel-mx data download --dataset data-YYYY.MM.DD
arancel-mx data verify --dataset data-YYYY.MM.DD
```

La versión del paquete y la versión de los datos son identidades distintas. El estado exacto de publicación del paquete vive en [package-release.md](package-release.md); esta guía evita fijar una versión “latest” que se vuelva obsoleta.

En Python:

```python
from arancel_mx import Dataset

# Release inmutable y explícita.
db = Dataset.version("data-YYYY.MM.DD")
record = db.lookup("01012101")
print(record.code, record.description)
```

- `Dataset.version(...)` fija una release pública inmutable.
- `Dataset.latest()` resuelve la release pública más reciente y la verifica antes de abrirla.
- `Dataset.open(path)` abre un DuckDB local y valida su estructura, pero no lo marca automáticamente como `release_verified`.

El dataset no viene embebido en el wheel. Una actualización del paquete no cambia silenciosamente una release fijada.

## Verificar

El flujo de consumo es **fail-closed**:

```text
resolver una release exacta
  → descargar a estado temporal
  → verificar manifest + SHA256 + estructura DuckDB
  → promover al cache sólo si todo pasó
  → abrir read-only
```

Una release válida publica exactamente seis assets:

```text
arancel_mx.duckdb
arancel_mx.csv
arancel_mx.json
manifest.json
SHA256SUMS
official-sources.tar.gz
```

`manifest.json` usa **schema v2** y conserva identidad de dataset, fuentes, hashes y procedencia de ejecución. Si descargaste los seis assets al mismo directorio, puedes verificar el bundle con:

```bash
sha256sum -c SHA256SUMS
```

La CLI aplica el mismo contrato:

```bash
arancel-mx doctor --dataset data-YYYY.MM.DD
arancel-mx data download --dataset data-YYYY.MM.DD
arancel-mx data verify --dataset data-YYYY.MM.DD
```

El `cache` sólo promueve una descarga después de verificarla. `--offline` es estricto: si falta el dataset solicitado o la verificación local falla, no hay fallback silencioso a red ni a otra versión.

Los errores públicos permiten manejar fallos de forma explícita. Por ejemplo, `RecordNotFoundError` representa un código inexistente en el dataset seleccionado; los errores de descarga, schema o integridad pertenecen a la jerarquía pública de errores de dataset.

## Consultar

### CLI

```bash
arancel-mx lookup 01012101
arancel-mx ficha 01012101
arancel-mx search "refrigeradores"
arancel-mx suggest "camisas de algodón de punto"
arancel-mx chapters
arancel-mx parent 01012101
arancel-mx children 010121
arancel-mx provenance 01012101
arancel-mx compare 01012101
arancel-mx wco cite 01
```

`search` y `suggest` son retrieve-only. `compare` contrasta el dataset verificado con la superficie VUCEM correspondiente cuando aplica; es una ayuda de verificación, no un clasificador.

### Python

```python
from arancel_mx import Dataset

db = Dataset.version("data-YYYY.MM.DD")
record = db.lookup("01012101")
card = db.ficha("01012101")
sources = db.provenance("01012101")
comparison = db.compare("01012101")
```

La superficie pública reexporta modelos de lectura como `TariffRecord`, `Ficha`, `ProvenanceRecord`, `SearchResult`, `DatasetInfo`, `HsSection` y `CompareRow`. Usa esos tipos en vez de depender de estructuras internas del DuckDB cuando necesites un contrato Python estable.

Los campos canónicos usan `fraccion8` para la fracción mexicana y `nico10` para el código completo. Si una aplicación downstream expone aliases como `fraction8` o `classification10`, debe documentar el mapeo y no mezclar semánticas de ocho y diez dígitos.

IGI/IGE se conservan como literales oficiales, por ejemplo `igi_text` y `ige_text`; no se reinterpretan automáticamente como otros impuestos.

### Goldens documentales, no consultas live

Los siguientes ejemplos existen para fijar semántica de tests y documentación. **No son una promesa de vigencia futura ni una instrucción de clasificación.**

- El fixture `01012101` tiene un hijo NICO `0101210100`; en ese golden `igi_text` es `10` y `ige_text` es `Ex.`.
- El ejemplo histórico SIICEX `11063001` para harina de sagú **no está** en el snapshot oficial usado por la comparación documental y debe fallar cerrado. El par vigente documentado para sagú es `11062002`, con literal IGI `10`. La fuente y el contexto completo están en [sources.md](sources.md).

### API HTTP pública

Usa un solo origen público:

```bash
export ARANCEL_MX_API_URL="https://arancel-mx.vercel.app"
curl "$ARANCEL_MX_API_URL/readyz"
curl "$ARANCEL_MX_API_URL/v1/meta"
curl "$ARANCEL_MX_API_URL/v1/search?q=telefonos&limit=5"
curl "$ARANCEL_MX_API_URL/v1/lookup/8517130100"
```

La documentación interactiva está en [`/docs`](https://arancel-mx.vercel.app/docs). La superficie `/v1` pública es **GET-only**, **read-only** y no requiere API key para las rutas documentadas.

La arquitectura pública es híbrida sin duplicar la fuente de verdad:

```text
GitHub Release verificada
          ↓
sincronización operacional
          ↓
        Neon
          ↓
Vercel: /v1/meta + /v1/search

Vercel: /v1/* restante + /docs + /readyz
          ↓ proxy
   runtime FastAPI reusable
```

`/v1/meta` y `/v1/search` se resuelven en la capa operacional read-only de Vercel respaldada por Neon. Las demás rutas se presentan bajo el mismo dominio mediante proxy al runtime FastAPI. **Vercel y Neon son superficies de servicio; la GitHub Release verificada sigue siendo la fuente canónica.**

## Autoingesta

Una aplicación puede cargar DuckDB, CSV o JSON en Postgres, un warehouse u otro almacén propio. Esa copia downstream no se convierte en la fuente upstream.

Conserva, como mínimo:

- tag `data-YYYY.MM.DD` de origen;
- `manifest.json` y checksums de la release;
- momento de ingesta downstream;
- transformaciones adicionales aplicadas por tu sistema.

No ejecutes un scrape paralelo de Diputados/DOF/SNICE y lo presentes como equivalente a una release de `arancel-mx`.

## Mapeo de procedencia

La trazabilidad se reconstruye desde las columnas por fila, `Dataset.provenance(code)` / `arancel-mx provenance`, `manifest.json` y los bytes preservados en `official-sources.tar.gz`.

No hace falta inventar un séptimo asset para representar procedencia. Para el schema exacto consulta [data-model.md](data-model.md), y para roles/autoridad de fuente consulta [official-source-roles.md](official-source-roles.md) y [sources.md](sources.md).

## Fuera de alcance

No infieras del dataset o de la API medidas que el contrato no publica. Entre otros, `arancel-mx` no publica por defecto:

- IVA, GIR u otros conceptos que no estén modelados como campos del dataset;
- NOM, permisos, franja/región, TLC/T-MEC o PROSEC como un motor de cumplimiento;
- una resolución de clasificación;
- una API de escritura o administración;
- Postgres/Neon como fuente canónica del dataset;
- SIICEX, VUCEM, RGCE o dumps `tigieX` como sustitutos de la identidad LIGIE/NICO de la release;
- interpretación jurídica automática de fuentes auxiliares.

VUCEM puede participar como superficie informativa de contraste y RGCE puede ser relevante para un caso jurídico, pero eso no significa que sus contenidos completos formen parte del schema publicado por este proyecto.

La ausencia de un campo nunca debe rellenarse mediante suposición.

## Licencia y atribución

El código original se distribuye bajo [Apache-2.0](../LICENSE). Revisa también [NOTICE](../NOTICE) y [TERMS.md](../TERMS.md).

Las publicaciones de Cámara de Diputados, DOF, SNICE, ANAM u otras autoridades conservan su propio estatus jurídico. Preservar bytes capturados para verificación no implica relicenciar las publicaciones oficiales.

`arancel-mx` **no constituye asesoría legal**. Para clasificación, cumplimiento, importación o exportación consulta las publicaciones oficiales aplicables y, cuando corresponda, profesionales especializados.

## Documentación relacionada

- [Inicio rápido](consumer-quickstart.md): elegir web, CLI, Python, DuckDB o HTTP.
- [CLI de consumo](consumer-cli.md): comandos, caché, offline y formatos.
- [Modelo de datos](data-model.md): tablas, tipos y manifest.
- [Guía NICO/LIGIE](nico-ligie-guide.md): jerarquía HS → fracción → NICO.
- [Roles de fuentes oficiales](official-source-roles.md): función de cada publicación.
- [Fuentes y reconciliación](sources.md): cadena de confianza y goldens de contraste.
- [Proceso de release](release-process.md): publicación autónoma y fail-closed.
- [Release del paquete](package-release.md): estado PyPI/TestPyPI y separación código/datos.
- [Visión del proyecto](project-overview.md): arquitectura y fronteras.
- [Centro de documentación](README.md): índice completo por intención.
