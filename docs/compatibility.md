# Compatibilidad y evolución de superficies públicas

Esta política define cómo `arancel-mx` conserva contratos utilizables para consumidores de datos sin transformar el proyecto en una autoridad regulatoria. El proyecto es una herramienta técnica de datos: **no clasifica mercancías**, no confirma origen, no liquida contribuciones y no genera pedimentos.

## Ventana de Python y distribución

El metadato de distribución declara `requires-python = ">=3.11"`. Las releases de paquete certifican actualmente **CPython 3.11–3.13** en la matriz de publicación definida en [la guía de release](package-release.md). El entorno de despliegue configurado en `.python-version` usa Python 3.13. Python 3.14 y posteriores no se declaran compatibles hasta que una matriz de certificación los incluya explícitamente.

| Superficie | Contrato de estabilidad | Evidencia de cambio |
|---|---|---|
| Biblioteca `arancel_mx` | Las importaciones y firmas documentadas cambian de forma aditiva por defecto. | Prueba de regresión, changelog y, si afecta varias fronteras, una decisión registrada. |
| CLI `arancel-mx` | Los comandos y salidas documentadas no se eliminan silenciosamente. | Prueba de CLI, guía de consumo y entrada en `CHANGELOG.md`. |
| HTTP read-only bajo `/v1` | Las rutas, campos y semántica publicada no se retiran sin transición documentada. | Contrato de API, prueba de ruta y changelog. |
| Dataset y release | Los contratos públicos de DuckDB, CSV, JSON, manifest y PUBLIC_COLUMNS evolucionan de forma aditiva por defecto; identidad, procedencia y validación permanecen separadas de los contratos de ejecución. | Manifest certificado, prueba de release y changelog con transición de esquema. |

## Cambios compatibles y deprecaciones

Los cambios aditivos son el camino predeterminado. Antes de una modificación incompatible de biblioteca, CLI o `/v1`, el cambio debe describir la alternativa, el impacto y la estrategia de migración en la pull request y en `CHANGELOG.md`.

Una retirada futura debe seguir una de estas dos formas:

1. Para biblioteca `arancel_mx`, cuando exista una alternativa ejecutable, conservar la superficie anterior durante una ventana anunciada y emitir `DeprecationWarning` que incluya el reemplazo y la **versión objetivo de retirada**. La advertencia debe tener una prueba que compruebe categoría, texto y `stacklevel`.
2. Para CLI, el comando retirado debe emitir un aviso `DEPRECATION:` observable por `stderr`, indicar el reemplazo y reflejarlo en `--help` cuando proceda. Para HTTP `/v1`, la ruta retirada debe emitir los encabezados `Deprecation` y `Sunset` cuando haya fecha de retirada, además de un enlace al reemplazo y la entrada correspondiente de `CHANGELOG.md`. Los campos de respuesta se sustituyen mediante una alternativa aditiva documentada antes de eliminarse.
3. Cuando una superficie siga siendo segura pero deje de evolucionar, documentarla como *soft deprecation* sin advertencia en runtime. La documentación debe indicar el reemplazo, el alcance y el criterio para una futura retirada.

Este flujo adapta el principio de compatibilidad de [PEP 387](https://peps.python.org/pep-0387/): las interfaces públicas requieren aviso y una ruta de migración antes de un cambio incompatible. Cuando una anotación estática pueda comunicar la deprecación sin alterar el runtime, se puede evaluar el patrón de [PEP 702](https://peps.python.org/pep-0702/) en una mejora posterior.

## Límites de esta política

La política no fija plazos de validez arancelaria, no interpreta normas, ni convierte cambios de dataset en decisiones jurídicas. Cualquier cambio de fuentes oficiales conserva el pipeline de evidencia, reconciliación y publicación certificada existente.

## Verificación de contribuciones

Para cambios de compatibilidad, ejecuta el contrato correspondiente y añade una prueba de regresión antes de abrir la pull request. La guía de contribución enlaza esta política; el [hub documental](README.md) la presenta junto con las guías de consumo y release.

## Referencias

[1] [PEP 387 — Backwards Compatibility Policy](https://peps.python.org/pep-0387/)

[2] [PEP 702 — Marking deprecations using the type system](https://peps.python.org/pep-0702/)
