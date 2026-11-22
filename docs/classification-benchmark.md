# Benchmark de clasificación asistida

## Propósito

Este contrato prepara evaluaciones reproducibles para sistemas que sugieren fracciones o NICO como **hipótesis de clasificación**. No entrena un modelo, no confirma una clasificación, no determina origen, no valida RRNA y no genera ni transmite pedimentos.

Cada caso se fija a una release inmutable de datos, por ejemplo `data-2026.08.17`, y debe contar con una revisión humana identificable y evidencia HTTPS de fuente oficial. No se distribuye un conjunto de etiquetas de entrenamiento dentro del repositorio hasta que sus casos tengan revisión documental y sus condiciones de uso estén aprobadas.

## Caso de referencia

| Campo | Requisito |
|---|---|
| `case_id` | Identificador único y estable. |
| `release_tag` | Tag inmutable con formato `data-YYYY.MM.DD`. |
| `query` | Descripción técnica de la mercancía, sin datos personales. |
| `gold_tariff_code` | Fracción de 8 dígitos o NICO de 10 dígitos, revisada. |
| `evidence_urls` | Al menos una fuente HTTPS oficial que sostenga la revisión. |
| `reviewed_by` y `reviewed_at` | Trazabilidad de revisión humana. |

Los casos deben separarse por familia de producto, fecha y release para evitar que descripciones casi idénticas filtren etiquetas entre entrenamiento, validación y prueba.

## Resultado de un sistema

Una respuesta no abstinente debe devolver candidatos únicos y ordenados, junto con evidencia HTTPS. La abstención es un resultado válido y preferible cuando la descripción o sus soportes no descartan alternativas plausibles.

El evaluador `arancel_mx.benchmark.classification` reporta las siguientes métricas:

| Métrica | Definición | Uso responsable |
|---|---|---|
| `coverage` | Proporción de casos respondidos sin abstención. | Mide alcance, no corrección jurídica. |
| `top_k_recall` | Proporción total cuyo código revisado aparece entre los primeros *k* candidatos. | Penaliza abstenciones al considerar el universo completo. |
| `selective_top_k_recall` | Proporción correcta dentro de los casos respondidos. | Debe interpretarse siempre junto con cobertura. |
| `abstentions` | Casos que el sistema escaló sin candidato. | Señal de prudencia, no un error automático. |

El resultado fija `decision_scope` como `classification_hypothesis`. Cualquier interfaz que use estas métricas debe mostrar ese alcance y enlazar la evidencia; no debe presentar una recomendación como resolución jurídica ni como confirmación de cumplimiento.

## Admisión de datos

Antes de agregar un caso al corpus, se debe verificar la existencia de la release indicada, retirar datos personales y comerciales no necesarios, registrar la fuente primaria y obtener revisión humana. Un cambio de release requiere repetir la evaluación o justificar la comparabilidad mediante su manifiesto y `source_history`.

## Próximo experimento controlado

El primer experimento puede ser un recuperador léxico o semántico que sólo consulte descripciones de la release fijada. Debe evaluar top-5, cobertura y abstención contra un conjunto de prueba retenido. Un modelo generativo, si se utiliza en una etapa posterior, sólo podrá ordenar candidatos ya recuperados y deberá citar la evidencia recuperada; no debe inventar fracciones ni sustituir la revisión documental.

## Autoverificación de la búsqueda actual

Antes de evaluar cualquier búsqueda asistida (RFC de búsqueda híbrida, #312) se necesita una línea base de la búsqueda léxica que ya existe. `arancel-mx data search-selfcheck` la mide sin etiquetas humanas, usando la propia release como respuesta conocida:

```bash
arancel-mx data search-selfcheck --dataset data-2026.11.20 --sample 50
```

Toma una muestra determinista y uniformemente espaciada de fracciones vigentes y, para cada una, consulta su código (`exact_code`), su código con puntos (`dotted_code`) y su descripción publicada (`own_description`). Una descripción compartida por varias fracciones (por ejemplo «Los demás.») no puede identificar una sola y se cuenta aparte como `non_distinctive_skipped`, no como fallo. Encontrar el mismo artículo en otro nivel de su propia línea con la misma descripción (su NICO o subpartida) cuenta como acierto. El reporte incluye las primeras fallas con su posición y la latencia por búsqueda en la máquina donde se corrió.

Esto mide si la búsqueda encuentra registros que ya existen, no si clasifica bien una mercancía: sus tasas no son una probabilidad de acierto para un producto.
