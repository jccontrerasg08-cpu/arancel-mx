# Contrato analítico de INEGI para Arancel‑mx

> Alcance: organizar las series nacionales actuales y preparar visualizaciones reproducibles de BCMM por país, mercancía y NICO. Este contrato no agrega cifras ficticias ni sustituye las consultas oficiales de INEGI.

## Decisión de fuentes

| Producto INEGI | Papel en la aplicación | Ruta técnica |
|---|---|---|
| API del Banco de Indicadores (BIE-BISE) | Resumen nacional mensual: exportaciones, importaciones y saldo. | Conexión server-side actual a los indicadores 33860, 33861 y 33229. |
| Datos Abiertos Mensuales de BCMM | Conjuntos publicados para análisis de comercio por país, mercancía u otras dimensiones, según cada archivo. | Ingesta de archivos oficiales, esquema por conjunto y procesamiento en servidor. |
| Cubo mensual de BCMM | Consultas con cruces multidimensionales, fracción/NICO, país, cantidad y valor; algunas tablas incluyen aduana/modo. | Reproducir sólo dimensiones presentes en la consulta/documentación oficial; conservar exportación y metadatos. |

La API de Indicadores y el Cubo de BCMM son productos distintos. Las tres series BIE actuales no contienen campos para país, fracción, NICO o modo de transporte. Las gráficas desglosadas deben usar los archivos abiertos o tablas/Cubo oficiales, no inferir campos faltantes de la respuesta de indicadores.

## Catálogo semántico

El archivo [inegi-analytics-catalog.json](inegi-analytics-catalog.json) define fuentes, indicadores, dimensiones, estados y vistas candidatas de forma legible por máquina.

### Hechos

- **Valor de exportación/importación:** valor reportado en la moneda disponible en el conjunto, con su moneda/unidad y base de valoración.
- **Cantidad:** valor cuantitativo con UMED; no sumar ni comparar cantidades cuando las unidades no coincidan.
- **Saldo comercial:** exportaciones menos importaciones para el mismo periodo, moneda, universo, revisión y nivel de agregación.
- **Códigos de estado:** estado de la publicación y estado de disponibilidad de la cifra deben mantenerse como variables distintas.

### Dimensiones

- Periodo: año y mes.
- Flujo: exportación o importación.
- País: origen y/o destino, según definición de la tabla.
- Mercancía: nivel HS/TIGIE: capítulo, partida, subpartida, fracción y NICO, donde exista.
- Unidad de medida y moneda.
- Aduana de entrada/salida y modo de transporte cuando el conjunto específico los incluya.
- Estatus estadístico / vintage de la publicación.

## Vistas para distintos usuarios

| Vista | Gráfica principal | Lectura guiada |
|---|---|---|
| Resumen | Tarjetas KPI + serie temporal | Qué se exporta/importa y cómo cambió el saldo; señala periodo, unidad y estatus. |
| Países | Ranking + barras de participación | Principales socios y cambio interanual comparable. |
| Mercancías | Treemap o barras por capítulo/partida/fracción/NICO | Composición, cambios y jerarquía del código con vínculo al explorador arancelario. |
| Rutas físicas | Barras o mapa sólo si la cobertura geográfica lo respalda | Modo de transporte y aduana cuando existan en el conjunto; no inferir rutas. |
| Analista | Tabla filtrable + exportación CSV | Filtros y notas de cobertura/vintage visibles; resultados reproducibles. |

Cada vista ofrece primero una explicación corta y deja filtros, tabla fuente y metodología disponibles para quien quiera profundizar. La versión inicial debe permitir elegir periodo y flujo, ver el resumen, revisar rankings por país/producto y descargar el resultado de la consulta como CSV. No cargar millones de registros al navegador.

## Fórmulas públicas

- Saldo: exportaciones menos importaciones, sólo para el mismo periodo, moneda, universo y desglose.
- Variación interanual: (valor del periodo / valor del mismo periodo del año anterior − 1) × 100. Si la base es cero, confidencial o ausente, mostrar “No calculable”.
- Participación: valor de la categoría / total comparable × 100. Si faltan categorías confidenciales, etiquetar el denominador como parcial.
- Cambio absoluto: valor actual − valor del mismo periodo anterior, usando la misma unidad y vintage.
- Cantidad: mostrar sólo dentro de una misma UMED; no agregar unidades distintas en una sola suma.

Las gráficas temporales deben comparar meses equivalentes o advertir cuando se usa mes contra mes. No llamar “tiempo real” a datos mensuales publicados con rezago.

## Estados y confidencialidad

Conservar por separado, como mínimo:

- **Disponible:** valor numérico consultable.
- **Confidencial:** valor protegido por el mecanismo estadístico de INEGI; nunca convertirlo a cero, excluirlo en silencio ni inferirlo a partir de totales.
- **Ausente/no publicado:** no hay observación para ese corte.
- **Preliminar/revisada/definitiva/ajustada/corregida:** estado de publicación/cifra que INEGI documenta para la serie o el conjunto.

La BCMM pública cubre cifras agregadas. No exponer registros microeconómicos, identificadores de informante ni intentos de reconstruir valores suprimidos.

## Contrato sugerido de respuesta

Cada resultado de serie o tabla debe devolver datos y contexto juntos:

- Metadatos: fuente, URL, identificador del conjunto, fecha de consulta, fecha de actualización, periodo de referencia, estatus, unidad, moneda, valoración, nivel de agregación, filtros, notas y checksum.
- Observaciones: periodo, medida, valor o estado confidencial/ausente, y códigos/etiquetas de las dimensiones seleccionadas.

No establecer endpoints finales hasta confirmar formato, estabilidad, licencia de reutilización, volumen y política de actualización de los archivos oficiales elegidos. El endpoint actual /api/trade_balance permanece para el agregado BIE; la futura API de consultas multidimensionales debe tener contrato separado, límites de rango, paginación y caché.

## Fuentes oficiales consultadas

- [BCMM — programa de información, tabulados, datos abiertos y APIs](https://www.inegi.org.mx/programas/comext/default.html)
- [Descripción del Cubo interactivo BCMM](https://www.inegi.org.mx/contenidos/programas/comext/doc/descripcion.pdf)
- [Descarga masiva BCMM y jerarquía TIGIE/NICO](https://www.inegi.org.mx/app/descarga/ficha.html?ag=0&f=csv&tit=83063)
- [Diccionario de datos BCMM 2025](https://www.inegi.org.mx/rnm/index.php/catalog/1082/data-dictionary/F40)
- [API del Banco de Indicadores](https://www.inegi.org.mx/servicios/api_indicadores.html)
