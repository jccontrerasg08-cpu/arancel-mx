# Promoción de snapshots desde `SNICE_DOCS`

`arancel-mx` usa una política de **promoción agresiva con evidencia** para los snapshots estructurados de LIGIE y NICO. Además de las páginas canónicas de SNICE, el registro versionado permite descubrir candidatos en el índice público [`~oracle/SNICE_DOCS`](https://www.snice.gob.mx/~oracle/SNICE_DOCS/). Un archivo más reciente puede ser seleccionado antes de que la página canónica se actualice, pero nunca se publica sólo por aparecer en ese directorio.[1]

> La promoción acelera la detección de una actualización operativa oficial. No convierte el directorio en autoridad jurídica autónoma ni autoriza la creación de códigos NICO que el origen oficial no publique.

![Flujo de promoción desde SNICE_DOCS](assets/source-promotion.png)

La fuente versionada del diagrama es [`assets/source-promotion.mmd`](assets/source-promotion.mmd).

## Criterios de elegibilidad

Un candidato del corpus sólo entra a la selección si cumple todos los criterios siguientes.

| Gate | Regla | Motivo |
|---|---|---|
| Índice permitido | El índice está declarado en `corpus_index_pages` del registro versionado. | Evita descubrimiento desde directorios o hosts arbitrarios. |
| Host HTTPS permitido | La URL final pertenece a los hosts oficiales de SNICE configurados. | Bloquea redirecciones o fuentes externas. |
| Familia y tipo válidos | El nombre coincide con la familia LIGIE/NICO y el tipo de medio permitido. | Evita propuestas, indicadores o documentos de otra clase. |
| Fecha verificable | El nombre o título contiene una fecha válida de ocho dígitos. | Un archivo no fechado no puede desplazar un snapshot publicado. |
| Ganador único | El candidato tiene la fecha más reciente y no empata con otra URL. | No se elige por heurística cuando existe ambigüedad. |
| Captura verificable | Se descargan los bytes, se registra SHA256 y se conserva `retrieved_at`. | Deja evidencia reproducible de lo observado. |
| Validación y reconciliación | Parsers, validación estructural y reconciliación Diputados/DOF deben aprobar. | La aparición de un archivo no salta los gates del pipeline. |

El snapshot descubierto desde el corpus conserva `discovery_url` y `discovery_kind: "corpus_index"` en el capture metadata y en `official-sources/source_capture.json`. Si el mismo archivo está enlazado tanto por la página canónica como por el corpus, se conserva la procedencia de la página canónica.

## Qué puede promoverse

La configuración aplica únicamente a `ligie/ligie_snapshot` y `nico/nico_snapshot`. No aplica a propuestas NICO, indicadores, notas nacionales, el ledger de Diputados ni documentos DOF. Las familias permitidas están declaradas en [`source_registry.json`](../src/arancel_mx/sources/source_registry.json), no inferidas desde el nombre de cualquier archivo.

| Rol | Familia permitida | Ejemplo de resultado |
|---|---|---|
| `ligie_snapshot` | `FRACCIONESARANCELARIAS*.xls[x]` | Nuevo workbook de fracciones para validación integral. |
| `nico_snapshot` | `NICO-*.xls[x]`, excluyendo `SOLICITUD-*` | Nuevo workbook oficial NICO para validación integral. |
| `nico_proposals` | `SOLICITUD-NICO*.xls[x]` | Contexto o propuesta; nunca sustituye un NICO publicado. |

## NICO y lag de publicación

Una LIGIE más reciente puede contener fracciones vigentes sin descendientes NICO porque la publicación NICO registrada todavía no se ha actualizado. El pipeline conserva esa situación observada y no inventa NICO `00`. El trabajo de cobertura y clasificación de faltantes se registra en [issue #110](https://github.com/jccontrerasg08-cpu/arancel-mx/issues/110).[2]

La ausencia de un NICO no es, por sí sola, una autorización para publicar datos fabricados ni una razón universal para invalidar una fuente oficial que todavía está rezagada. Los reportes de cobertura deben distinguir lag aguas arriba, pérdida de datos inesperada y casos especiales con evidencia.

## Rollback y recuperación

Las releases publicadas son inmutables. Si una promoción resulta incorrecta o insuficiente, no se edita una release existente. La recuperación es una nueva ejecución validada con una corrección revisable.

| Situación | Acción de recuperación |
|---|---|
| El directorio expone candidatos ambiguos | El pipeline falla cerrado; investigar antes de alterar el registro. |
| Una familia produjo un falso positivo | Ajustar el patrón en `source_registry.json`, incrementar `registry_version` y añadir una fixture. |
| Debe suspenderse la promoción desde corpus | Eliminar `corpus_index_pages` de ese dataset, incrementar `registry_version` y ejecutar el pipeline. |
| Un candidato pasa descubrimiento pero falla parseo o reconciliación | No publicar; conservar los diagnósticos y seguir el ciclo de alertas del pipeline. |

## Pruebas requeridas para cambios futuros

Todo cambio a esta política debe conservar pruebas offline que cubran: promoción de un candidato fechado y estrictamente más nuevo; rechazo de una URL fuera del índice registrado; rechazo de candidatos no fechados; empate de la fecha más reciente; procedencia escrita en `source_capture.json`; y el comportamiento sin cambios cuando el documento ya está enlazado por la página canónica.

## Referencias

[1]: https://www.snice.gob.mx/~oracle/SNICE_DOCS/ "Índice público SNICE_DOCS"
[2]: https://github.com/jccontrerasg08-cpu/arancel-mx/issues/110 "Reconciliación de fracciones LIGIE y lag NICO"
