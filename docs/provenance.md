# Procedencia y evidencia

La procedencia es parte del contrato de datos, no metadata decorativa. Una fila publicada debe poder relacionarse con documentos fuente concretos y con la ejecución que produjo la release.

## Capas

```text
fuente registrada
  -> documento capturado
  -> parseo / normalización
  -> reconciliación
  -> registro canónico
  -> release
```

## Identidad de una captura

Para una captura oficial se conservan señales como:

```text
authority
source_url
final_url
media_type
byte_size
sha256
retrieved_at
source_document_id
```

`retrieved_at` representa el momento real de descarga. No es fecha de publicación ni entrada en vigor.

## Evidencia legal y fuente estructurada

El proyecto separa funciones de fuente. DOF aporta evidencia de publicación jurídica, Diputados sirve como compilación/ledger legislativo y SNICE aporta datasets estructurados registrados. Una fuente conveniente no adquiere autoridad para todo por el hecho de ser oficial.

VUCEM se está estudiando por separado como cross-check operativo. Consulta [`vucem-characterization.md`](vucem-characterization.md). Durante esa fase no es autoridad de tarifa ni gate de publicación.

## Release

`manifest.json` relaciona el dataset con el registry, commit y ejecución de GitHub Actions. `official-sources.tar.gz` permite reconstruir qué bytes oficiales fueron observados.

La trazabilidad técnica no reemplaza interpretación jurídica ni asesoría profesional.
