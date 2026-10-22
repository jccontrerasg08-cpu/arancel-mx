# CLI de consumo

`arancel-mx` ofrece una línea de comandos pensada primero para consumidores: descarga, verifica, consulta y diagnostica los datasets arancelarios mexicanos publicados sin clonar el repositorio. La CLI de consumo ya está implementada en el paquete y `pip install arancel-mx` es la ruta pública de instalación vigente. Quien contribuya desde un checkout debe usar la instalación editable de desarrollo documentada en el README.

## Instalación y primera ejecución

Se requiere Python 3.11 o posterior.

```bash
pip install arancel-mx
arancel-mx --version
arancel-mx doctor
arancel-mx data download
arancel-mx lookup 01012101
arancel-mx ficha 01012101
arancel-mx compare 01012101
arancel-mx chapters
arancel-mx search "refrigeradores"
arancel-mx suggest "camisas de algodón de punto"
arancel-mx data verify
```

`data download` resuelve una release pública exacta `data-YYYY.MM.DD`, descarga sus assets obligatorios, verifica la integridad y sólo entonces promueve el dataset a la caché local. Una descarga fallida o parcial nunca se promueve como datos utilizables.

## Versión del paquete y versión del dataset

La versión del paquete y la versión del dataset son identificadores independientes.

- **Versión del paquete:** la distribución de Python y la implementación de la CLI, que reporta `arancel-mx --version`. PyPI publica actualmente `0.3.6`. El checkout declara `0.3.7`; los candidatos anteriores `0.3.3`, `0.3.4` y `0.3.5` siguen sólo en TestPyPI y no son elegibles para promoverse a PyPI.
- **Versión del dataset:** una release pública e inmutable de datos arancelarios con nombre `data-YYYY.MM.DD`. `/releases/latest` resuelve actualmente a `data-2026.08.17`.

Actualizar el paquete de Python no reemplaza en silencio una versión de dataset fijada. Publicar una nueva release de datos no exige cambiar la versión del paquete.

Para elegir una release de datos exacta en lugar de la selección predeterminada (la más reciente):

```bash
arancel-mx data download --dataset data-YYYY.MM.DD
arancel-mx lookup 01012101 --dataset data-YYYY.MM.DD
arancel-mx data verify --dataset data-YYYY.MM.DD
arancel-mx suggest "reproductores" --dataset arancel_mx.duckdb
```

`--dataset` también abre un archivo `.duckdb` local (`Dataset.open`). Esa ruta se valida estructuralmente, pero no queda como `release_verified`.

La misma fijación puede darse con `ARANCEL_MX_DATASET`.

## Uso sin conexión

Después de descargar y verificar un dataset, los comandos de consulta pueden funcionar sin acceso a la red:

```bash
arancel-mx lookup 01012101 --offline
arancel-mx search "refrigeradores" --offline
arancel-mx data status --offline --format json
arancel-mx data verify --offline --format json
arancel-mx doctor --offline --json
```

El modo sin conexión es estricto. Sólo usa datos locales verificados y nunca recurre a una petición de red. Si el dataset solicitado no está disponible o falla la verificación local, el comando falla en lugar de descargar otra release.

El modo sin conexión también puede activarse para un proceso o una shell con `ARANCEL_MX_OFFLINE=1`. Los flags explícitos de la CLI tienen prioridad: `--no-offline` fuerza el acceso a la red aunque esa variable de entorno esté definida.

## Salida legible por máquina

Los comandos de consulta y de datos admiten salida determinista en tabla, JSON y CSV cuando aplica.

```bash
arancel-mx lookup 01012101 --format json
arancel-mx search "refrigeradores" --format csv
arancel-mx data status --format json
arancel-mx data list --format csv
arancel-mx data verify --format json
```

Usa `--format json` para automatización estructurada y `--format csv` para intercambio por filas. `data path` imprime a propósito sólo la ruta del DuckDB local seleccionado, para que los scripts la consuman directamente.

## Comandos de consulta

```bash
arancel-mx lookup 01012101
arancel-mx ficha 01012101
arancel-mx compare 010121
arancel-mx compare 01012101
arancel-mx compare 0101210100
arancel-mx chapters
arancel-mx search "refrigeradores" --limit 20
arancel-mx search "camisas de algodón de punto"
arancel-mx suggest "camisas de algodón de punto"
arancel-mx parent 01012101
arancel-mx children 010121
arancel-mx provenance 01012101
arancel-mx wco cite 61
arancel-mx wco download 61
```

| Comando | Qué hace |
|---|---|
| `lookup` | Resuelve un código arancelario normalizado exacto. |
| `ficha` | Devuelve la ficha jerárquica al estilo SIICEX (agrupación por sección, capítulo → partida → subpartida → fracción/NICO, UM, IGI, IGE), sólo a partir del dataset oficial verificado. IGI/IGE son los valores oficiales `igi_text` / `ige_text` (por ejemplo `10` y `Ex.`), no porcentajes reescritos. Los códigos ausentes del snapshot oficial vigente fallan cerrado. |
| `chapters` | Lista los capítulos HS2 vigentes. |
| `search` | Ordena los registros vigentes. El orden por código exacto y por prefijo de código no cambia. Las consultas por descripción ordenan primero los capítulos HS2 que coinciden y después las filas vigentes de esos capítulos. Los resultados incluyen `scorer_version` (`"1"`; se incrementa cuando cambia el orden) y un `confidence` de 0 a 1 para analítica. `search` no es una clasificación. |
| `suggest` | Usa el mismo acotamiento por descripción e imprime la ficha y las notas nacionales de `arancel_mx_national_notes`, cuando esa vista tiene filas (`data-2026.08.15` contiene 266 registros), para los primeros N resultados, con preferencia por `fraccion8`. Ejemplos: `arancel-mx suggest "camisas de algodón de punto"` / `Dataset.suggest(text, limit=5)`. Es retrieve-only: no afirma una clasificación. Clasifica una persona, o su propio modelo; la evidencia permanece en el dataset oficial. |
| `wco cite` | Imprime la URL del PDF del SA 2022 de la OMA (WCO HS 2022) y la ruta en la caché local si existe; nunca descarga. `arancel-mx wco cite gir` cita el PDF de las RGI (GIR). |
| `wco download` | Guarda el PDF en la caché local (`--offline` falla cerrado si falta). Los PDF de la OMA sólo sirven de apoyo de lectura; no son autoridad sobre la LIGIE ni los NICO. |
| `parent` | Devuelve el padre directo en la jerarquía HS2 → HS4 → HS6 → MX8 → NICO10. |
| `children` | Devuelve los hijos directos de un código. |
| `provenance` | Devuelve la trazabilidad de fuente registrada para el código seleccionado. |
| `compare` | Compara un código HS6, MX8 o NICO del dataset `data-*` verificado de GitHub contra la hoja del clasificador de VUCEM (`buildHojas1/{mx8}.html`). HS6 no tiene página en VUCEM, así que se comparan sus hijos MX8/NICO. VUCEM es informativo, no identidad legal. `--offline` omite la consulta al tercero. `compare` es una ayuda de verificación, no un clasificador. |

La capa pública de consumo en Python y la CLI comparten la misma normalización y la misma semántica de consulta.

```python
from arancel_mx import Dataset

dataset = Dataset.latest()  # or Dataset.open("arancel_mx.duckdb")
card = dataset.ficha("01012101")
print(card.formatted_code, card.record.description, card.record.igi_text)
for node in card.hierarchy:
    print(node.level, node.code, node.description)
dataset.suggest("camisas de algodón de punto", limit=5)  # retrieve-only; not a classification
```

## Ciclo de vida del dataset

```bash
arancel-mx data status
arancel-mx data list
arancel-mx data list --remote
arancel-mx data download
arancel-mx data update
arancel-mx data path
arancel-mx data verify
arancel-mx data verify --online
arancel-mx data verify --bundle
```

`data update` es idempotente cuando la release válida más reciente ya está en caché y no borra versiones verificadas anteriores. `data verify` es local por omisión. `--online` compara los metadatos en caché con la release remota exacta. `--bundle` verifica temporalmente el contrato completo de seis assets de la release pública.

## Diagnóstico con `doctor`

Ejecuta el diagnóstico después de instalar o cuando no se pueda consultar un dataset:

```bash
arancel-mx doctor
arancel-mx doctor --json
```

`doctor` revisa los metadatos de la distribución, el entrypoint de consola, la información de Python y plataforma, el registro de fuentes empaquetado, que la caché admita escritura, la verificación del dataset local, el acceso de sólo lectura a DuckDB, una consulta real, la preparación para uso sin conexión y, cuando hay acceso a la red, los metadatos de la release pública.

El contrato de códigos de salida es estable:

| Estado | Código de salida | Significado |
|---|---:|---|
| `HEALTHY` | 0 | Pasaron las verificaciones locales obligatorias y no se detectó ninguna advertencia. |
| `DEGRADED` | 1 | El uso local sigue siendo viable, pero se detectó una condición no fatal, como metadatos remotos no disponibles. |
| `UNHEALTHY` | 2 | Falló una verificación obligatoria de instalación, caché, integridad o consulta. |

`arancel-mx doctor --json` emite el mismo modelo de diagnóstico que la salida legible por personas, con el mismo mapeo de códigos de salida.

## Variables de entorno

Los argumentos explícitos de la CLI o de la API tienen prioridad sobre las variables de entorno, y éstas sobre los valores predeterminados.

| Variable | Uso |
|---|---|
| `ARANCEL_MX_CACHE_DIR` | Reemplaza el directorio de caché multiplataforma del usuario. |
| `ARANCEL_MX_DATASET` | Fija una release exacta `data-YYYY.MM.DD`. |
| `ARANCEL_MX_OFFLINE` | Activa el modo estricto sin conexión con `1`, `true`, `yes` u `on`. |
| `ARANCEL_MX_TIMEOUT` | Define el timeout HTTP en segundos (positivo). |

Raíz de caché predeterminada cuando `ARANCEL_MX_CACHE_DIR` no está definida:

- `XDG_CACHE_HOME/arancel-mx` cuando `XDG_CACHE_HOME` está definida;
- macOS: `~/Library/Caches/arancel-mx`;
- Windows: `%LOCALAPPDATA%/arancel-mx/Cache`;
- en otro caso: `~/.cache/arancel-mx`.

El runtime de consumo no usa `platformdirs`.

Una configuración de consumo inválida falla con un error público accionable en lugar de tratarse como una falla de integridad.

## Integridad y caché

El flujo de consumo es fail-closed:

1. Resuelve una release pública de datos exacta.
2. Descarga a un estado temporal.
3. Verifica el conjunto de assets obligatorio, los valores SHA256, el contrato del manifest y la estructura del DuckDB.
4. Promueve la versión verificada a la caché de forma atómica.
5. Abre el DuckDB seleccionado en sólo lectura para las consultas.

Las descargas concurrentes se serializan con un file lock. Las versiones verificadas existentes siguen disponibles, y un candidato corrupto o incompleto nunca sustituye en silencio a otro dataset.

El contrato de seis assets y las atestaciones del lado de la publicación están en [`release-process.md`](release-process.md). El esquema canónico de la base de datos está en [`data-model.md`](data-model.md).

> `arancel-mx` es una herramienta técnica de datos, no clasifica mercancías y no constituye asesoría legal. Para decisiones de clasificación arancelaria o de cumplimiento, consulta las publicaciones oficiales aplicables y a profesionales calificados.

## Relacionado

- [Consumo externo](external-consumption.md): archivos, Python y API HTTP.
- [Inicio rápido de consumo](consumer-quickstart.md)
- [Modelo de datos](data-model.md)
- [Proceso de release](release-process.md)
- [Release del paquete de Python](package-release.md)
