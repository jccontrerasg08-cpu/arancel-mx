# Triage mínimo de issues

Esta rutina describe cómo los mantenedores revisan los issues nuevos de `arancel-mx`. Adapta el enfoque de clasificación de reportes del ecosistema Python a un repositorio pequeño: su objetivo es dejar un siguiente paso visible, no resolver automáticamente ni sustituir la revisión técnica.

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

La etiqueta `needs-triage` sólo significa que falta clasificación o información material. Debe retirarse **solo cuando** la clasificación esté completa y se haya obtenido la información material solicitada; dejar un comentario pidiendo reproducción o alcance no basta para retirarla. No activa automatizaciones, cierres ni publicaciones de datos.

Dos etiquetas las aplica la automatización del **Official data pipeline** y siguen su propio ciclo:

- `dof-candidate`: la vigilancia diaria del DOF abre un issue por cada nota arancelaria nueva. El triage confirma si el instrumento cambia tasas, fracciones, NICO o medidas que sigue el proyecto, completa la lista de revisión del issue y lo cierra cuando la release certificada lo refleje o quede documentado por qué no.
- Las alertas de falla del pipeline llevan un marcador oculto de automatización y se cierran solas en la siguiente ejecución saludable. No las cierres a mano: si la causa persiste, deja el diagnóstico en el issue.

## Relacionado

- [CONTRIBUTING.md](../../CONTRIBUTING.md)
- [SECURITY.md](../../SECURITY.md)
- [Proceso de release](../release-process.md#11-fallos-github-issue-y-recovery)
- [Historial certificado de fuentes](../source-history.md)
