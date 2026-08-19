# Documentación de `arancel-mx`

La portada del repositorio explica **qué es** `arancel-mx` y cómo empezar. Este índice es la entrada canónica al detalle técnico: elige la ruta según lo que necesitas hacer.

**[Hub público](https://arancel-mx.vercel.app/)** · **[Mesa de comercio exterior](https://arancel-mx.vercel.app/trade)** · **[API / OpenAPI](https://arancel-mx.vercel.app/docs)** · **[Metadata del dataset](https://arancel-mx.vercel.app/v1/meta)** · **[Última release](https://github.com/jccontrerasg08-cpu/arancel-mx/releases/latest)** · **[README](../README.md)**

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
| Integrar DuckDB/CSV/JSON, Python o HTTP | [Consumo externo](external-consumption.md) | Contratos de archivos, `Dataset` y API GET-only/read-only. |
| Explorar el contrato HTTP | [OpenAPI público](https://arancel-mx.vercel.app/docs) | Endpoints y esquemas bajo el mismo dominio del hub. |
| Identificar la release que sirve la capa pública | [`/v1/meta`](https://arancel-mx.vercel.app/v1/meta) | Identidad separada de API, paquete y dataset. |
| Entender tablas, vigencia y manifest | [Modelo de datos](data-model.md) | Semántica del DuckDB y de una release verificable. |

## Entender y verificar

| Necesidad | Lee | Resultado |
|---|---|---|
| Saber qué autoridad cumple cada fuente | [Roles de fuentes oficiales](official-source-roles.md) | Límites entre Diputados, DOF, SNICE y fuentes auxiliares. |
| Entender captura, reconciliación y no-op | [Fuentes y reconciliación](sources.md) | Cadena de confianza y gates de publicación. |
| Entender cómo se evalúan candidatos SNICE_DOCS | [Política de promoción](source-promotion.md) | Allowlist, procedencia, rollback y límites. |
| Revisar el mapa especializado del MOA | [Mapa ANAM / MOA](research/anam-moa-source-map.md) | Índice de navegación y procedencia hacia fuentes oficiales ANAM. |
| Ubicar la fuente oficial para una categoría de comercio exterior | [Mapa de cobertura de comercio exterior](research/external-trade-coverage-map.md) | Cobertura LIGIE/NICO y referencias oficiales para leyes, RGCE, tratados, RRNA, VUCEM, padrones y programas. |
| Auditar variables, fórmulas y límites de la mesa | [Plan de fuentes de la mesa](research/trade-assistant-source-plan.md) | Fuentes primarias confirmadas y separación entre datos declarados, resultados orientativos y determinaciones de autoridad. |

## Mantener y contribuir

| Necesidad | Lee | Resultado |
|---|---|---|
| Ejecutar o depurar el pipeline semanal | [Proceso de release](release-process.md) | Estados, publicación, no-op y recuperación. |
| Certificar permisos de producción | [Certificación de producción](production-certification.md) | Runbook aislado de write-boundaries y rollback. |
| Publicar el paquete Python | [Release del paquete](package-release.md) | Flujo TestPyPI/PyPI y gates de publicación. |
| Configurar GitHub y checks | [Configuración de GitHub](operations/github-settings.md) | Protección de `main`, permisos y required checks. |
| Integrar cambios paralelos sin revertir arquitectura | [Handoff de integración](integration-handoff.md) | Baseline actual y fronteras de alto riesgo. |
| Centralizar la capa pública en Vercel | [Centralización Vercel](vercel-centralization.md) | Cutover por etapas, identidad de release y retiro seguro de FastAPI. |
| Enviar cambios | [CONTRIBUTING.md](../CONTRIBUTING.md) | Flujo y criterios de contribución. |
| Reportar un problema de seguridad | [SECURITY.md](../SECURITY.md) | Canal de reporte privado. |

## Proyecto y presentación

| Necesidad | Lee | Resultado |
|---|---|---|
| Entender por qué existe, qué posee y qué queda fuera | [Visión del proyecto](project-overview.md) | Arquitectura conceptual y fronteras de producto. |
| Usar logos, paleta, copy o storytelling | [Marca y presentación](brand.md) | Assets canónicos y reglas de comunicación. |
| Ver cambios relevantes | [CHANGELOG.md](../CHANGELOG.md) | Historial de versiones y entregas. |
| Revisar reglas de comunidad | [CODE_OF_CONDUCT.md](../CODE_OF_CONDUCT.md) · [TERMS.md](../TERMS.md) | Colaboración y términos del proyecto. |

> `arancel-mx` es una herramienta técnica de datos. No clasifica mercancías ni constituye asesoría legal. Para decisiones regulatorias o aduaneras deben consultarse las publicaciones oficiales aplicables y, cuando corresponda, profesionales especializados.

**[Hub](https://arancel-mx.vercel.app/)** · **[API](https://arancel-mx.vercel.app/docs)** · **[Español](../README.md)** · **[English](../README.en.md)** · **[Última release](https://github.com/jccontrerasg08-cpu/arancel-mx/releases/latest)**
