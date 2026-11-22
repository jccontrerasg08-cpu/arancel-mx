# RFC: Búsqueda semántica asistida y clasificación responsable

> Prioridad P2 | Estado: solo especificación | Corte: 2026-11-21
> Basado en el contenido visible de la conversación Gemini y el [inventario de 42 entradas](../../research/notebooklm-source-inventory-2026-11-21.json) junto a [auditoría](../../research/notebooklm-source-audit-2026-11-21.md). La investigación original tiene límites de acceso.

## Punto de partida / capacidad existente

Existe búsqueda lexical exacta/prefijos por código y descripción, Dataset API y /data/v1/search-index.json. No existe clasificador oficial, y la misión del proyecto declara que no asigna fracciones legalmente.

## Producto esperado

Añadir búsqueda híbrida opcional para preguntas coloquiales como pantalla OLED para automóvil, mostrando candidatos de consulta y fragmentos de fuentes; sin predecir la fracción correcta ni porcentajes de certeza no calibrados.

## Diseño técnico, UX, fuentes y límites

- Definir baseline con ranking lexical deterministic y retrieval de capítulos; cuantificar mejoras antes de IA.
- Dataset de evaluación publicado con preguntas de no especialistas, sin datos privados ni etiquetas comerciales sensibles; respuestas de referencia revisadas por expertos.
- Opt-in de modelo local o proveedor externo únicamente tras privacy-by-design/consentimiento; no enviar fotos, facturas o composición a terceros por defecto.
- Resultados devuelven códigos candidatos, evidencia textual, estado de dataset y caveat; no columna authoritative_code ni clasificación oficial.
- Si se usa score de similitud: mostrar etiqueta de similitud no porcentaje de probabilidad; calibración y límites por idioma/capítulo antes de exponer confidence.
- Búsqueda ambigua debe devolver consulta refinada o abstención; incluir clasificación errónea como riesgo jurídico y red-teaming de prompts.
- Nunca responder sobre requisitos, certificados, país de origen o arancel aplicable automáticamente sólo desde una coincidencia semántica.

## Contrato lógico preliminar (no implementado)

~~~json
{
  "query": "pantalla OLED para automóvil",
  "dataset": "data-YYYY.MM.DD",
  "method": "lexical|hybrid",
  "candidates": [
    {
      "code": "XXXXXXXX",
      "match_explanation": "texto de release",
      "similarity_score": null,
      "official_classification": false,
      "source_release": "data-YYYY.MM.DD"
    }
  ],
  "abstain": true,
  "notice": "Resultados de consulta, no clasificación aduanera."
}
~~~

Metadatos requeridos: identificador estable, fuente original/URL, fecha de consulta y publicación, versión, SHA256 cuando existan bytes, derechos de reutilización, estado verificado/refencia/declarado, fecha efectiva cuando corresponda. No reemplazar unknown con valores inferidos.

## Criterios de aceptación comprobables

- [ ] Top-k, recall/precision y tasa de abstención en evaluación congelada; métricas por ambigüedad.
- [ ] Ejemplos adversariales: descripciones comerciales vagas, materia mixta, unidades y NICO inexistente.
- [ ] No filtrar contenido sensible a proveedor ni ejecutar instrucciones incluidas en documentos indexados.
- [ ] No hallucinated codes; todo código devuelto existe en release fijada.
- [ ] Sin opt-in, búsqueda exacta y privacidad existentes no cambian.
- [ ] Especificar fallback, seguridad, accesibilidad, idiomas, privacidad, rollback, presupuesto de recursos y compatibilidad antes de PR de código.
- [ ] No reactivar /v1 ni modificar releases LIGIE/NICO sin ADR.

## Plan de implementación

1. Benchmark lexical actual + corpus de evaluación revisado
2. Prototipo híbrido sin proveedor externo
3. Revisión legal/privacidad y métricas de calibración
4. UI de candidatos con evidencias y abstención

## Preguntas abiertas y verificaciones pendientes

Determinar quién mantiene etiquetas de referencia y quién revisa falsos positivos; no implementar clasificación automática con efecto jurídico.

## Trazabilidad a NotebookLM y fuentes oficiales

- Notebook: entrada 2 arancel-mx, 10 GitHub, 11–36 fundamentos legales, propuesta explícita de búsqueda IA híbrida.
- https://www.snice.gob.mx/cs/avi/snice/ligie.info22.html
- https://www.diputados.gob.mx/LeyesBiblio/ref/ladua.htm

## Fuera de alcance del PR

El PR crea esta especificación; no activa IA, transmisiones aduaneras, nuevos contenidos multimedia o cambios en producción. Implementación posterior mediante PRs separados con CI y revisión del propietario.
