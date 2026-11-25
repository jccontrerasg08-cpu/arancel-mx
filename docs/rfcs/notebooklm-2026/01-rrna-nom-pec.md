# RFC: RRNA, NOM, PEC y autoridades

> **Estado:** propuesta de implementación — documentación únicamente. **Prioridad:** P0. **Corte:** 2026-11-21.
> **Trazabilidad:** [inventario NotebookLM de 42 entradas](../../research/notebooklm-source-inventory-2026-11-21.json) y [auditoría](../../research/notebooklm-source-audit-2026-11-21.md). La conversación de Gemini se revisó; no se ha inspeccionado el interior de los seis elementos de Studio ni transcrito todos los videos.

## Estado existente y por qué no duplicarlo

Ya existen regulations/{hs2}.json, datos NOM del Anexo 2.4.1, estados available/unavailable/carried_forward y canario diario (ADR 0004). No repetir parsers ni afirmar automáticamente cumplimiento.

## Resultado esperado y experiencia de usuario

Ficha de regulaciones para revisar por fracción8/NICO10 con fundamento, acotación literal, autoridad, estado de fuente, fecha y enlaces; añadir por etapas referencias RRNA sectoriales, evaluación de conformidad, PEC/OEC, equivalencias y derechos documentados.

1. Ver NOM y acotación precisa al consultar una fracción, conservando el origen documental y el estado del Anexo 2.4.1.
2. Navegar a SNICE, DOF, VUCEM y autoridades competentes (Salud/COFEPRIS, SENASICA, SEMARNAT), distinguiendo enlaces de requisitos confirmados.
3. Saber si las NOM vienen de la release actual o arrastre anterior, sin resultados 'libre de RRNA'.
4. Consultar certificados, inspección, muestreo, laboratorios/OEC, equivalencias/reconocimientos y derechos únicamente si hay instrumento específico.

## Arquitectura propuesta

- Reusar lector NOM ya certificado y el contrato regulations/{hs2}.json, sin alterar el core LIGIE/NICO.
- Catálogo lateral de medidas: instrument_id, measure_id, authority, code, effective_dates, scope_text, source_url, source_sha256, fetched_at, confidence_status.
- Adaptadores de fuentes sectoriales aislados, con allowlist, fixture de cambios y revisión humana si ambigüedad. No presuponer que NOM equivale a cualquier otra RRNA.
- UI con tres estados distintos: aparece en anexo, no aparece en anexo disponible, anexo no disponible/arrastrado; cada fila muestra alcance, numeral, acotación y vigencia.
- PEC, OEC, tratados de reconocimiento y derechos por trámites son catálogos opcionales distintos; no se infiere modalidad de cumplimiento a partir del código.

## Contrato lógico de ejemplo (NO implementado)

~~~json
{
  "code": "8517xxxx",
  "dataset_version": "data-YYYY.MM.DD",
  "annex": {
    "status": "available|unavailable|carried_forward|not_included",
    "source_release": null
  },
  "references": [
    {
      "kind": "nom_reference",
      "norm_id": "NOM-...",
      "scope_text": "acotación original",
      "numeral": "1",
      "authority_id": null,
      "instrument_url": null,
      "source_sha256": null,
      "determines_compliance": false
    }
  ]
}
~~~

**Metadatos obligatorios:** identificador de fuente/instrumento, URL oficial, fecha de consulta, versión/corte, fecha de publicación y vigencia cuando se confirme, captura SHA-256 cuando existan bytes, datos declarados vs oficiales y estados `unknown`/`unavailable` distintos de «no aplica».

## Reglas de seguridad legal y de datos

- La fracción no basta para determinar cumplimiento, excepciones, país, régimen, producto o documentos.
- Nunca asignar muestreo, inspección, derecho, aprobación o acuerdo de equivalencia sin fuente primaria concreta.
- Conservar unknown, not-in-source, unavailable y carried-forward; no reemplazar valores por 'no aplica'.
- No incorporar RRNA sectoriales al source_registry canónico sin ADR y pruebas de captura/fuentes.

## Pruebas y criterios de aceptación

- [ ] Fracciones con NOM y acotaciones, sin fila, anexo no disponible, arrastre y dos fechas de reforma.
- [ ] Test de conformidad JSON aditiva, sin cambiar records ni LIGIE.
- [ ] E2E desktop/móvil: fuente y estado visibles, sin mensaje de cumplimiento certificado.
- [ ] El canario NOM conserva política fail-visible y no detiene LIGIE por falla auxiliar.
- [ ] No alterar releases LIGIE/NICO, source_registry.json ni reactivar el endpoint /v1 retirado sin ADR formal.
- [ ] Definir estrategia de fallos, rollback, compatibilidad, latencia, accesibilidad y textos en español/inglés.

## Fases de implementación

1. UI sobre datos NOM existentes
2. Registro lateral RRNA sectorial verificado
3. PEC/OEC y equivalencia sólo con publicación y vigencia

## Decisiones abiertas y bloqueos

Fuente por autoridad, ámbito del procedimiento, términos vigentes, excepciones y viabilidad de captura; aprobación legal antes de habilitar señales adicionales.

## Mapa de fuentes del notebook y oficiales

- Notebook entradas 9, 11–36, 37–39; Ley Aduanera, LIC, Salud, LFSA, LFSV, LGEEPA, LFD, acuerdos SNICE.
- https://www.snice.gob.mx/cs/avi/snice/seguridad.normatividad.html
- https://sidof.segob.gob.mx/notas/docFuente/5799697
- https://sidof.segob.gob.mx/notas/5797937

## Alcance de este PR

**Sólo RFC.** No contiene implementación, modificación de esquemas canónicos, publicación de nuevas tasas, automatización fiscal, decisiones vinculantes ni despliegue. Cada fase requiere PR de código, pruebas y verificación legal cuando corresponda.
