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

Las tablas `national_note*` y la vista `arancel_mx_national_notes` existen en el DuckDB público. El parser HTML de notas nacionales está en el paquete. La release `data-2026.08.11` no incluye `national_notes` en `source_identity`, así que esa vista puede estar vacía. GIR, notas de sección/capítulo y reglas complementarias no se publican.

`source_registry.json` **no se embebe en el DuckDB público**. La identidad exacta del registry usado para construir una release se conserva en `manifest.json` mediante `registry_version` y `registry_sha256`, y también queda disponible dentro del metadata de release correspondiente. Esta separación evita confundir estado operativo del pipeline con el contrato de consumo del dataset.

La vista pública `arancel_mx` expone códigos, descripción, jerarquía, unidad, tasas, vigencia, versión, estado actual y procedencia verificable. Su orden de columnas se valida contra el contrato canónico `PUBLIC_COLUMNS`.

### Compatibilidad mínima de DuckDB

El paquete declara `duckdb>=1.1`. CI protege esa promesa con una prueba ejecutada, no sólo documental: primero genera un `arancel_mx.duckdb` usando el exporter y el entorno productivo actual, y luego abre ese mismo archivo en modo read-only dentro de un entorno aislado con `duckdb==1.1.0`.

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
