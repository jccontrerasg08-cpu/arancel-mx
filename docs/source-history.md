# Historial certificado de fuentes oficiales

## Alcance actual

Cada release inmutable de datos contiene un manifiesto certificado. Cuando el pipeline semanal detecta una identidad de fuente distinta de la release certificada anterior, el manifiesto incorpora `source_history` dentro de sus metadatos de release.

El resumen conserva la versión anterior y un diff determinista por `dataset_key` y `document_role`. Cada cambio es `added`, `removed` o `updated`, y conserva tanto la identidad anterior como la actual: URL de origen, SHA-256 y versión del registro de fuentes. El historial se muestra en la página pública **Release changes**, donde cada versión enlaza a su release inmutable y a sus artefactos verificables.

Este mecanismo no escribe datos si falta evidencia requerida o si la reconciliación legal no es publicable. Una ejecución sin cambios no crea una release nueva; por ello, el historial describe cambios de fuentes que llegaron a una release certificada, no cada sondeo técnico.

## Revisión semanal

El flujo `official-data-pipeline.yml` ejecuta el pipeline semanal los lunes a las 11:17 UTC. Puede lanzarse manualmente como vista previa. La publicación automática queda limitada a una release construida, certificada y reconciliada correctamente.

## Ampliación diaria futura

Una detección diaria puede aportar aviso temprano sin alterar este límite de confianza. Debe implementarse como un flujo independiente de sólo lectura que:

1. Capture las mismas fuentes registradas y calcule sus identidades.
2. Compare esas identidades con el último manifiesto certificado.
3. Publique únicamente un diagnóstico o actualice una alerta cuando observe una diferencia.
4. No genere releases, no cambie artefactos y no active datos.
5. Deje que el pipeline semanal certificado, o una ejecución manual revisada, sea el único camino de publicación.

Antes de habilitar esa ampliación se deben conservar los mismos límites de host, validación de media type, reintentos y controles de concurrencia del pipeline principal.

## Uso por integradores

Los integradores deben fijar un tag `data-YYYY.MM.DD`, descargar el `manifest.json`, verificar `SHA256SUMS` y tratar `source_history` como una explicación de diferencia, no como una interpretación normativa. La vigencia y aplicabilidad de una medida deben verificarse siempre contra la fuente primaria enlazada.
