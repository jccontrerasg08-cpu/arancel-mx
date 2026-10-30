# Documentación de `arancel-mx`

La portada del repositorio explica **qué es** `arancel-mx` y cómo empezar. Este índice es la entrada canónica al detalle técnico: elige la ruta según lo que necesitas hacer.

**[Hub público](https://arancel-mx.vercel.app/)** · **[Mesa de comercio exterior](https://arancel-mx.vercel.app/trade)** · **[Centro de documentación](https://arancel-mx.vercel.app/documentation)** · **[Metadata del dataset](https://arancel-mx.vercel.app/data/v1/meta.json)** · **[Última release](https://github.com/jccontrerasg08-cpu/arancel-mx/releases/latest)** · **[README](../README.md)**

## Usar

| Necesidad | Lee / abre | Resultado |
|---|---|---|
| Buscar una fracción, HS o NICO sin instalar nada | [Hub público](https://arancel-mx.vercel.app/) | Búsqueda web sobre la release verificada activa. |
| Construir un escenario de costos, origen, RRNA o despacho | [Mesa de comercio exterior](https://arancel-mx.vercel.app/trade) | Orientación con entradas declaradas, resultados aritméticos y fuentes oficiales; no determina obligaciones ni transmite trámites. |
| Instalar, descargar y validar una release | [Inicio rápido](consumer-quickstart.md) | Dataset local verificado y listo para consultar. |
| Usar todos los comandos, formatos, caché y modo offline | [CLI de consumo](consumer-cli.md) | Referencia de `doctor`, `data`, `lookup`, `search`, `ficha`, `provenance` y más. |
| Entender HS2 → HS4 → HS6 → fracción → NICO | [Guía NICO y LIGIE](nico-ligie-guide.md) | Jerarquía y navegación de códigos mexicanos. |

## Integrar

| Necesidad | Lee / abre | Resultado |
|---|---|---|
| Integrar DuckDB/CSV/JSON, Python o HTTP | [Consumo externo](external-consumption.md) | Contratos de archivos, `Dataset` y API estática GET-only/read-only. |
| Evolucionar biblioteca, CLI o HTTP sin romper consumidores | [Política de compatibilidad](compatibility.md) | Soporte certificado, cambios aditivos y deprecaciones anunciadas. |
| Migrar desde la API dinámica `/v1` alojada | [Retiro de `/v1`](operations/v1-sunset.md) | Equivalencias con `/data/v1` y calendario de retiro (2027-01-31). |
| Explorar rutas, límites y contratos públicos | [Centro de documentación](https://arancel-mx.vercel.app/documentation) | Rutas GET-only, documentación mantenida y límites de integración. |
| Identificar la release que sirve el hub | [`/data/v1/meta.json`](https://arancel-mx.vercel.app/data/v1/meta.json) | Identidad del dataset servido por la API estática. |
| Entender tablas, vigencia y manifest | [Modelo de datos](data-model.md) | Semántica del DuckDB y de una release verificable. |

## Entender y verificar

| Necesidad | Lee | Resultado |
|---|---|---|
| Saber qué autoridad cumple cada fuente | [Roles de fuentes oficiales](official-source-roles.md) | Límites entre Diputados, DOF, SNICE y fuentes auxiliares. |
| Entender captura, reconciliación y no-op | [Fuentes y reconciliación](sources.md) | Cadena de confianza y gates de publicación. |
| Entender cómo se evalúan candidatos SNICE_DOCS | [Política de promoción](source-promotion.md) | Allowlist, procedencia, rollback y límites. |
| Revisar el mapa especializado del MOA | [Mapa ANAM / MOA](research/anam-moa-source-map.md) | Índice de navegación y procedencia hacia fuentes oficiales ANAM. |
| Revisar las fuentes del glosario y la normatividad ANAM | [Mapa de normatividad y glosario ANAM](research/anam-normativity-glossary-source-map.md) | Recursos normativos 2022 y glosario oficial con fechas de consulta. |
| Ver cada instrumento del DOF que creó o modificó la LIGIE | [Inventario de instrumentos](research/ligie-instrument-inventory.md) | Decretos, acuerdos NICO, fechas y verificación contra la release. |
| Ubicar la fuente oficial para una categoría de comercio exterior | [Mapa de cobertura de comercio exterior](research/external-trade-coverage-map.md) | Cobertura LIGIE/NICO y referencias oficiales para leyes, RGCE, tratados, RRNA, VUCEM, padrones y programas. |
| Auditar variables, fórmulas y límites de la mesa | [Plan de fuentes de la mesa](research/trade-assistant-source-plan.md) | Fuentes primarias confirmadas y separación entre datos declarados, resultados orientativos y determinaciones de autoridad. |

## Mantener y contribuir

| Necesidad | Lee | Resultado |
|---|---|---|
| Ejecutar o depurar el pipeline diario | [Proceso de release](release-process.md) | Estados, publicación, no-op y recuperación. |
| Certificar permisos de producción | [Certificación de producción](production-certification.md) | Runbook aislado de write-boundaries y rollback. |
| Publicar el paquete Python | [Release del paquete](package-release.md) | Flujo TestPyPI/PyPI y gates de publicación. |
| Configurar GitHub y checks | [Configuración de GitHub](operations/github-settings.md) | Protección de `main`, permisos y required checks. |
| Entender cómo encajan todas las piezas | [Arquitectura](architecture.md) | Vista general, flujo de publicación, módulos, scripts, workflows e invariantes. |
| Registrar o consultar una decisión de arquitectura | [Decisiones](decisions/) | Contexto, alternativas y compatibilidad de cada cambio de rumbo. |
| Escribir o revisar documentación | [Guía de estilo](documentation-style.md) | Idioma, estructura y documentos canónicos. |
| Mantener o compilar la interfaz pública | [Fuente mantenible del frontend](frontend-source.md) | Rutas React, contenido declarativo, build Vite y copia al directorio publicado `src/arancel_mx/api/static/site/`. |
| Aplicar las reglas comunes del ecosistema | [Política de desarrollo verificable](governance/DEVELOPMENT_POLICY.md) | Evidencia, contratos, seguridad, excepciones y recuperación para Central Hub y RFA. |
| Enviar cambios | [CONTRIBUTING.md](../CONTRIBUTING.md) | Flujo y criterios de contribución. |
| Reportar un problema de seguridad | [SECURITY.md](../SECURITY.md) | Canal de reporte privado. |

## Proyecto y presentación

| Necesidad | Lee | Resultado |
|---|---|---|
| Entender por qué existe, qué posee y qué queda fuera | [Visión del proyecto](project-overview.md) | Arquitectura conceptual y fronteras de producto. |
| Usar logos, paleta, copy o storytelling | [Marca y presentación](brand.md) | Assets canónicos y reglas de comunicación. |
| Aplicar imágenes, banderas o referencias institucionales | [Atlas visual](visual-atlas.md) | Taxonomía por capítulo, fuentes, atribución y límites de marca. |
| Ver hacia dónde va el modelo de datos | [Programa de profundidad](depth-program.md) | Gates, workstreams y registro de decisiones del propietario. |
| Ver cambios relevantes | [CHANGELOG.md](../CHANGELOG.md) | Historial de versiones y entregas. |
| Revisar reglas de comunidad | [CODE_OF_CONDUCT.md](../CODE_OF_CONDUCT.md) · [TERMS.md](../TERMS.md) | Colaboración y términos del proyecto. |

> `arancel-mx` es una herramienta técnica de datos. No clasifica mercancías ni constituye asesoría legal. Para decisiones regulatorias o aduaneras deben consultarse las publicaciones oficiales aplicables y, cuando corresponda, profesionales especializados.

**[Hub](https://arancel-mx.vercel.app/)** · **[Documentación](https://arancel-mx.vercel.app/documentation)** · **[Español](../README.md)** · **[English](../README.en.md)** · **[Última release](https://github.com/jccontrerasg08-cpu/arancel-mx/releases/latest)**
