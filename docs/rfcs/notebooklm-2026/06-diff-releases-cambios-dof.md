# RFC: Diff entre releases, trazabilidad y alertas DOF

> Estado: propuesta exclusivamente documental | Prioridad: P1 | Fecha: 2026-11-21
> Basado en [inventario NotebookLM (42 entradas)](../../research/notebooklm-source-inventory-2026-11-21.json) y [auditoría](../../research/notebooklm-source-audit-2026-11-21.md); las respuestas de Gemini no sustituyen lectura de fuentes primarias.

## Punto de partida: evitar duplicación

Ya existe /changes, /release-analytics, manifests con source_history y watcher DOF diario que abre issues; los assets data-YYYY.MM.DD son inmutables. Evitar construir un segundo bot redundante.

## Problema, alcance y resultado

Comparador determinista por código, tasa, descripción, vigencia y NICO entre dos releases verificadas; distinguir cambios de datos publicados de eventos legislativos e incidencias de capturas, con navegación de evidencia.

## Historias de usuario

1. Seleccionar dos releases certificadas y filtrar altas, bajas, modificaciones de tasas, textos, jerarquía, notas y NICO.
2. Ver fuente, fecha de publicación, entrada en vigor confirmada y hash antes/después; no confundir un cambio de snapshot con un nuevo decreto.
3. Exportar diff verificable CSV/JSON y permalink con parejas de tags.
4. Seguir candidatos de DOF ya detectados con estatus pendiente/revisado/rechazado, sin autopublicar instrumentos.

## Arquitectura técnica propuesta

- Reusar source_history en manifest y scripts/watch_dof.py para cambios de fuentes; construir una vista distinta de diff por filas a partir de assets exactos de ambas releases.
- Comparación SQL DuckDB fijando release A y B con SHA256SUMS verificados, sin solicitudes contra latest mutante.
- Tipo de evento row_added,row_removed,description_changed,igi_changed,ige_changed,nico_changed,notes_changed,provenance_changed; aceptar múltiples por código.
- Normalizar texto solo para comparación secundaria: conservar valores literales y mostrar original; no colapsar cambios de acentos que sean jurídicamente relevantes.
- Algoritmo de paginación o precomputación incremental con manifest, hash y test de estabilidad; sin desplegar servicio dinámico /v1.
- El watcher existente sigue generando issue candidato y requiere gate humano para promoción de fuentes; no abrir PR de datos automático antes de reconciliación.

## Contrato JSON de referencia, no implementado

~~~json
{
  "from": "data-YYYY.MM.DD",
  "to": "data-YYYY.MM.DD",
  "verified_shas": {
    "from": "sha256...",
    "to": "sha256..."
  },
  "changes": [
    {
      "code": "XXXXXXXX",
      "event": "igi_changed",
      "old_text": "X",
      "new_text": "Y",
      "source_url": null,
      "legal_effective_date": null
    }
  ],
  "unclassified_changes": [],
  "comparison_status": "verified_snapshots_only"
}
~~~

Cada dato nuevo debe enlazar fuente, autoridad, documento/version, retrieved_at, published_at/effective_date si se conoce, SHA256 cuando se conserva bytes, estado y fecha de revisión. Sin datos se representa unknown y no cero.

## Invariantes y límites

- Un cambio de fecha de captura sin cambio de tarifa no es reforma legal.
- Distinguir add/remove de código y reutilización de código tras reforma.
- No mostrar estados 'vigente' solo porque latest los incluye; enlazar transitorios y fecha de operación.
- No permitir re-publicar releases inmutables ni editar manifest en sitio.

## Casos de prueba y definición de terminado

- [ ] A=B: diff vacío; A/B invertidas: eventos simétricos; conjuntos en orden determinista.
- [ ] Muestras con cambios de tasa temporal, textos, nuevos/retirados NICOs y falta de release.
- [ ] Verificación real de SHA; si falla no mostrar diff como verificado.
- [ ] Pruebas de paginación, export y enlaces estables; fixtures offline de fuente.
- [ ] Monitoreo DOF no dispara nuevos issues duplicados ni afecta los pipelines de publicación.
- [ ] Compatibilidad de API estática /data/v1, sin alterar la release canónica ni revivir /v1 dinámico.
- [ ] Documentar costes, medidas de rendimiento, UX de accesibilidad, seguridad, errores, rollbacks y traducción antes de pasar a código.

## Entrega incremental

1. Especificación row-level diff y fixtures históricos
2. Comparador accesible y export con hashes
3. Feed Atom/JSON de cambios sobre releases verificadas y enlace a DOF
4. Mejoras del triage del watcher existente sin nueva acción automática de publicación

## Investigaciones pendientes

Definir snapshot histórico comparables, política de versión y tamaño de índices; validar semántica de fechas jurídicas.

## Fuentes del NotebookLM y primarias

- Notebook entradas 9 DOF, 10 GitHub, 2 web del proyecto, 37–38 SNICE y leyes que modifican TIGIE.
- https://www.diputados.gob.mx/LeyesBiblio/ref/ligie_2022.htm
- https://www.snice.gob.mx/cs/avi/snice/ligie.info22.html
- https://www.dof.gob.mx/

## No forma parte de este PR

Esta rama contiene sólo RFC. No activa nuevas funciones, no modifica la interpretación legal oficial, no crea datos sin evidencia y no habilita despliegues. La implementación requerirá PR(s) de código con fixtures, métricas y revisión técnica/jurídica.
