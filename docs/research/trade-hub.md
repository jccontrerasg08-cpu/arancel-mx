# Hub de comercio exterior mexicano

> La página pública [Comercio exterior](https://arancel-mx.vercel.app/trade-context) conecta herramientas del proyecto, rutas educativas, cifras de INEGI y fuentes oficiales. Este documento explica cómo recorrerla y qué significa cada fuente.

## Qué cubre el hub

**arancel-mx** funciona como una puerta de entrada para investigar el comercio exterior mexicano, mientras conserva sus datos arancelarios verificables como un componente delimitado. La navegación distingue entre:

| Capa | Qué resuelve | Herramientas o fuentes |
|---|---|---|
| Aprender conceptos | Entender importación, exportación, clasificación, arancel, origen, regulación, despacho y balanza comercial. | [Guía para empezar](https://arancel-mx.vercel.app/learn), glosario y mapa de fuentes. |
| Consultar tarifa | Encontrar capítulos, partidas, fracciones y NICO de la release, con jerarquía, vigencia y evidencia disponible. | [Explorador](https://arancel-mx.vercel.app/app), [capítulos](https://arancel-mx.vercel.app/chapters), releases verificables. |
| Investigar una operación | Organizar preguntas sobre costos, documentos, origen y medidas que deben confirmarse. | [Mesa de comercio exterior](https://arancel-mx.vercel.app/trade), RGCE/SAT, SNICE, ANAM y VUCEM. |
| Leer estadística | Estudiar flujos agregados por periodo, producto o socio donde la fuente publique el desglose. | INEGI/BCMM, API de Indicadores y tabulados oficiales. |
| Comprobar cambios | Seguir decretos y acuerdos que modifican la TIGIE u otros instrumentos. | DOF, [registro de cambios](https://arancel-mx.vercel.app/changes), fuente oficial enlazada. |

Una estadística de exportaciones no es una tasa arancelaria. Una fracción no basta para determinar permisos, origen, contribuciones ni despacho. Las rutas del hub dirigen cada pregunta a la fuente y el nivel de evidencia apropiados.

## Ruta de aprendizaje sugerida

1. **Conceptos básicos:** diferencia entre importación y exportación; qué representa la balanza; qué mide una estadística de mercancías.
2. **Nomenclatura:** Sistema Armonizado (HS) a seis dígitos, fracción mexicana a ocho dígitos y NICO a diez dígitos; lectura de secciones, capítulos, partidas y notas.
3. **Medidas aplicables:** IGI/IGE, preferencias por tratado, permisos, cupos, NOM y otras regulaciones. Cada una debe verificarse en el acuerdo, decreto o portal oficial vigente.
4. **Operación:** valor, régimen, contribuciones, documentos, despacho y logística. La mesa ayuda a ordenar preguntas, no transmite declaraciones ni decide obligaciones.
5. **Análisis:** leer cifras con periodo, unidad, cobertura, estado estadístico y metodología; luego formular comparaciones reproducibles.

## Mapa de fuentes y su función

| Pregunta | Fuente primaria o portal de consulta | Uso y límite |
|---|---|---|
| ¿Qué fracción, NICO y tasa están publicados? | [LIGIE/TIGIE y NICO — SNICE](https://www.snice.gob.mx/cs/avi/snice/ligie.info22.html), DOF y la release arancelaria de arancel-mx. | La búsqueda y el código propuesto no constituyen clasificación legal definitiva. |
| ¿Qué pasó con las exportaciones e importaciones de México? | [Balanza Comercial de Mercancías de México — INEGI](https://www.inegi.org.mx/programas/comext/default.html), [tema Balanza](https://www.inegi.org.mx/temas/balanza/). | Estadística oficial agregada; revisar metodología, periodo, unidad y estatus de revisión. |
| ¿Cómo obtengo series programáticamente? | [API del Banco de Indicadores — INEGI](https://www.inegi.org.mx/servicios/api_indicadores.html). | Requiere token y clave de indicador. La API de Indicadores no debe suponerse equivalente a todas las tablas desagregadas de BCMM. |
| ¿Qué arancel preferencial o regla de origen consultar? | [Tratados y acuerdos — Secretaría de Economía](https://www.gob.mx/se/acciones-y-programas/comercio-exterior-paises-con-tratados-y-acuerdos-firmados-con-mexico), textos oficiales del tratado y SNICE. | Una preferencia depende del tratado, producto, origen y evidencia; no se deduce sólo por país. |
| ¿Qué permiso, cupo o NOM aplica? | [Medidas no arancelarias — SNICE](https://www.snice.gob.mx/cs/avi/snice/rrnas.html), acuerdo publicado en DOF y autoridad sectorial competente. | La lista orienta la consulta; la aplicabilidad requiere revisar fracción, régimen, fecha, país y producto. |
| ¿Cómo se realiza un trámite o despacho? | [RGCE — SAT](https://www.sat.gob.mx/minisitio/NormatividadRMFyRGCE/), [MOA — ANAM](https://www.anam.gob.mx/manual-de-operacion-aduanera-moa/) y [VUCEM](https://www.ventanillaunica.gob.mx/vucem/index.html). | Los actos y expedientes transaccionales ocurren en plataformas de la autoridad. No solicitar credenciales en el hub. |
| ¿Dónde revisar la vigencia de un instrumento? | [Diario Oficial de la Federación](https://www.dof.gob.mx/) y portal de la autoridad emisora. | La fecha de consulta y la versión del instrumento deben quedar visibles. |
| ¿Qué programas de fomento existen? | [IMMEX, PROSEC y otros programas — SNICE](https://www.snice.gob.mx/cs/avi/snice/programasdefom.immex.html). | Elegibilidad y obligaciones requieren revisar las reglas de cada programa y la situación del solicitante. |

El [mapa de cobertura oficial existente](external-trade-coverage-map.md) y el [catálogo de fuentes estructurado](external-trade-source-catalog.json) documentan con mayor detalle fuentes jurídicas y límites por categoría. No se deben duplicar estos catálogos en el dataset arancelario: son referencias de navegación, no registros LIGIE/NICO.

## Cifras interactivas: fuentes y dimensiones

No conviene forzar todos los gráficos dentro de una sola llamada API. El proyecto debe presentar dos productos estadísticos con contratos distintos:

| Fuente | Uso | Qué permite | Acceso |
|---|---|---|---|
| BIE-BISE · API de Indicadores | Cifras nacionales agregadas de exportaciones, importaciones y saldo. | Serie mensual para resumen, tendencias y comparaciones de tiempo. | API con token; la integración actual usa los indicadores 33860, 33861 y 33229. |
| BCMM · Datos Abiertos mensuales | Análisis desglosado según cada conjunto publicado. | Periodo, flujo, país, mercancía y, en conjuntos específicos, modo de transporte por aduana/capítulo. | Descarga pública de archivos; requiere procesamiento antes de servir gráficas. |
| BCMM · Cubo mensual | Consultas multidimensionales de comercio de mercancías. | Fracción/NICO, país, cantidad, valor y otras dimensiones que incluya el corte. | Consulta interactiva y exportación; comprobar la disponibilidad exacta de cada dimensión. |

Los datos abiertos mensuales de BCMM tienen cobertura desde 2012 en los conjuntos publicados. La información agregada puede llegar a fracción de ocho dígitos y NICO de diez dígitos. Los registros confidenciales permanecen identificables como tales: no convertirlos en cero ni reconstruir el valor. La base anual 2025 documenta más de 27 millones de registros agregados, así que las consultas de detalle deben procesarse en servidor, no descargarse enteras al navegador.

El modelo de campos, gráficos y fórmulas queda en [Contrato analítico de INEGI](inegi-analytics-contract.md) y [Catálogo de datos legible por máquina](inegi-analytics-catalog.json).

## Datos de INEGI en arancel-mx

El proyecto ya tiene una conexión viva para tres series mensuales del Banco de Información Económica (BIE-BISE):

| ID documentado en el proyecto | Serie | Unidad indicada por INEGI |
|---|---|---|
| **33860** | Exportaciones totales FOB | Millones de dólares |
| **33861** | Importaciones totales FOB | Millones de dólares |
| **33229** | Saldo FOB | Millones de dólares |

El flujo actual obtiene el JSON desde la API de Indicadores, calcula años completos y acumulados comparables, muestra la fecha de consulta y mantiene un snapshot de respaldo. El token se guarda del lado servidor en INEGI_TOKEN; no debe exponerse en React, HTML, logs públicos o URLs compartidas. El código de integración está en scripts/trade-balance-lib.mjs, scripts/build-trade-balance.mjs y api/trade_balance.py; la experiencia aparece en /trade-context.

Antes de ampliar el tablero a cifras por producto, país, entidad, modo de transporte o fracción:

1. Confirmar si el desglose está publicado por INEGI y en qué producto estadístico/API, no inferirlo de los tres indicadores agregados anteriores.
2. Registrar para cada serie su identificador, nombre oficial, unidad, cobertura, frecuencia, fecha de actualización, estatus (preliminar, revisada, definitiva, ajustada o corregida) y notas.
3. Comparar una muestra de respuesta API con el tabulado o descarga oficial de la misma fecha; documentar cualquier diferencia de revisión, conversión o agregación.
4. Conservar fuente, fecha de extracción y un snapshot reproducible; no sobrescribir silenciosamente la historia cuando INEGI revise cifras.
5. Presentar valores ausentes y fallas de API como tales, sin rellenarlos con cero ni mantener una cifra antigua sin mostrar su fecha.
6. Si el token está configurado en despliegue, consultar desde una función del servidor. No colocarlo en variables públicas como VITE_* o NEXT_PUBLIC_*.

La documentación oficial del API indica que las consultas requieren un token y un ID de indicador, y que las respuestas incluyen observaciones, unidad, notas, fuente, fecha de actualización y geografía. La disponibilidad de la API no garantiza que un cruce de producto × socio × fracción exista en ese servicio; las publicaciones de BCMM y sus descargas siguen siendo el punto de validación.

## Siguiente expansión de datos

- **Primero:** completar fichas metodológicas y etiquetas visibles para las series agregadas existentes, incluyendo estado estadístico y hora/fecha de última consulta.
- **Después:** construir un catálogo versionado de indicadores INEGI verificados por pregunta, con pruebas de conciliación contra los tabulados oficiales.
- **Luego:** explorar estadísticas de producto y socio disponibles en BCMM/INEGI y fuentes complementarias oficiales, manteniendo separado cada esquema y unidad.
- **Más adelante:** agregar filtros y visualizaciones comparables, descarga de datos y consultas reproducibles con su fuente, release o fecha de extracción.

No anunciar “tiempo real” si la serie se publica mensual o tiene rezago. “Consulta directa a la API” describe el transporte; “última cifra publicada” describe la actualidad del dato.

## Criterio de confianza

Cada cifra y referencia debe responder claramente: **quién la publicó, qué mide, para qué periodo, en qué unidad, con qué estatus y cuándo fue consultada**. El hub facilita aprender y navegar. La fuente primaria conserva la autoridad sobre tasas, requisitos, trámites y cifras oficiales.
