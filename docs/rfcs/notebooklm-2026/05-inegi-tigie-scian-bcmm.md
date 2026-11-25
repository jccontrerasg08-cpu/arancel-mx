# RFC: Inteligencia económica TIGIE–SCIAN, BCMM y consumo aparente

> Estado: propuesta exclusivamente documental | Prioridad: P1 | Fecha: 2026-11-21
> Basado en [inventario NotebookLM (42 entradas)](../../research/notebooklm-source-inventory-2026-11-21.json) y [auditoría](../../research/notebooklm-source-audit-2026-11-21.md); las respuestas de Gemini no sustituyen lectura de fuentes primarias.

## Punto de partida: evitar duplicación

Ya hay contrato INEGI, catálogo estadístico, API BIE de tres series, página /trade-analytics y narrativa de estructura/estados incorporadas por PR #299. Falta una ingesta multidimensional controlada y un cruce versionado TIGIE–SCIAN.

## Problema, alcance y resultado

Explorar comercio por fracción/NICO, socio, periodo y actividad SCIAN; cálculos de balanza, crecimiento, concentración y consumo aparente **sólo cuando producción nacional compatible esté documentada**.

## Historias de usuario

1. Buscar industria SCIAN asociada a una fracción respetando versión y cardinalidad de correlación.
2. Filtrar BCMM por periodo, flujo, país, HS2/4/6/8/NICO y ver valor FOB, cantidad y unidades comparables.
3. Exportar CSV con vintage, estatus de cifras y controles de confidencialidad.
4. Consultar consumo aparente sólo cuando una serie de producción nacional comparable por producto/periodo y una conversión válida estén disponibles.

## Arquitectura técnica propuesta

- Tres fuentes separadas: BIE-BISE agregado (IDs 33860,33861,33229), BCMM cubo/archivos abiertos y tabla TIGIE–SCIAN, sin fingir dimensiones que API de indicadores no tiene.
- Modelo de snapshots para BCMM con periodo, release date, flujo, país, código, unidad, valor, estado de cifra, ocultamiento C y fuente; no persistir microdatos confidenciales.
- Correlación TIGIE–SCIAN oficial con vintage (actualización 2025 no equivale a release 2026); registrar relaciones y cardinalidad reales, nunca suponer unívoca hasta medir.
- Desacoplar descargas grandes: ETL servidor/Actions por partes, SQL local de artefactos analíticos publicados y consultas paginadas o preagregados estáticos; sin cargar millones de filas al navegador.
- Fórmulas: saldo = X-M solo periodos y universos coincidentes; share = parte/total comparable; YoY por mismo periodo; consumo aparente = producción + importaciones - exportaciones solo magnitudes homogéneas.
- Publicar solo agregados permitidos: 'C' indica dato suprimido, no 0; respetar estado oportuna/revisada/definitiva/ajustada/corregida.
- Conectar UX existente en /trade-analytics, /data y ficha sin duplicar storytelling de PR #299.

## Contrato JSON de referencia, no implementado

~~~json
{
  "source": "INEGI_BCMM",
  "dataset_version": "official-vintage",
  "reference_period": "YYYY-MM",
  "flow": "import|export",
  "value_usd": null,
  "valuation_basis": "FOB",
  "tariff_code": "XXXXXXXXXX",
  "unit": null,
  "figure_status": "reviewed|final|adjusted|confidential",
  "scian_mapping": {
    "version": "2025",
    "relation_count": null,
    "classes": []
  },
  "calc": {
    "balance": null,
    "apparent_consumption": {
      "status": "not_calculable_until_production_series_verified"
    }
  }
}
~~~

Cada dato nuevo debe enlazar fuente, autoridad, documento/version, retrieved_at, published_at/effective_date si se conoce, SHA256 cuando se conserva bytes, estado y fecha de revisión. Sin datos se representa unknown y no cero.

## Invariantes y límites

- No comparar montos FOB con CIF como equivalentes, ni realizar comparación interanual sin vintage y cobertura homogénea.
- No sumar cantidades de UMED diferentes ni reconstruir celdas C por sustracción.
- No usar 8,177 fracciones (INEGI correlación 2025) para validar o sustituir automáticamente 8,183 registros de una release futura.
- No inferir clase SCIAN por similitud de nombre ni fabricar producción nacional a partir de importaciones.

## Casos de prueba y definición de terminado

- [ ] Fixtures INEGI con estados C, revisado, ajustado, cambios de versión TIGIE.
- [ ] Correlación con uno-a-muchos/muchos-a-uno si existe; verificación real de claves y sin duplicación en joins.
- [ ] Test de saldo contra totales INEGI por periodo/currency/vintage.
- [ ] Cálculo de consumo aparente bloqueado sin producción comparable, reglas de agregación y fuente.
- [ ] Pruebas de rendimiento/bundle sin carga de dataset masivo al cliente.
- [ ] Compatibilidad de API estática /data/v1, sin alterar la release canónica ni revivir /v1 dinámico.
- [ ] Documentar costes, medidas de rendimiento, UX de accesibilidad, seguridad, errores, rollbacks y traducción antes de pasar a código.

## Entrega incremental

1. Mapa de cobertura y contrato de correlación con versionado
2. ETL BCMM/joins con fixtures y reportes de calidad
3. UI por socio/producto/industria y exportaciones reproducibles
4. Consumo aparente solo tras encontrar producción nacional compatible

## Investigaciones pendientes

Confirmar disponibilidad, descarga y licencia de tabla TIGIE–SCIAN y desgloses BCMM, así como series de producción nacional y denominadores comparables.

## Fuentes del NotebookLM y primarias

- Notebook entradas 4–8, 39–40 y 10; propuesta de Gemini de 8,177 fracciones, 11,507 NICOs, 1,086 clases SCIAN a verificar por corte.
- https://www.inegi.org.mx/app/tigie/
- https://www.inegi.org.mx/programas/comext/default.html
- https://inegi.org.mx/contenidos/productos/prod_serv/contenidos/espanol/bvinegi/productos/nueva_estruc/889463929079.pdf

## No forma parte de este PR

Esta rama contiene sólo RFC. No activa nuevas funciones, no modifica la interpretación legal oficial, no crea datos sin evidencia y no habilita despliegues. La implementación requerirá PR(s) de código con fixtures, métricas y revisión técnica/jurídica.
