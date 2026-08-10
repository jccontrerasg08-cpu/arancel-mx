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

## Tablas DuckDB

Las tablas principales son `source_registry`, `source_document`, `hs_code`, `tariff_fraction`, `nico`, `tariff_rate`, `canonical_record`, `record_provenance` y `dataset_release`. Tablas separadas conservan enmiendas NICO, notas nacionales, indicadores y evidencia de conciliación sin mezclarlas con `arancel_mx`.

La vista pública `arancel_mx` expone códigos, descripción, jerarquía, unidad, tasas, vigencia, versión, estado actual y procedencia verificable.

## `dataset_release.release_metadata_json`

`dataset_release.release_metadata_json` conserva **internal release provenance**. Es metadato interno de materialización y trazabilidad del release, no una columna del contrato tabular público `arancel_mx`.

Puede conservar el contexto necesario para auditar una construcción, por ejemplo versión de manifest, identidad del registry, commit y metadatos de ejecución. La fuente pública de verdad para consumidores externos sigue siendo el bundle verificado y su `manifest.json`; este JSON interno ayuda a reconstruir cómo llegó el warehouse a ese estado.

## Separación entre datos y release

El modelo distingue tres capas:

1. evidencia capturada, con identidad y `retrieved_at`;
2. registros normalizados/reconciliados, con vigencia y procedencia;
3. release, con `generated_at`, schema/provenance y hashes de artefactos.

Esta separación permite que un mismo snapshot observado pueda ser procesado de forma determinista sin atribuirle tiempos o estados legales inferidos únicamente por el momento del build.
