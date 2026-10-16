# Historial certificado de fuentes oficiales

Este documento explica cómo cada release de datos registra qué fuentes oficiales cambiaron respecto de la anterior y cómo se vigila a diario el DOF. Está dirigido a integradores que necesitan explicar una diferencia entre dos releases y a mantenedores que revisan alertas de fuentes.

## Historial en el manifest

Cada release inmutable de datos contiene un `manifest.json` certificado. Cuando el pipeline diario detecta una identidad de fuente distinta de la release certificada anterior, el manifest incorpora `source_history` dentro de sus metadatos de release.

El resumen conserva la versión anterior y un diff determinista por `dataset_key` y `document_role`. Cada cambio es `added`, `removed` o `updated`, y conserva tanto la identidad anterior como la actual: URL de origen, SHA-256 y versión del registro de fuentes. El historial se muestra en la página pública `/changes`, donde cada versión enlaza a su release inmutable y a sus artefactos verificables.

Este mecanismo no escribe datos si falta evidencia requerida o si la reconciliación legal no es publicable. Una ejecución sin cambios termina como `no_change` y no crea una release nueva; por ello, el historial describe cambios de fuentes que llegaron a una release certificada, no cada sondeo técnico.

## Revisión diaria

El workflow **Official data pipeline** (`.github/workflows/official-data-pipeline.yml`) corre todos los días a las 11:17 UTC (cron `17 11 * * *`, [decisión 0002](decisions/0002-arquitectura-github-primero.md)). Cada ejecución hace dos revisiones independientes:

1. **Fuentes registradas.** El job `build-and-verify` captura las fuentes del registro, calcula sus identidades y las compara con el último manifest certificado. Si no cambiaron, termina como `no_change`; si cambiaron, construye, certifica y publica una release nueva.
2. **Vigilancia del DOF.** El job `notify` ejecuta `scripts/watch_dof.py`, que consulta los servicios web oficiales de SIDOF para los últimos siete días del DOF, de modo que una ejecución perdida la cubre la siguiente. Por cada nota con título arancelario nueva abre un issue con la etiqueta `dof-candidate` para revisión humana.

La vigilancia del DOF es de sólo lectura: no construye, no cambia ni publica datos. El issue es el paso de confirmación humana; un instrumento confirmado llega al dataset sólo cuando sus fuentes registradas cambian y el pipeline certifica una release nueva. En ejecuciones manuales con `publish=false` o fuera de `main`, la vigilancia sólo informa y no abre issues.

Ambas revisiones usan los mismos límites del pipeline: allowlist de hosts, validación de media type, reintentos acotados y un único grupo de concurrency para las ejecuciones de producción.

## Uso por integradores

Los integradores deben fijar un tag `data-YYYY.MM.DD`, descargar el `manifest.json`, verificar `SHA256SUMS` y tratar `source_history` como una explicación de diferencia, no como una interpretación normativa. La vigencia y aplicabilidad de una medida deben verificarse siempre contra la fuente primaria enlazada. `arancel-mx` no clasifica mercancías ni constituye asesoría legal.

## Relacionado

- [Proceso de release](release-process.md)
- [Fuentes y reconciliación](sources.md)
- [Arquitectura](architecture.md)
- [Decisión 0002](decisions/0002-arquitectura-github-primero.md)
