# RFC: Ficha técnica PDF/Markdown y UX

> Propuesta únicamente de diseño. Prioridad P1; base documental: Gemini Notebook 2026-11-21 y [auditoría de fuentes](../../research/notebooklm-source-audit-2026-11-21.md).

## Existente / no duplicar

El explorador ya publica campos LIGIE/NICO, notas, NOM acotadas y procedencia. Gemini proponía PDF con impuestos y RRNA que hoy no están siempre determinados.

## Objetivo y alcance

Exportar una ficha de consulta versionada, imprimible y accesible con datos verificables, enlaces de fuente y secciones opcionales de referencia separadas de una determinación legal.

## Arquitectura técnica, UX y contratos

- Modelo de ficha principal: release, manifest SHA, HS2→NICO, descripción, UMED, IGI/IGE textual, nota, vigencia y fuentes.
- Vistas secundarias NOM, tratados, DTA/IVA/IEPS e interpretación legal sólo como referencias, escenarios o not_available, nunca 'aplicable' automático.
- HTML semántico desde datos ya consumidos y CSS print A4/Carta; export Markdown escapado; preferir browser print PDF a servicio externo.
- Mostrar generated_at, official_source_checked_at, dataset_version y effective_as_of como fechas distintas.
- Si el usuario aporta valor o país, etiquetar user_declared y mantener render local; sin enviar datos de negocio a terceros.
- Modo sin conexión con fuente congelada, disclaimer visible, citas breves y enlaces oficiales; no copiar textos legales completos.
- Accesibilidad para lectores de pantalla, contraste, encabezados, links y paginación sin truncamientos; límite de memoria y tamaño.

## Esquema de ejemplo (no endpoint ni release implementados)

~~~json
{
  "report_schema": "1",
  "generated_at": "ISO-8601",
  "release": "data-YYYY.MM.DD",
  "record": {
    "code": "XXXXXXXX",
    "igi_text": "literal",
    "sha256": "hash"
  },
  "secondary": [
    {
      "kind": "regulatory|tax|treaty",
      "status": "reference_only"
    }
  ],
  "formats": [
    "markdown",
    "print-pdf"
  ],
  "legal_determination": false
}
~~~

**Metadatos comunes:** source_url, fecha oficial de publicación, fecha efectiva comprobada si existe, retrieved_at, dataset_version/tag, instrumento, hash SHA-256 real, estado de fuente y distinción entre datos oficiales/declarados/derivados. Nunca inventar ausencias.

## Pruebas/criterios de aceptación

- [ ] Ficha generada desde mismo hash conserva código/texto y enlaces.
- [ ] Sin fuente o dato no se substituye por 0, libre ni no aplica.
- [ ] Escape HTML/Markdown previene XSS y ruptura de formato.
- [ ] Print tests para A4/Carta, móvil y multipágina.
- [ ] No duplicar y no inferir datos regulatorios o tasas preferenciales.
- [ ] Mantener /data/v1 y las seis piezas canónicas, salvo ADR aprobado por separado.
- [ ] CI reproducible, fallback, límites, rollback, i18n español/inglés y documentación de accesibilidad y desempeño.

## Entregas técnicas sugeridas

1. ADR de cobertura, formatos y compatibilidad con el repositorio actual.
2. PoC offline con fixtures oficiales y umbrales medibles.
3. Integración opt-in tras aprobación del propietario y revisión CI.
4. Pruebas multiplataforma y documentación de uso/errores.

## Pendiente de investigación

Comparar print navegador vs renderer externo y elegir menor coste/privacidad; datos fiscales esperan RFC correspondiente.

## Fuentes del NotebookLM y fuentes primarias

- Notebook entradas 1–3,9–10,11–38: ficha técnica con fundamentos, NICO, NOMs, DTA, IVA, IEPS y tasa preferencial.
- https://www.snice.gob.mx/cs/avi/snice/ligie.info22.html
- https://www.dof.gob.mx/

**Inventario:** [42 entradas identificadas](../../research/notebooklm-source-inventory-2026-11-21.json). Respuestas de Gemini no son hechos verificados y materiales Studio no fueron inspeccionados.

## Límite de este PR

El PR contiene sólo especificación, no implementa funciones ni agrega assets a releases. La publicación en GitHub sólo activa revisiones/CI y potencial preview, sin despliegue funcional.
