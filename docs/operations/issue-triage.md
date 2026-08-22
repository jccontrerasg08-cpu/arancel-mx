# Triage mínimo de issues

Esta rutina adapta el enfoque de clasificación de reportes del ecosistema Python a un repositorio pequeño. Su objetivo es dejar un siguiente paso visible, no resolver automáticamente ni sustituir la revisión técnica.

## Cadencia y responsable

Un mantenedor revisa los issues nuevos al menos una vez por semana. Si no hay capacidad, se conserva la etiqueta actual y se deja una respuesta honesta; no se prometen tiempos de resolución.

## Checklist por issue

| Paso | Acción mínima | Resultado visible |
|---|---|---|
| Duplicado | Busca issues y pull requests con el mismo síntoma, fuente o propuesta. | Enlaza el duplicado o conserva el reporte único. |
| Reproducción | Para bugs, confirma versión, comando o fixture sanitizado y resultado esperado. | Marca qué información falta o adjunta el caso reproducible. |
| Alcance | Determina si afecta fuente, parser, modelo, pipeline, release, CLI, documentación o seguridad. | Elige una etiqueta de área cuando exista y evita ampliar el issue. |
| Etiqueta | Aplica `bug`, `enhancement`, `documentation`, `question` u otra etiqueta existente; usa `needs-triage` si falta información material. | La cola queda filtrable y sin inferir una prioridad jurídica. |
| Siguiente acción | Solicita un dato concreto, enlaza un issue/PR, acepta el alcance o explica por qué no se trabajará. | Cada reporte tiene un próximo paso público. |

## Límites

No cierres reportes ambiguos, conflictos de alcance o posibles vulnerabilidades sólo por falta de información. Deriva posibles vulnerabilidades a [SECURITY.md](../../SECURITY.md), conserva la confidencialidad y solicita revisión de un mantenedor antes de cerrar un caso controvertido.

## Señales de estado

La etiqueta `needs-triage` sólo significa que falta clasificación o información material. Debe retirarse al completar la checklist. No activa automatizaciones, cierres ni publicaciones de datos.
