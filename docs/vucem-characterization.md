# Caracterización del Clasificador Arancelario VUCEM

Esta herramienta estudia el **Clasificador Arancelario de VUCEM como cross-check operativo independiente**. No convierte a VUCEM en autoridad de tarifa, no modifica `source_registry` y no participa en el gate de publicación del dataset.

El contrato de seguridad durante esta fase es explícito:

```text
authoritative_for_tariff = false
publication_gate = false
```

La fuente estructurada de referencia continúa siendo el dataset canónico respaldado por las fuentes registradas del proyecto. La publicación jurídica y vigencia continúan sujetas a la evidencia oficial correspondiente, especialmente DOF.

## Objetivo de la fase

Antes de proponer cualquier entrada de VUCEM en `source_registry`, se requiere una caracterización reproducible de **100+ fracciones MX8** que permita responder al menos:

1. ¿Qué cobertura real tiene el patrón de páginas del Clasificador?
2. ¿La estructura HTML es estable o existen varios esquemas?
3. ¿La fracción consultada aparece de forma consistente en la página?
4. ¿Qué tanto coincide la descripción observada con la descripción de referencia?
5. ¿Qué diferencias aparecen por capítulo?
6. ¿Cuántos `schema_fingerprint` distintos aparecen?
7. ¿Cuál es el **update lag** de VUCEM frente a cambios conocidos de la fuente estructurada?

Esta fase es investigación de fuente. Una tasa, descripción o vigencia observada en VUCEM no puede por sí sola volver publicable un registro ni sustituir el pipeline de reconciliación actual.

## Entradas

El script usa un `arancel_mx.csv` validado como universo de referencia y toma únicamente filas `fraccion8`. El muestreo es determinista y round-robin por capítulo para evitar que 120 observaciones terminen concentradas en unas pocas familias arancelarias.

Patrón actualmente caracterizado:

```text
https://www.ventanillaunica.gob.mx/Clasificador/data/buildHojas1/{fraccion8}.html
```

## Dry run

Primero inspecciona qué fracciones serían consultadas sin acceder a VUCEM:

```bash
python scripts/characterize_vucem.py \
  --snice-csv path/to/arancel_mx.csv \
  --output out/vucem-characterization.json \
  --sample-size 120 \
  --dry-run
```

El dry run escribe las URLs planeadas y conserva:

```text
source_role = independent_operational_cross_check
authoritative_for_tariff = false
publication_gate = false
```

## Caracterización live

Cuando se quiera realizar la muestra real:

```bash
python scripts/characterize_vucem.py \
  --snice-csv path/to/arancel_mx.csv \
  --output out/vucem-characterization.json \
  --sample-size 120
```

Opciones de red disponibles:

```text
--timeout 20
--max-bytes 2097152
--delay-ms 100
```

La descarga reutiliza el boundary HTTP estricto del proyecto: HTTPS, allowlist de host, `text/html`, límite de tamaño y rechazo de redirect fuera de VUCEM.

## Qué registra cada página

Para cada fracción se preserva información suficiente para auditar la observación:

```text
code
chapter
requested_url
final_url
media_type
retrieved_at
sha256
byte_size
page_title
headings
code_present
snice_description_present
snice_description_token_coverage
schema_fingerprint
```

`schema_fingerprint` se deriva de señales estructurales del HTML, entre ellas tags, tablas, filas, celdas, forms, scripts, IDs y clases. No es un identificador jurídico. Sirve para detectar cambios o variantes de estructura que deban estudiarse antes de escribir un parser formal.

La comparación de descripción incluye una coincidencia normalizada exacta y una cobertura de tokens. Estos campos son señales diagnósticas, no una decisión de equivalencia jurídica.

## Resumen de cobertura

El reporte agrega:

```text
fetched
errors
coverage_rate
code_match_rate
description_exact_match_rate
mean_description_token_coverage
chapters_sampled
unique_schema_fingerprints
```

`registry_review_ready` sólo puede ser `true` cuando al menos 100 páginas fueron recuperadas exitosamente. No significa que VUCEM deba entrar al registro. Significa únicamente que existe el mínimo de observaciones pedido para iniciar una revisión humana de la caracterización.

## Cómo evaluar update lag

Una ejecución aislada no permite medir update lag. Para hacerlo de manera defendible:

1. conserva el JSON de una ejecución caracterizada;
2. identifica un cambio posterior confirmado por las fuentes registradas y su fecha relevante;
3. repite la muestra alrededor de las fracciones modificadas;
4. compara `retrieved_at`, contenido, SHA256 y descripciones entre ejecuciones;
5. registra cuándo VUCEM refleja por primera vez el cambio;
6. no conviertas el resultado en una fecha legal de vigencia.

## Gate para una futura propuesta al registry

Una propuesta separada para incorporar VUCEM a `source_registry` sólo debe considerarse después de revisar:

- muestra live de 100+ páginas válidas;
- distribución razonable entre capítulos;
- cobertura y tipos de error;
- estabilidad de `schema_fingerprint`;
- correspondencia de códigos y descripciones;
- comportamiento ante páginas inexistentes o cambiantes;
- evidencia de update lag a partir de cambios reales;
- términos de uso/licencia y límites de redistribución aplicables;
- tests offline con fixtures sanitizados.

Incluso después de esa revisión, la propuesta debe conservar como mínimo:

```text
authoritative_for_tariff = false
publication_gate = false
```

Cualquier cambio futuro de esas dos propiedades necesitaría justificación independiente, tests y revisión explícita. Esta herramienta no realiza ese cambio.
