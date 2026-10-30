# Modelo de datos

## Identificadores

Los documentos fuente y registros canónicos reciben identificadores deterministas derivados de atributos estables. Los hashes SHA256 identifican los bytes capturados; una URL por sí sola no identifica una versión documental.

## Jerarquía arancelaria

Los niveles admitidos son `hs2`, `hs4`, `hs6`, `fraccion8` y `nico10`. Cada código conserva sus componentes padre. Una fracción requiere su HS6 vigente y un NICO requiere su fracción vigente dentro de la misma versión LIGIE.

## Representación de tasas

La importación (`IGI`) y exportación (`IGE`) conservan texto original, tipo normalizado y valor numérico solamente cuando corresponde. Los tipos incluyen tasas ad valorem, exentas, prohibidas, específicas, compuestas y desconocidas. Los niveles HS descriptivos no heredan tasas.

## Vigencia y tiempos de observación

`effective_from` y `effective_to` representan intervalos jurídicos conocidos. `observed_at`, `retrieved_at`, `published_at`, `updated_at` y `generated_at` no son intercambiables.

- `retrieved_at`: **actual fetch time**, la hora real en que el pipeline recuperó los bytes del snapshot oficial.
- `generated_at`: hora de generación del candidato/release reproducible.
- `published_at`: fecha/hora de publicación sólo cuando la fuente o evidencia la proporciona.
- `effective_from` / `effective_to`: intervalo de vigencia legal conocido.

Observar o descargar un documento no permite inventar su fecha de publicación o entrada en vigor. Separar `retrieved_at` de `generated_at` evita convertir la hora del workflow en una propiedad falsa de la fuente.

### Vigencia de la tasa

`rate_effective_from` y `rate_effective_to` dicen desde cuándo y, si es temporal, hasta qué día (inclusive) rige la tasa IGI/IGE vigente de cada fracción. Los NICO heredan las fechas de su fracción, y `effective_from`/`effective_to` del registro las reflejan. Las calcula `arancel_mx.pipeline.rate_validity` a partir de [`legal_instruments.json`](../src/arancel_mx/sources/legal_instruments.json): las filas de la Tarifa de la LIGIE 2022 original (en vigor el 2022-12-12) y de cada instrumento posterior del DOF que fijó tasas generales, extraídas de los PDF del registro de la Cámara de Diputados con `scripts/extract_legal_instruments.py`.

- La tasa en vigor un día es la fila del instrumento más reciente en vigor ese día.
- La vigencia empieza donde comienza el último tramo ininterrumpido con la misma IGI/IGE: la entrada en vigor del instrumento que la fijó, o el día siguiente al fin de una tasa temporal, cuando vuelve la anterior.
- Termina el último día del instrumento que la rige, si es temporal (por ejemplo, 9803.00.01 está exenta del 2026-10-14 al 2031-10-14).

Una fracción queda sin fechas cuando no hay certeza: si la tasa de SNICE no coincide con la de los instrumentos (se reporta como discrepancia) o si la menciona un instrumento que el registro no modela (las tasas escalonadas y tablas sectoriales del decreto del 2022-11-18 y los decretos de exención) y su tasa vendría del texto base. El manifest publica el resumen en `rate_validity`: cuántas fracciones fechó cada instrumento, cuántas quedaron sin fecha y por qué, las discrepancias y la URL y el SHA-256 de cada instrumento. Un cambio del registro genera una release nueva aunque las fuentes no cambien.

### Erratas de la descripción

La descripción de cada fila es la que publica SNICE. Cuando SNICE trae una errata tipográfica que el texto del DOF no tiene, [`description_corrections.json`](../src/arancel_mx/sources/description_corrections.json) registra el texto exacto de SNICE, el corregido y el PDF del DOF (URL y SHA-256) que lo respalda. Sólo admite erratas: nunca reescribe una descripción.

Una corrección aplica únicamente mientras SNICE publique exactamente el texto registrado. Si SNICE la corrige o cambia la descripción, la corrección se omite y aparece como `stale` en `description_corrections` del manifest, junto con las aplicadas. Un cambio del registro también genera una release nueva.

## Procedencia documental

Cada registro canónico señala una fuente primaria y puede incluir evidencia adicional. La procedencia conserva autoridad, URL, hash, papel documental, source role y referencia al registro de fuentes. Las propuestas e indicadores no se presentan como tarifa legal vigente.

La identidad capturada queda vinculada a la versión del registro y a los bytes utilizados por el build, de modo que el contenido publicado pueda auditarse incluso si una URL oficial cambia más tarde.

## Manifest público schema v2

La release pública usa `schema_version: "2"`. El manifest separa metadatos del dataset, identidad de fuentes, reconciliación y procedencia de GitHub Actions.

Entre los campos de procedencia se encuentran:

```text
schema_version
registry_version
registry_sha256
git_commit_sha
github_run_id
github_run_attempt
github_workflow_ref
github_artifact_name
generated_at
```

`registry_sha256` fija la identidad del source registry usado. `github_run_id`, `github_run_attempt`, `github_workflow_ref` y `github_artifact_name` permiten relacionar una release con el artifact exacto validado por Actions.

## DuckDB interno y DuckDB distribuible

El warehouse interno materializa las tablas canónicas (y notas, propuestas e indicadores) antes de copiarlas al DuckDB público.

El archivo público `arancel_mx.duckdb` no es una copia completa de ese warehouse. El exporter crea un DuckDB distribuible nuevo y copia únicamente tablas canónicas o de auditoría pública. El contrato mínimo que la certificación de consumidor exige incluye:

```text
source_document
hs_code
tariff_fraction
nico
tariff_rate
canonical_record
record_provenance
dataset_release
arancel_mx  (vista)
```

También pueden incluirse tablas y vistas públicas para versiones/enmiendas NICO e indicadores cuando forman parte del modelo distribuible.

Las tablas `national_note*` y la vista `arancel_mx_national_notes` existen en el DuckDB público. El pipeline oficial captura la publicación oficial del DOF de notas nacionales, las parsea y las materializa. La release publicada `data-2026.08.15` contiene 266 registros de esa fuente. GIR, notas de sección/capítulo y reglas complementarias no se publican.

`source_registry.json` **no se embebe en el DuckDB público**. La identidad exacta del registry usado para construir una release se conserva en `manifest.json` mediante `registry_version` y `registry_sha256`, y también queda disponible dentro del metadata de release correspondiente. Esta separación evita confundir estado operativo del pipeline con el contrato de consumo del dataset.

La vista pública `arancel_mx` expone códigos, descripción, jerarquía, unidad, tasas, vigencia, versión, estado actual y procedencia verificable. Su orden de columnas se valida contra el contrato canónico `PUBLIC_COLUMNS`.

### Compatibilidad mínima de DuckDB

El paquete declara `duckdb>=1.1`. CI protege esa promesa con una prueba ejecutada, no sólo documental: primero genera un `arancel_mx.duckdb` usando el exporter y el entorno productivo actual, y luego abre ese mismo archivo en modo read-only dentro de un entorno aislado con `duckdb==1.1.0`.

`init_tariff_db` crea cada base con `storage_compatibility_version = 'v1.0.0'`, de modo que el build puede usar DuckDB 2.x y el archivo sigue abriendo en DuckDB 1.1. Un archivo conserva el formato con el que se creó.

La prueba consulta la vista `arancel_mx` y `dataset_release`. Si una futura actualización del DuckDB usado para construir releases deja de producir un archivo consumible por 1.1.0, `CI / test` falla antes de integrar el cambio. El floor sólo debe cambiar mediante un cambio explícito y revisado respaldado por esa evidencia ejecutada.

## `dataset_release.release_metadata_json`

`dataset_release.release_metadata_json` conserva **internal release provenance**. Es metadato interno de materialización y trazabilidad del release, no una columna del contrato tabular público `arancel_mx`.

Puede conservar el contexto necesario para auditar una construcción, por ejemplo versión de manifest, identidad del registry, commit y metadatos de ejecución. La fuente pública de verdad para consumidores externos sigue siendo el bundle verificado y su `manifest.json`; este JSON interno ayuda a reconstruir cómo llegó el warehouse a ese estado.

## Separación entre datos y release

El modelo distingue tres capas:

1. evidencia capturada, con identidad y `retrieved_at`;
2. registros normalizados/reconciliados, con vigencia y procedencia;
3. release, con `generated_at`, schema/provenance y hashes de artefactos.

Esta separación permite que un mismo snapshot observado pueda ser procesado de forma determinista sin atribuirle tiempos o estados legales inferidos únicamente por el momento del build.
