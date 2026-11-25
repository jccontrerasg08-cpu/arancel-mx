# Roadmap de funcionalidades · NotebookLM → arancel-mx (2026-11-21)

> **Estado:** PRs RFC abiertos como draft, ninguno de estos PRs añade código funcional. Se fundamentan en [auditoría de fuentes fusionada en #300](https://github.com/jccontrerasg08-cpu/arancel-mx/pull/300), [inventario de 42 entradas](../../research/notebooklm-source-inventory-2026-11-21.json) y [catálogos existentes](../../research/external-trade-source-catalog.json).

## Por qué existe este índice

Gemini propuso componentes que ya están parcialmente presentes en el repositorio. Este roadmap conserva esos activos y separa toda capacidad nueva según dominio: sin duplicar vigilancia del DOF, notas nacionales, NOM del Anexo 2.4.1, API GET-only, /trade, /moa ni analítica INEGI reciente. Cada PR incluye historias, contratos, pruebas, dependencias, límites regulatorios y fases.

**Alcance real de la investigación:** NotebookLM muestra 42 entradas/41 títulos únicos por duplicación de LSH.pdf; se leyeron las respuestas visibles y los encabezados de 25 PDF legislativos únicos, pero NO se auditó el articulado íntegro de todas las leyes, ni se leyó internamente cada recurso Studio, ni se verificaron por separado los once videos. Los vínculos a documentos no son prueba automática de vigencia; comparar DOF, reformas y transitorios.

## PRs por funcionalidad

| Orden | Prioridad | RFC | Enlace |
|---:|---|---|---|
| 1 | P0 | RRNA/NOM/PEC y autoridades | [PR #302](https://github.com/jccontrerasg08-cpu/arancel-mx/pull/302) |
| 2 | P0 | Escenarios de impuestos y valoración | [PR #303](https://github.com/jccontrerasg08-cpu/arancel-mx/pull/303) |
| 3 | P1 | Notas y criterios SAT | [PR #304](https://github.com/jccontrerasg08-cpu/arancel-mx/pull/304) |
| 4 | P1 | Matriz de TLC y origen | [PR #306](https://github.com/jccontrerasg08-cpu/arancel-mx/pull/306) |
| 5 | P1 | Análisis INEGI BCMM / TIGIE-SCIAN | [PR #307](https://github.com/jccontrerasg08-cpu/arancel-mx/pull/307) |
| 6 | P1 | Cambios DOF y diff de releases | [PR #308](https://github.com/jccontrerasg08-cpu/arancel-mx/pull/308) |
| 7 | P2 | DuckDB WASM en navegador | [PR #309](https://github.com/jccontrerasg08-cpu/arancel-mx/pull/309) |
| 8 | P2 | SDK JS/Go y derivados abiertos | [PR #310](https://github.com/jccontrerasg08-cpu/arancel-mx/pull/310) |
| 9 | P1 | Ficha PDF/Markdown | [PR #311](https://github.com/jccontrerasg08-cpu/arancel-mx/pull/311) |
| 10 | P2 | Búsqueda híbrida/IA responsable | [PR #312](https://github.com/jccontrerasg08-cpu/arancel-mx/pull/312) |
| 11 | P1 | MOA/régimen y documentación | [PR #313](https://github.com/jccontrerasg08-cpu/arancel-mx/pull/313) |
| 12 | P2 | Módulo 8 y Studio / Ruta Logística | [PR #314](https://github.com/jccontrerasg08-cpu/arancel-mx/pull/314) |

**Importante:** cada RFC está en una rama independiente, por lo que su archivo solo se verá en `main` después de un merge autorizado. Los enlaces anteriores llevan directamente a su PR (no a archivos futuros inexistentes en `main`).

## Matriz de requisitos que recoge las propuestas de Gemini

| ID | Descripción operativa y verificable | RFC responsable |
|---|---|---|
| 01.1 | NOM/RRNA por fracción y NICO con acotación, vigencia, autoridad y tipo de fuente | [#302](https://github.com/jccontrerasg08-cpu/arancel-mx/pull/302) |
| 01.2 | PEC, OEC, inspección/muestreo, equivalencia y reconocimiento mutuo con evidencia | [#302](https://github.com/jccontrerasg08-cpu/arancel-mx/pull/302) |
| 01.3 | Derechos por trámites reguladores solo desde fuente aplicable | [#302](https://github.com/jccontrerasg08-cpu/arancel-mx/pull/302) |
| 01.4 | Diferenciar anexo disponible, ausente y carried_forward | [#302](https://github.com/jccontrerasg08-cpu/arancel-mx/pull/302) |
| 02.1 | Valor en aduana e incrementables y métodos alternativos | [#303](https://github.com/jccontrerasg08-cpu/arancel-mx/pull/303) |
| 02.2 | IGI, DTA, IVA, IEPS por caso y base legal | [#303](https://github.com/jccontrerasg08-cpu/arancel-mx/pull/303) |
| 02.3 | INPC, actualizaciones, recargos y garantías por precios estimados | [#303](https://github.com/jccontrerasg08-cpu/arancel-mx/pull/303) |
| 02.4 | Regímenes fiscales con inputs declarados y resultado orientativo | [#303](https://github.com/jccontrerasg08-cpu/arancel-mx/pull/303) |
| 03.1 | Visor notas de sección, capítulo y notas nacionales | [#304](https://github.com/jccontrerasg08-cpu/arancel-mx/pull/304) |
| 03.2 | Índice de criterios SAT, consultas y precedentes judiciales distinguidos por tipo | [#304](https://github.com/jccontrerasg08-cpu/arancel-mx/pull/304) |
| 04.1 | Comparación de IGI general contra tasas preferenciales oficiales por fecha y acuerdo | [#306](https://github.com/jccontrerasg08-cpu/arancel-mx/pull/306) |
| 04.2 | Reglas de origen, resoluciones, instrumentos y comprobación documental sin decidir elegibilidad | [#306](https://github.com/jccontrerasg08-cpu/arancel-mx/pull/306) |
| 05.1 | Correlación TIGIE/NICO con SCIAN con versión/cardenalidad | [#307](https://github.com/jccontrerasg08-cpu/arancel-mx/pull/307) |
| 05.2 | BCMM y BIE por periodo, flujo, país, producto, valor FOB, confidencialidad y vintage | [#307](https://github.com/jccontrerasg08-cpu/arancel-mx/pull/307) |
| 05.3 | Balanza/crecimiento/consumo aparente solo con producción nacional comparable | [#307](https://github.com/jccontrerasg08-cpu/arancel-mx/pull/307) |
| 06.1 | Comparador entre versiones inmutables por código, NICO, tasa, descripción, notas y fechas | [#308](https://github.com/jccontrerasg08-cpu/arancel-mx/pull/308) |
| 06.2 | Reuso del watcher DOF, feed de cambios y triage humano, sin duplicar bot | [#308](https://github.com/jccontrerasg08-cpu/arancel-mx/pull/308) |
| 07.1 | Consultas SQL locales opt-in, worker, SHA de release, caché y benchmarks reales | [#309](https://github.com/jccontrerasg08-cpu/arancel-mx/pull/309) |
| 08.1 | SDKs TypeScript y Go con paridad Python/CLI, API estática y release fija | [#310](https://github.com/jccontrerasg08-cpu/arancel-mx/pull/310) |
| 08.2 | Descargas Parquet, SQLite y JSON-LD como derivados opcionales separados de seis assets | [#310](https://github.com/jccontrerasg08-cpu/arancel-mx/pull/310) |
| 09.1 | Exportar ficha imprimible de fracción/NICO con versión, notas, fuentes y secciones referenciales de NOM/TLC/impuestos | [#311](https://github.com/jccontrerasg08-cpu/arancel-mx/pull/311) |
| 10.1 | Recuperación semántica de candidatos, evaluación de calidad y abstención, nunca clasificación jurídica | [#312](https://github.com/jccontrerasg08-cpu/arancel-mx/pull/312) |
| 11.1 | Guías por regímenes definitivos, temporales, depósito, tránsito, recintos e IMMEX | [#313](https://github.com/jccontrerasg08-cpu/arancel-mx/pull/313) |
| 11.2 | Mapa de COVE, transmisión y prevalidación, Anexo 22 y autoridad | [#313](https://github.com/jccontrerasg08-cpu/arancel-mx/pull/313) |
| 11.3 | Checklists orientativos sin credenciales, trámites ni pedimento | [#313](https://github.com/jccontrerasg08-cpu/arancel-mx/pull/313) |
| 12.1 | Cinco unidades educativas propias sobre fuentes, regulación, cálculo, industria y notas | [#314](https://github.com/jccontrerasg08-cpu/arancel-mx/pull/314) |
| 12.2 | Seis creaciones Studio identificadas con contenido aún no inspeccionado | [#314](https://github.com/jccontrerasg08-cpu/arancel-mx/pull/314) |
| 12.3 | Once videos/cápsulas citados por Gemini y pendientes de verificación individual | [#314](https://github.com/jccontrerasg08-cpu/arancel-mx/pull/314) |

## Trazabilidad de las 42 fuentes del panel

Una relación temática significa «material de estudio para ese RFC», NO que una ley cubre automáticamente la operación, ni que se ha leído toda ella. Los títulos y URL se preservan en [el registro JSON](feature-coverage-2026-11-21.json); la fecha de las portadas PDF, cuando se obtuvo, tiene significado distinto a la última reforma.

| # | Entrada visible | PRs |
|---:|---|---|
| 1 | Datos Arancelarios MX | #314 |
| 2 | arancel-mx — Consulta el arancel de México, con su evidencia. | #302, #304, #307, #308, #311, #312 |
| 3 | arancel-mx — Manual de Operación Aduanera, en contexto. | #313, #314 |
| 4 | Balanza | #307, #314 |
| 5 | Balanza comercial | #307, #314 |
| 6 | Balanza Comercial de Mercancías de México (BCMM) | #307, #314 |
| 7 | Clasificadores - Catálogo TIGIE - SCIAN | #307, #314 |
| 8 | Cuéntame de México | #307, #314 |
| 9 | DOF - Diario Oficial de la Federación | #302, #303, #304, #306, #308, #313 |
| 10 | GitHub - jccontrerasg08-cpu/arancel-mx: Open-source tools and traceable public data for Mexico's LIGIE, NICO, and tariff analysis · GitHub | #308, #309, #310, #311, #312 |
| 11 | https://www.diputados.gob.mx/LeyesBiblio/pdf/65_071220.pdf | #313, #314 |
| 12 | https://www.diputados.gob.mx/LeyesBiblio/pdf/207.pdf | #302, #313, #314 |
| 13 | https://www.diputados.gob.mx/LeyesBiblio/pdf/CFF.pdf | #303, #313, #314 |
| 14 | https://www.diputados.gob.mx/LeyesBiblio/pdf/LAdua.pdf | #302, #303, #304, #306, #313, #314 |
| 15 | https://www.diputados.gob.mx/LeyesBiblio/pdf/LCPAF.pdf | #313, #314 |
| 16 | https://www.diputados.gob.mx/LeyesBiblio/pdf/LFAFE.pdf | #302, #313, #314 |
| 17 | https://www.diputados.gob.mx/LeyesBiblio/pdf/LFCPQ.pdf | #302, #313, #314 |
| 18 | https://www.diputados.gob.mx/LeyesBiblio/pdf/LFD.pdf | #302, #303, #314 |
| 19 | https://www.diputados.gob.mx/LeyesBiblio/pdf/LFISAN.pdf | #303, #314 |
| 20 | https://www.diputados.gob.mx/LeyesBiblio/pdf/LFMZAAH.pdf | #302, #313, #314 |
| 21 | https://www.diputados.gob.mx/LeyesBiblio/pdf/LFSA.pdf | #302, #313, #314 |
| 22 | https://www.diputados.gob.mx/LeyesBiblio/pdf/LFSV.pdf | #302, #313, #314 |
| 23 | https://www.diputados.gob.mx/LeyesBiblio/pdf/LFZEE.pdf | #313, #314 |
| 24 | https://www.diputados.gob.mx/LeyesBiblio/pdf/LGEEPA.pdf | #302, #313, #314 |
| 25 | https://www.diputados.gob.mx/LeyesBiblio/pdf/LGOAAC.pdf | #303, #313, #314 |
| 26 | https://www.diputados.gob.mx/LeyesBiblio/pdf/LGPAS.pdf | #302, #313, #314 |
| 27 | https://www.diputados.gob.mx/LeyesBiblio/pdf/LGS.pdf | #302, #313, #314 |
| 28 | https://www.diputados.gob.mx/LeyesBiblio/pdf/LGTOC.pdf | #313, #314 |
| 29 | https://www.diputados.gob.mx/LeyesBiblio/pdf/LGVS.pdf | #302, #313, #314 |
| 30 | https://www.diputados.gob.mx/LeyesBiblio/pdf/LICal_010720.pdf | #302, #314 |
| 31 | https://www.diputados.gob.mx/LeyesBiblio/pdf/LIEPS.pdf | #303, #314 |
| 32 | https://www.diputados.gob.mx/LeyesBiblio/pdf/LISR.pdf | #303, #314 |
| 33 | https://www.diputados.gob.mx/LeyesBiblio/pdf/LIVA.pdf | #303, #314 |
| 34 | https://www.diputados.gob.mx/LeyesBiblio/pdf/LNCM.pdf | #313, #314 |
| 35 | https://www.diputados.gob.mx/LeyesBiblio/pdf/LSH.pdf | #302, #313, #314 |
| 36 | https://www.diputados.gob.mx/LeyesBiblio/pdf/LSH.pdf | #302, #313, #314 |
| 37 | https://www.snice.gob.mx/cs/avi/snice/biblioteca.juridica.tasas.html | #306, #314 |
| 38 | https://www.snice.gob.mx/cs/avi/snice/biblioteca.juridica.tlc.html | #306, #314 |
| 39 | https://www.snice.gob.mx/cs/avi/snice/f.c.indic.int.html | #307, #314 |
| 40 | Instituto Nacional de Estadística y Geografía (INEGI) | #307, #314 |
| 41 | International Business | #314 |
| 42 | Ruta Logística MX - YouTube | #314 |

## Seis elementos Studio visibles; contenido interno pendiente

1. **Estrategia Transnacional Global** (slides; NotebookLM indicó 40 fuentes). Necesita inspección del contenido y derechos antes de publicar material derivado.
2. **Balanza Comercial de México 2024** (infographic; NotebookLM indicó 40 fuentes). Necesita inspección del contenido y derechos antes de publicar material derivado.
3. **Comercio Exterior Cuestionario** (quiz; NotebookLM indicó 40 fuentes). Necesita inspección del contenido y derechos antes de publicar material derivado.
4. **Derecho Aduanero Tarjetas** (flashcards; NotebookLM indicó 40 fuentes). Necesita inspección del contenido y derechos antes de publicar material derivado.
5. **Dependencias Gubernamentales Mapa Mental** (mindmap; NotebookLM indicó 40 fuentes). Necesita inspección del contenido y derechos antes de publicar material derivado.
6. **Navegando el Comercio Internacional y la Regulación Jurídica en México** (report; NotebookLM indicó 41 fuentes). Necesita inspección del contenido y derechos antes de publicar material derivado.

## Once videos/cápsulas que Gemini enumeró, aún sin auditoría individual

Los títulos y duraciones de abajo son **afirmaciones visibles de Gemini**, no una revisión independiente de cada video. Antes de usar un video deben verificarse URL, fecha, licencia, transcripción y exactitud del temario.

1. Módulo 1: Contexto y Fundamentos de la Reforma Aduanera — duración declarada por Gemini: 3 h 31 min.
2. Módulo 2: Actores y Atribuciones de la Reforma Aduanera — duración declarada por Gemini: 3 h 27 min.
3. Módulo 3: Procesos Operativos del Despacho Aduanero — duración declarada por Gemini: 3 h 35 min.
4. Módulo 4: Fiscalización y Cumplimiento Aduanero — duración declarada por Gemini: 3 h 18 min.
5. Módulo 5: Digitalización y Facilitación Comercial — duración declarada por Gemini: 2 h 23 min.
6. Módulo 6: Aplicación Práctica y Visión Estratégica ante la Reforma — duración declarada por Gemini: 2 h 26 min.
7. Viernes: De la Operación Reactiva a la Logística Inteligente — duración declarada por Gemini: 1 h 58 min.
8. Viernes: Innovación Logística - Control de Inventarios — duración declarada por Gemini: 1 h 57 min.
9. Viernes: ¿Cómo andamos con la Mensajería y Paquetería? — duración declarada por Gemini: 1 h 02 min.
10. Viernes: El Nuevo Pasaporte del Talento — duración declarada por Gemini: 1 h 35 min.
11. Cápsula: Logística en México: Datos, Retos y Oportunidades — duración declarada por Gemini: 6 min 26 s.

**Currículo editorial del proyecto, no módulo oficial identificado:** (1) datos abiertos, TIGIE/NICO y procedencia; (2) RRNA/NOM/LIC y autoridades; (3) fiscalidad, valor, COVE y regímenes; (4) BCMM/TIGIE–SCIAN, balanza, consumo aparente y TLC; (5) notas nacionales/criterios SAT. El calendario público de Ruta Logística MX 2026 debe investigarse por separado de este módulo propio. [Secretaría de Economía](https://www.gob.mx/se/prensa/inicia-la-segunda-fase-de-ruta-logistica-mx-2026-mexico-la-nueva-ruta-del-mundo?state=published).

## Afirmaciones de Gemini que no se promueven como hechos

- **8,183 fracciones y 11,507 NICO** → Conteo atribuido por Gemini al proyecto; cotejar con manifest y tag concreto.
- **8,177 fracciones, 11,507 NICO, 1,086 clases SCIAN** → Corte atribuido a la correlación INEGI 2025, no idéntico al inventario LIGIE 2026.
- **DuckDB-WASM 0 ms de latencia** → Afirmación técnicamente incorrecta; definir benchmark de descarga, startup y SQL.
- **Módulo 8 de Ruta Logística = tecnología y datos abiertos** → Título editorial propuesto por Gemini; no atribuir a programa oficial.
- **Una tasa IVA/DTA/IEPS aplica universalmente a la importación** → Depende de supuestos y vigencia de instrumentos; requiere revisión especialista.
- **Fracción/NICO determina automáticamente NOM aplicable y cumplimiento** → Es señal de revisión, no acredita cumplimiento específico.
- **País de origen determina por sí solo una preferencia TLC** → No sustituye prueba ni regla específica del tratado.
- **Puntaje semántico de IA equivale a probabilidad de clasificación legal** → No demostrar sin evaluación/calibración; no presentarlo como precisión legal.

## Secuencia de entrega por dependencias

**Gate 0 — gobierno de datos:** confirmar corpus oficial, transitorios, fecha y derecho de reutilización. La ficha de catálogo no convierte referencia en obligación. Mantener los seis assets de las releases y GET-only /data/v1; cambios requieren ADR.

**P0:** RFC #302 RRNA sobre NOM existente, RFC #303 escenarios fiscales explicables; aprobar fixtures legales y límites antes de UI nueva.

**P1:** #304 notas/SAT, #306 TLC, #307 SCIAN/BCMM, #308 diff, #311 ficha, #313 MOA; avanzar desde datos y contratos hacia UX. No convertir el proyecto en sistema de despacho.

**P2:** #309 DuckDB-WASM y benchmarks, #310 SDKs/formatos con contratos, #312 IA con evaluación y abstención, #314 formación y recursos con licencias.

**Criterios por PR de implementación:** ADR, fuente oficial primaria, compatibilidad con release exacta, datos de prueba, E2E, CI, seguridad, privacidad, accesibilidad, métricas, rollback, revisión del propietario y despliegue explícitamente autorizado.

## Registro estructurado para contribuir

[feature-coverage-2026-11-21.json](feature-coverage-2026-11-21.json) recoge 12 RFCs, 28 grupos de requisitos, 42 fuentes, seis recursos Studio, once afirmaciones de videos y ocho afirmaciones de Gemini sujetas a comprobación. No es fuente jurídica ni sustituye textos oficiales.
