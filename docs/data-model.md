# Modelo de datos

## Identificadores

Los documentos fuente y registros canónicos reciben identificadores deterministas derivados de sus atributos estables. Los hashes SHA-256 identifican los bytes capturados; una URL por sí sola no identifica una versión documental.

## Jerarquía arancelaria

Los niveles admitidos son `hs2`, `hs4`, `hs6`, `fraccion8` y `nico10`. Cada código conserva sus componentes padre. Una fracción requiere su HS6 vigente y un NICO requiere su fracción vigente dentro de la misma versión LIGIE.

## Representación de tasas

La importación (`IGI`) y exportación (`IGE`) conservan texto original, tipo normalizado y valor numérico solamente cuando corresponde. Los tipos incluyen tasas ad valorem, exentas, prohibidas, específicas, compuestas y desconocidas. Los niveles HS descriptivos no heredan tasas.

## Vigencia

`effective_from` y `effective_to` representan intervalos jurídicos conocidos. `observed_at`, `retrieved_at`, `published_at` y `updated_at` tienen significados distintos; observar un documento no permite inventar su fecha de publicación o entrada en vigor.

## Procedencia

Cada registro canónico señala una fuente primaria y puede incluir evidencia adicional. La procedencia conserva autoridad, URL, hash, papel documental y referencia al registro de fuentes. Las propuestas e indicadores no se presentan como tarifa legal vigente.

## Tablas DuckDB

Las tablas principales son `source_registry`, `source_document`, `hs_code`, `tariff_fraction`, `nico`, `tariff_rate`, `canonical_record`, `record_provenance` y `dataset_release`. Tablas separadas conservan enmiendas NICO, notas nacionales, indicadores y evidencia de conciliación sin mezclarlas con `arancel_mx`.

La vista pública `arancel_mx` expone códigos, descripción, jerarquía, unidad, tasas, vigencia, versión, estado actual y procedencia verificable.
