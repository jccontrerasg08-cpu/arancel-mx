# RFC: Academia: cinco unidades de Módulo 8 y recursos Studio

> Prioridad P2 | Estado: solo especificación | Corte: 2026-11-21
> Basado en el contenido visible de la conversación Gemini y el [inventario de 42 entradas](../../research/notebooklm-source-inventory-2026-11-21.json) junto a [auditoría](../../research/notebooklm-source-audit-2026-11-21.md). La investigación original tiene límites de acceso.

## Punto de partida / capacidad existente

Ya existen /learn, /wiki, /glossary y mapa de fuentes; NotebookLM presenta cinco unidades bajo título propio 'Integración de Tecnología, Datos Abiertos, Analítica Arancelaria y Cumplimiento Normativo'. Esto NO debe atribuirse a la numeración del programa oficial Ruta Logística MX.

## Producto esperado

Convertir el temario del notebook en contenido didáctico de arancel-mx con ejercicios reproducibles, autoevaluaciones, tarjetas, mapa de dependencias y material audiovisual, verificando fuentes y licencias.

## Diseño técnico, UX, fuentes y límites

- Unidad 1: arquitectura datos abiertos LIGIE/NICO, HS2→HS10, DuckDB, Python/CLI, API estática, releases y SHA256.
- Unidad 2: RRNA, NOM, LIC/PEC, OEC, equivalencias, inspección, muestreo y autoridades sectoriales; ejercicios de fuente y no de cumplimiento.
- Unidad 3: valor en aduana, IGI, DTA, IVA/IEPS, CFF INPC/recargos, precios estimados, COVE, regímenes; sólo escenarios explicativos.
- Unidad 4: INEGI BCMM/BIE, TIGIE–SCIAN y consumo aparente condicionado a producción nacional comparable; TLC y origen documental.
- Unidad 5: notas nacionales/sección/capítulo, criterios SAT y consultas; distinguir jurisprudencia, casos y resoluciones.
- Diseñar lecciones con objetivos observables, prerequisitos, lecturas oficiales, ejercicios sobre fixtures, soluciones, rúbrica, nivel, fecha/version, licencia y responsable editorial.
- Reutilizar /learn/wiki/glossary; no copiar videos completos, transcripciones ni 6 productos Studio sin derechos y acceso. Todo material debe tener identidad URL y fecha de revisión.
- Vincular seis Studio: Estrategia Transnacional Global (diapositivas), Balanza Comercial de México 2024 (infografía), Comercio Exterior Cuestionario, Derecho Aduanero Tarjetas, Dependencias Gubernamentales Mapa Mental, Navegando el Comercio Internacional y la Regulación Jurídica en México (reporte); contenido interno PENDIENTE DE INSPECCIÓN.
- Vincular 11 videos mencionados por Gemini en Ruta Logística: seis módulos (Contexto y Fundamentos; Actores; Procesos Operativos; Fiscalización y Cumplimiento; Digitalización y Facilitación; Aplicación Práctica), cuatro Viernes (Operación Reactiva; Control de Inventarios; Mensajería y Paquetería; Pasaporte del Talento) y cápsula Logística en México. **Los títulos/duraciones son aseveraciones de Gemini, no videos individualmente verificadas.**
- Identificar por separado el programa oficial 2026 de diez módulos (22 sep a 24 nov) documentado por Secretaría de Economía; nombre propio de esta unidad didáctica 'Módulo 8 de arancel-mx' y fecha editorial; no confundirlo con sesión oficial #8.

## Contrato lógico preliminar (no implementado)

~~~json
{
  "curriculum_id": "arancel-mx-module-8",
  "status": "editorial_proposal",
  "units": [
    1,
    2,
    3,
    4,
    5
  ],
  "lesson": {
    "id": "u1-l1",
    "objective": "observable",
    "source_refs": [
      "notebook-entry-10"
    ],
    "official_urls": [],
    "license_status": "review_required",
    "fixture_tag": "data-YYYY.MM.DD",
    "exercise_type": "source-verification|quiz|simulation",
    "reviewed_at": null
  },
  "studio_assets": {
    "visible": 6,
    "internal_content_reviewed": false
  },
  "video_claims": {
    "listed_by_gemini": 11,
    "per_video_verified": false
  }
}
~~~

Metadatos requeridos: identificador estable, fuente original/URL, fecha de consulta y publicación, versión, SHA256 cuando existan bytes, derechos de reutilización, estado verificado/refencia/declarado, fecha efectiva cuando corresponda. No reemplazar unknown con valores inferidos.

## Criterios de aceptación comprobables

- [ ] Cada lección muestra fuente, fecha, edición y objetivo con rubric propia.
- [ ] Problemas reproducibles con datos de release fijada, sin infringir copyright.
- [ ] 100% de preguntas explican respuesta y dan fuente; revisión humana de derecho.
- [ ] Distinguir claramente programa educativo propio vs calendario oficial de Ruta Logística.
- [ ] Tests UI accesible, lectura offline y enlaces no rotos; sin inferir que 6 assets Studio fueron leídos.
- [ ] Especificar fallback, seguridad, accesibilidad, idiomas, privacidad, rollback, presupuesto de recursos y compatibilidad antes de PR de código.
- [ ] No reactivar /v1 ni modificar releases LIGIE/NICO sin ADR.

## Plan de implementación

1. Índice editorial y matriz de fuentes/verificación de cada unidad
2. Primera unidad con ejercicios citables y verificados
3. Cuestionario y tarjetas con test editorial
4. Integración de multimedia tras revisar licencia y accesibilidad
5. Extensión al resto de unidades

## Preguntas abiertas y verificaciones pendientes

Conseguir enlaces directos y revisar íntegramente cada material Studio/video antes de afirmar contenido; registrar licencias, fechas y temario oficial.

## Trazabilidad a NotebookLM y fuentes oficiales

- Notebook: las 42 entradas del inventario, incluyendo 1 'Datos Arancelarios MX', 41 'International Business', 42 canal Ruta Logística, 4–8 INEGI y 11–36 leyes.
- https://www.gob.mx/se/prensa/inicia-la-segunda-fase-de-ruta-logistica-mx-2026-mexico-la-nueva-ruta-del-mundo?state=published
- https://www.inegi.org.mx/programas/comext/default.html
- https://www.anam.gob.mx/manual-de-operacion-aduanera-moa/

## Fuera de alcance del PR

El PR crea esta especificación; no activa IA, transmisiones aduaneras, nuevos contenidos multimedia o cambios en producción. Implementación posterior mediante PRs separados con CI y revisión del propietario.
