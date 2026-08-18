# Contrato de consumo externo

Guía canónica para aplicaciones que consumen `arancel-mx` mediante releases verificadas, el paquete Python o la API HTTP pública. El proyecto es una capa de datos; no sustituye el pipeline oficial, no clasifica mercancías y no convierte este repositorio en una plataforma aduanera completa.

**[Hub público](https://arancel-mx.vercel.app/)** · **[OpenAPI](https://arancel-mx.vercel.app/docs)** · **[Metadata](https://arancel-mx.vercel.app/v1/meta)** · **[Última release](https://github.com/jccontrerasg08-cpu/arancel-mx/releases/latest)**

## Elige el contrato de consumo

| Caso | Contrato recomendado |
|---|---|
| SQL, BI, ETL o notebooks | DuckDB/CSV/JSON de una release `data-YYYY.MM.DD` |
| Aplicación Python | `Dataset.version("data-YYYY.MM.DD")` |
| Terminal o automatización local | CLI `arancel-mx` |
| Servicio o UI remota | `https://arancel-mx.vercel.app/v1/...` |
| Auditoría | `manifest.json`, `SHA256SUMS`, `provenance` y fuentes capturadas |

El recorrido de ingesta más estricto es:

```text
instalar paquete
  -> resolver una release exacta data-YYYY.MM.DD
  -> descargar
  -> verificar manifest + checksums + DuckDB
  -> consultar
  -> conservar la identidad de la release junto al resultado derivado
```

La versión del paquete Python y la identidad del dataset son independientes. No uses “lo que haya en git” como identidad de datos.

## Instalar y fijar una release

Python 3.11 o superior:

```bash
python -m pip install arancel-mx
arancel-mx --version
arancel-mx doctor
arancel-mx data download --dataset data-YYYY.MM.DD
arancel-mx data verify --dataset data-YYYY.MM.DD
```

En Python:

```python
from arancel_mx import Dataset

db = Dataset.version("data-YYYY.MM.DD")
record = db.lookup("01012101")
print(record.code, record.description)
```

`Dataset.version(...)` fija una release inmutable. `Dataset.latest()` resuelve la release pública más reciente y la verifica antes de abrirla. `Dataset.open(path)` valida un DuckDB local, pero un archivo local que abre correctamente no hereda por sí solo la procedencia de una GitHub Release verificada.

## API HTTP pública

El origen HTTP público canónico es el mismo dominio del hub:

```bash
export ARANCEL_MX_API_URL="https://arancel-mx.vercel.app"
curl "$ARANCEL_MX_API_URL/readyz"
curl "$ARANCEL_MX_API_URL/v1/meta"
curl "$ARANCEL_MX_API_URL/v1/search?q=telefonos&limit=5"
curl "$ARANCEL_MX_API_URL/v1/lookup/8517130100"
```

La documentación interactiva está en [`https://arancel-mx.vercel.app/docs`](https://arancel-mx.vercel.app/docs).

El contrato `/v1` es GET-only y read-only. No requiere API key para las rutas públicas documentadas. `/v1/meta` separa la identidad de la API, la versión del paquete y la release de datos servida.

### Cómo se sirve bajo Vercel

La superficie pública usa una arquitectura híbrida para mantener un solo front door sin duplicar la fuente de verdad:

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

`/v1/meta` y `/v1/search` se resuelven directamente en la capa operacional read-only de Vercel respaldada por Neon. Las demás rutas públicas `/v1/*`, `/docs` y `/readyz` se presentan bajo el mismo dominio mediante **proxy** al runtime FastAPI reusable. La release verificable sigue siendo la fuente canónica; Neon y Vercel son proyecciones/superficies de consumo sincronizadas desde ella.

La producción debe identificar una release verificable y fallar cerrada cuando el dataset requerido no puede cargarse o validarse. No debe inventarse un fallback silencioso que cambie la identidad del dataset servido.

### Endpoints de consumo

La superficie documentada incluye, entre otros:

```text
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
GET /docs
GET /openapi.json
```

El servicio no expone endpoints HTTP de actualización, reconciliación, captura oficial o publicación. Tampoco convierte `search` o `suggest` en una clasificación arancelaria.

## Verificar una release

Orden recomendado para una release `data-YYYY.MM.DD`:

1. Resolver un tag exacto.
2. Ejecutar `arancel-mx doctor`.
3. Descargar con `arancel-mx data download --dataset ...`.
4. Revalidar con `arancel-mx data verify --dataset ...`.
5. Si descargaste todos los assets de GitHub Release al mismo directorio, comprobar `sha256sum -c SHA256SUMS`.
6. Conservar `manifest.json` junto con cualquier dataset o resultado derivado.

Una release válida publica exactamente seis assets:

```text
arancel_mx.duckdb
arancel_mx.csv
arancel_mx.json
manifest.json
SHA256SUMS
official-sources.tar.gz
```

`SHA256SUMS` cubre los otros assets según el contrato de release; `official-sources.tar.gz` conserva los bytes oficiales capturados y su metadata de captura. El modo `--offline` no debe caer silenciosamente a red cuando falta o falla la verificación local.

## Consultar

CLI:

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
```

Python:

```python
from arancel_mx import Dataset

db = Dataset.version("data-YYYY.MM.DD")
record = db.lookup("01012101")
card = db.ficha("01012101")
sources = db.provenance("01012101")
hits = db.search("raza pura")
children = db.children("010121")
```

`search` y `suggest` son retrieve-only. Pueden ayudar a revisar candidatos, pero no publican ni garantizan una clasificación. `compare` y fuentes de apoyo como WCO/VUCEM tampoco sustituyen la identidad legal de LIGIE/NICO.

IGI/IGE deben conservar los literales oficiales publicados por el dataset, por ejemplo `igi_text` y `ige_text`; no deben reinterpretarse como IVA ni convertirse automáticamente a otro impuesto.

### Alias de aplicaciones downstream

Las columnas canónicas usan `fraccion8` para la fracción mexicana de ocho dígitos y `nico10` para el código de diez dígitos. Si una aplicación downstream expone alias en inglés, debe documentar el mapeo y nunca colocar un código de diez dígitos en un campo semánticamente definido como fracción de ocho.

## Autoingesta

Una aplicación puede leer DuckDB, CSV o JSON e insertarlos en Postgres, un warehouse o un servicio propio. Ese almacén downstream no se convierte en la verdad aguas arriba.

Conserva al menos:

- tag `data-YYYY.MM.DD` de origen;
- hash/manifest de la release;
- momento de ingesta downstream;
- cualquier transformación adicional aplicada por la aplicación consumidora.

No ejecutes un scrape paralelo de Diputados/DOF/SNICE y lo presentes como equivalente a una release de `arancel-mx`.

## Mapeo de procedencia

La procedencia se reconstruye desde las columnas por fila, `Dataset.provenance(code)` / `arancel-mx provenance`, `manifest.json` y los bytes incluidos en `official-sources.tar.gz`. No hace falta inventar un séptimo asset para representar la trazabilidad.

Consulta [modelo de datos](data-model.md) y [roles de fuentes oficiales](official-source-roles.md) para la semántica completa.

## Fuera de alcance

No infieras del API o dataset medidas que el contrato no publica. Entre otros, el proyecto no promete por defecto:

- IVA u otros impuestos no modelados;
- permisos, NOM, TLC/T-MEC o PROSEC no declarados en el schema;
- una resolución de clasificación;
- una API de escritura o administración;
- Postgres hospedado como fuente canónica;
- HTML de terceros como identidad legal;
- interpretación jurídica automática de RGCE, MOA u otros instrumentos.

Cuando una capacidad adicional exista, debe estar documentada explícitamente en el schema, API o release correspondiente. La ausencia de un campo nunca debe rellenarse mediante suposición.

## Licencia, fuentes y límites jurídicos

El código original del proyecto es [Apache-2.0](../LICENSE). Las publicaciones de Cámara de Diputados, DOF, SNICE, ANAM u otras autoridades conservan su propio estatus jurídico. La inclusión de bytes capturados para verificación no supone una relicencia de esas publicaciones.

`arancel-mx` **no constituye asesoría legal**. Para clasificación, cumplimiento, importación o exportación consulta las publicaciones oficiales aplicables y, cuando corresponda, profesionales especializados.

## Documentación relacionada

- [Inicio rápido](consumer-quickstart.md): elegir web, CLI, Python, DuckDB o HTTP.
- [CLI de consumo](consumer-cli.md): caché, offline, formatos y comandos.
- [Modelo de datos](data-model.md): columnas, tablas y manifest.
- [Guía NICO/LIGIE](nico-ligie-guide.md): jerarquía de códigos.
- [Roles de fuentes oficiales](official-source-roles.md): autoridad y uso de fuentes.
- [Proceso de release](release-process.md): publicación fail-closed.
- [Visión del proyecto](project-overview.md): arquitectura y fronteras.
- [Centro de documentación](README.md): índice completo por intención.
