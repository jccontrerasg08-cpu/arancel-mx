# RFC: Valoración, IGI/DTA/IEPS/IVA, INPC y garantías

> **Estado:** propuesta de implementación — documentación únicamente. **Prioridad:** P0. **Corte:** 2026-11-21.
> **Trazabilidad:** [inventario NotebookLM de 42 entradas](../../research/notebooklm-source-inventory-2026-11-21.json) y [auditoría](../../research/notebooklm-source-audit-2026-11-21.md). La conversación de Gemini se revisó; no se ha inspeccionado el interior de los seis elementos de Studio ni transcrito todos los videos.

## Estado existente y por qué no duplicarlo

La ruta /trade ya muestra escenarios orientativos; docs/research/trade-assistant-source-plan.md delimita su alcance. El proyecto NO es un generador ni liquidador oficial de pedimentos.

## Resultado esperado y experiencia de usuario

Motor de escenarios con fórmulas explicables, entradas declaradas y fuentes legales versionadas: valor en aduana, IGI, DTA, IEPS, IVA, actualización INPC, recargos, precios estimados/garantías y regímenes, desglosando los casos no calculables.

1. Ingresar valor comercial, moneda, fecha, tipo de cambio, flete, seguro, incrementables y régimen declarado.
2. Ver descomposición fiscal y fórmulas con vigencia por concepto sin presentarla como liquidación definitiva.
3. Comparar escenarios sin usar tasas de tratado no verificadas ni suponer 16% IVA o 8 al millar DTA universales.
4. Descargar escenario local explicando supuestos, datos faltantes, fórmulas y fuentes.

## Arquitectura propuesta

- Reusar herramienta /trade; introducir reglas versionadas por componente e instrument_id, effective_from/effective_to, required_inputs y supported_cases.
- Separar cálculo de base de valoración, IGI ad valorem/mixto/específico, DTA, IEPS, IVA, actualización, intereses, garantías.
- Montos con Decimal y redondeo documentado; no aplicar tarifa numérica de IGI a tipos no ad valorem.
- Modelo de tres estados: calculable ilustrativo, no calculable con causas, requiere revisión profesional.
- Fases de activación con fixtures y revisión fiscal-aduanera por familia de producto; sin envío de pedimentos o COVE.
- INPC y tipo de cambio necesitan series oficiales y corte temporal; garantía por precios estimados requiere catálogo oficial validado.

## Contrato lógico de ejemplo (NO implementado)

~~~json
{
  "dataset_version": "data-YYYY.MM.DD",
  "operation_date": "YYYY-MM-DD",
  "inputs": {
    "commercial_value": "user_declared",
    "incoterm": "user_declared",
    "incrementables": "unknown",
    "regime": "unknown"
  },
  "components": [
    {
      "id": "igi",
      "status": "not_calculable",
      "formula_id": null,
      "amount_mxn": null,
      "source_url": null
    }
  ],
  "total_status": "partial_not_official",
  "decision_is_binding": false
}
~~~

**Metadatos obligatorios:** identificador de fuente/instrumento, URL oficial, fecha de consulta, versión/corte, fecha de publicación y vigencia cuando se confirme, captura SHA-256 cuando existan bytes, datos declarados vs oficiales y estados `unknown`/`unavailable` distintos de «no aplica».

## Reglas de seguridad legal y de datos

- No calcular tasas universales ni redondeos sin expediente de fuente y vigencia legal.
- Distinguir reforma legislativa, actualización de cuotas e INPC; no reemplazar la primera por las otras.
- IVA depende del supuesto de importación, exenciones y composición de base gravable; no hardcodear generalidad.
- Valor en aduana puede requerir métodos distintos al transaccional: si faltan antecedentes, no fingir resultado.
- No validar origen T-MEC, inscripción IMMEX, precio estimado ni garantías mediante un booleano del usuario.

## Pruebas y criterios de aceptación

- [ ] Decimal, moneda, redondeo, negativos, null, fechas límite y diferencias entre reglas.
- [ ] Fixtures de tasa específica y mixta: no calculable sin fórmula confirmada.
- [ ] UI y export: mostrar siempre supuestos, fuente, vigencia e incertidumbre.
- [ ] Revisión de especialista previo a cálculos de IEPS, garantías o régimen complejo.
- [ ] No alterar releases LIGIE/NICO, source_registry.json ni reactivar el endpoint /v1 retirado sin ADR formal.
- [ ] Definir estrategia de fallos, rollback, compatibilidad, latencia, accesibilidad y textos en español/inglés.

## Fases de implementación

1. Matriz de operaciones soportadas y reglas con fixtures
2. Valoración/IGI para casos acotados, cálculo explicable
3. DTA/IVA/IEPS, INPC, recargos, garantías y regímenes por submódulos certificados

## Decisiones abiertas y bloqueos

Confirmar bases, excepciones y vigencia caso por caso; no publicar un 'cálculo completo de pedimento' como promesa de producto.

## Mapa de fuentes del notebook y oficiales

- Notebook entradas 11–36: LAdua, CFF, LFD, LIEPS, LIVA, LFISAN, LISR, LGOAAC.
- https://www.sat.gob.mx/minisitio/NormatividadRMFyRGCE/normatividad_rmf_rgce2026.html
- https://www.diputados.gob.mx/LeyesBiblio/ref/ladua.htm
- https://www.diputados.gob.mx/LeyesBiblio/ref/lfd.htm
- https://www.diputados.gob.mx/LeyesBiblio/ref/lieps.htm

## Alcance de este PR

**Sólo RFC.** No contiene implementación, modificación de esquemas canónicos, publicación de nuevas tasas, automatización fiscal, decisiones vinculantes ni despliegue. Cada fase requiere PR de código, pruebas y verificación legal cuando corresponda.
