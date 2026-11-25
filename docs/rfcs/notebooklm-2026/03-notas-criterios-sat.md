# RFC: Notas oficiales y buscador de criterios SAT

> **Estado:** propuesta de implementación — documentación únicamente. **Prioridad:** P1. **Corte:** 2026-11-21.
> **Trazabilidad:** [inventario NotebookLM de 42 entradas](../../research/notebooklm-source-inventory-2026-11-21.json) y [auditoría](../../research/notebooklm-source-audit-2026-11-21.md). La conversación de Gemini se revisó; no se ha inspeccionado el interior de los seis elementos de Studio ni transcrito todos los videos.

## Estado existente y por qué no duplicarlo

Notas nacionales y national-notes/{hs2}.json ya se publican; faltan relaciones pedagógicas por sección/capítulo y un corpus de criterios clasificado, si existe evidencia legal capturable.

## Resultado esperado y experiencia de usuario

Mejorar visor de notas de sección, capítulo y nacionales y crear una biblioteca independiente de criterios de clasificación publicados, diferenciando resolución SAT, criterio normativo, consulta y precedente judicial.

1. Ver las notas relevantes y su origen al consultar HS6, fracción y NICO.
2. Buscar por concepto, documento, autoridad, fecha y código mencionado, sin respuesta automática de clasificación.
3. Comparar notas entre releases cuando la evidencia histórica lo soporte.

## Arquitectura propuesta

- Reutilizar contrato de national-notes y árbol de capítulos. No crear notas duplicadas.
- Capa lateral de criterios con tipo, identificador documental, autoridad, título, texto breve, fecha, vigencia, código explicitado, SHA y URL.
- No mezclar criterios SAT con jurisprudencia judicial ni asumir jerarquía normativa común.
- Búsqueda textual exacta antes de filtros semánticos; coincidencia de términos no prueba clasificación.
- Derechos de reproducción: preferir índice, citas breves y link oficial; no copiar corpus no redistribuible.

## Contrato lógico de ejemplo (NO implementado)

~~~json
{
  "criterion_id": "authority:instrument:section",
  "kind": "sat_criteria|consultation_resolution|court_reference",
  "title": "texto",
  "authority": "SAT",
  "published_at": null,
  "source_url": "https://...",
  "effective_from": null,
  "code_relations": [
    {
      "code": "XXXXXXXX",
      "relation": "explicit_reference"
    }
  ],
  "classification_decision": false
}
~~~

**Metadatos obligatorios:** identificador de fuente/instrumento, URL oficial, fecha de consulta, versión/corte, fecha de publicación y vigencia cuando se confirme, captura SHA-256 cuando existan bytes, datos declarados vs oficiales y estados `unknown`/`unavailable` distintos de «no aplica».

## Reglas de seguridad legal y de datos

- No declarar un NICO correcto por semejanza, nota o resolución de otro caso.
- La naturaleza y fuerza de cada criterio se comprueban en el instrumento; no llamar obligatoria a toda nota/guía sin leerlo.
- Distinguir fecha de criterio, consulta, transitorio, vigencia y revisión de fuentes.
- Nunca indexar material privado del notebook ni contenidos con derechos sin autorización.

## Pruebas y criterios de aceptación

- [ ] Paridad de notas nacionales y árboles actuales.
- [ ] Fixtures de documentos de nombre igual pero distinto tipo; preservar autoridad y URL.
- [ ] Navegación sin clasificación implícita y con estados de fuente desconocida.
- [ ] E2E de búsqueda y accesibilidad, y pruebas de formato/versionado.
- [ ] No alterar releases LIGIE/NICO, source_registry.json ni reactivar el endpoint /v1 retirado sin ADR formal.
- [ ] Definir estrategia de fallos, rollback, compatibilidad, latencia, accesibilidad y textos en español/inglés.

## Fases de implementación

1. Notas contextuales con contratos existentes
2. Fuentes piloto de criterios y taxonomía legal aprobada
3. Búsqueda facetada y vínculos entre documentos y códigos con evidencia

## Decisiones abiertas y bloqueos

Elegir corpus oficial publicable y autoridad por tipo; no exponer criterios en fuente cruzada sin verificar estatus jurídico.

## Mapa de fuentes del notebook y oficiales

- Notebook entradas 9, 10, 11–36 y 37–38, con especial foco LAdua y LIGIE.
- https://www.snice.gob.mx/cs/avi/snice/ligie.notasnac22.html
- https://www.diputados.gob.mx/LeyesBiblio/ref/ladua.htm

## Alcance de este PR

**Sólo RFC.** No contiene implementación, modificación de esquemas canónicos, publicación de nuevas tasas, automatización fiscal, decisiones vinculantes ni despliegue. Cada fase requiere PR de código, pruebas y verificación legal cuando corresponda.
