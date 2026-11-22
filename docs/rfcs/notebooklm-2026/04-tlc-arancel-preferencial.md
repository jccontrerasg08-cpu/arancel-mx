# RFC: Matriz de TLC, reglas de origen y tasas preferenciales

> Estado: propuesta exclusivamente documental | Prioridad: P1 | Fecha: 2026-11-21
> Basado en [inventario NotebookLM (42 entradas)](../../research/notebooklm-source-inventory-2026-11-21.json) y [auditoría](../../research/notebooklm-source-audit-2026-11-21.md); las respuestas de Gemini no sustituyen lectura de fuentes primarias.

## Punto de partida: evitar duplicación

docs/research/treaty-preferences-spike.md ya describe un side-asset sin implementación; el IGI de la release es general. /trade trabaja con supuestos declarados, sin certificar origen.

## Problema, alcance y resultado

Matriz de investigación por tratado/fracción/fecha con tasa preferencial textual, decreto, regla de origen referenciada, fecha de vigencia, evidencia y estado de disponibilidad; comparación con IGI general sin afirmar elegibilidad para una operación.

## Historias de usuario

1. Comparar arancel general y tratamientos publicados de T-MEC, TLCUE, AELC, Alianza del Pacífico, Japón, Chile, Colombia, Perú, Panamá, Uruguay, Israel, Centroamérica u otros, sólo si fuente vigente sustenta la relación.
2. Abrir tasa oficial, regla de origen, resolución aduanera y evidencia de publicación con versión.
3. Distinguir acuerdo vigente, acuerdo histórico, desgravación parcial, cuota, exclusión, dependencia de origen y falta de fuente por código.
4. Exportar comparación indicando que prueba de origen, requisitos y operación no han sido verificados.

## Arquitectura técnica propuesta

- Inventario de instrumentos por tratado con IDs estables y jerarquía de normas (decreto de tasas, protocolo, reglas específicas y resolución aduanera).
- Assets laterales separados del core IGI; publicación condicionada a captura SHA, cotejo de tasas y vigencias por código, tratamiento de HS6 contra fraccion8.
- No reemplazar igi_text/igi_kind/igi_value; una vista de 'comparar' selecciona tasa general y preferencias posibles documentadas, no tasa aplicable.
- No asignar 0% por defecto ni derivar de mero convenio diplomático; representar calendarios, cupos, notas y condiciones.
- UI: tabla por acuerdo, país, instrumento, publicación, efectivo desde/hasta, preferencia textual y origen no comprobado.
- Tratado anterior (TLCAN) se etiqueta histórico cuando corresponda; no usar su regla automáticamente para T-MEC.

## Contrato JSON de referencia, no implementado

~~~json
{
  "code": "XXXXXXXX",
  "dataset_version": "data-YYYY.MM.DD",
  "general_igi": {
    "text": "de release verificada"
  },
  "candidate_preferences": [
    {
      "treaty_id": "T-MEC",
      "tariff_text": "instrument-dependent",
      "published_at": null,
      "effective_from": null,
      "effective_to": null,
      "origin_rule_ref": null,
      "source_url": "https://...",
      "source_sha256": null,
      "product_scope": "text literal",
      "status": "reference_only",
      "shipment_eligible": null
    }
  ]
}
~~~

Cada dato nuevo debe enlazar fuente, autoridad, documento/version, retrieved_at, published_at/effective_date si se conoce, SHA256 cuando se conserva bytes, estado y fecha de revisión. Sin datos se representa unknown y no cero.

## Invariantes y límites

- Regla de origen, prueba documental, elegibilidad y preferencias son hechos distintos; jamás inferir del país de procedencia.
- Datos parciales no se rellenan con 0%; preferir unknown o not_published.
- Comparar códigos solo con concordancias oficiales de fecha y desagregación HS/fracción.
- PROSEC, IMMEX, cupos y medidas de remedio comercial no son TLC y deben quedar separados.

## Casos de prueba y definición de terminado

- [ ] Fixtures por tratado, fecha límite, una fracción sin preferencia, cuota y tasa mixta.
- [ ] Paridad con decreto SNICE/DOF para muestra de códigos auditada por dos revisores.
- [ ] Releases con preferencia lateral ausente siguen siendo válidas; core IGI no cambia.
- [ ] UX muestra explícitamente falta de comprobación del origen y documentos.
- [ ] Compatibilidad de API estática /data/v1, sin alterar la release canónica ni revivir /v1 dinámico.
- [ ] Documentar costes, medidas de rendimiento, UX de accesibilidad, seguridad, errores, rollbacks y traducción antes de pasar a código.

## Entrega incremental

1. Inventario de tratados y anexos con régimen de actualización
2. Piloto de un tratado con side asset y fixtures
3. Matriz multi-tratado con comparador documental y exportación

## Investigaciones pendientes

Inventario de decretos vigentes por tratado y corte de fracciones; determinar qué entidad y evidencia permiten afirmar un valor por fracción sin emitir decisión de origen.

## Fuentes del NotebookLM y primarias

- Notebook: 37 (tasas), 38 (resoluciones TLC), 9 (DOF), 11–36 (LAdua/LCE), 10 GitHub.
- https://www.snice.gob.mx/cs/avi/snice/biblioteca.juridica.tasas.html
- https://www.snice.gob.mx/cs/avi/snice/biblioteca.juridica.tlc.html
- https://www.gob.mx/se/acciones-y-programas/comercio-exterior-paises-con-tratados-y-acuerdos-firmados-con-mexico

## No forma parte de este PR

Esta rama contiene sólo RFC. No activa nuevas funciones, no modifica la interpretación legal oficial, no crea datos sin evidencia y no habilita despliegues. La implementación requerirá PR(s) de código con fixtures, métricas y revisión técnica/jurídica.
