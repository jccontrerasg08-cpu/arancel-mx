# Documentación de `arancel-mx`

Esta guía organiza la documentación por objetivo. Empieza por la ruta que describa tu necesidad y evita tratar los archivos de ejemplo, la caché local o un visor de terceros como la fuente del dataset.

## Consumir un dataset verificado

| Si necesitas… | Lee… | Resultado |
|---|---|---|
| Instalar, descargar y validar una release | [Inicio rápido de consumo](consumer-quickstart.md) | Un dataset local verificado y listo para consulta. |
| Conocer cada comando, la caché y los formatos | [CLI de consumo](consumer-cli.md) | Uso correcto de `doctor`, `data`, `lookup`, `ficha` y `provenance`. |
| Integrar el paquete o la API en otro sistema | [Consumo externo](external-consumption.md) | Contratos de descarga, Python y HTTP GET-only. |
| Entender la jerarquía LIGIE/NICO | [Guía NICO y LIGIE](nico-ligie-guide.md) | Navegación HS2 → HS4 → HS6 → fracción → NICO. |

## Verificar procedencia y datos

| Si necesitas… | Lee… | Resultado |
|---|---|---|
| Entender la autoridad de cada fuente | [Roles de fuentes oficiales](official-source-roles.md) | Límites entre SNICE, Diputados, DOF y fuentes auxiliares. |
| Revisar URLs, reconciliación y no-op | [Fuentes y reconciliación](sources.md) | Modelo de confianza y gates de publicación. |
| Entender la promoción agresiva desde SNICE_DOCS | [Política de promoción SNICE_DOCS](source-promotion.md) | Criterios, procedencia, rollback y límites de la promoción. |
| Consultar tablas, tiempos y semántica de release | [Modelo de datos](data-model.md) | Significado de los registros y del `manifest.json`. |

## Mantener y publicar

| Si necesitas… | Lee… | Resultado |
|---|---|---|
| Ejecutar o depurar el pipeline diario | [Proceso de release](release-process.md) | Estados, transacción y recuperación. |
| Certificar permisos de producción sin alterar datos | [Certificación de producción](production-certification.md) | Runbook aislado para GitHub Releases e Issues. |
| Publicar el paquete Python | [Release del paquete](package-release.md) | Flujo PyPI/TestPyPI y contrato de publicación. |
| Configurar reglas de GitHub y seguridad | [Configuración de GitHub](operations/github-settings.md) | Protección de `main`, permisos y checks requeridos. |
| Integrar cambios paralelos | [Handoff de integración](integration-handoff.md) | Baseline, fronteras de archivos y secuencia de merge segura. |

## Contribuir

Los cambios que afecten fuentes, parsers, reconciliación o contratos de release deben incluir fixtures offline y pruebas de regresión. Empieza por [CONTRIBUTING.md](../CONTRIBUTING.md), luego consulta [SECURITY.md](../SECURITY.md) para reportes privados y [CODE_OF_CONDUCT.md](../CODE_OF_CONDUCT.md) para la colaboración.

> `arancel-mx` es una herramienta de datos técnicos, no asesoría legal. Las decisiones de clasificación o cumplimiento deben contrastarse con las publicaciones oficiales aplicables y profesionales calificados.

[Español](../README.md) · [English](../README.en.md) · [Última release](https://github.com/jccontrerasg08-cpu/arancel-mx/releases/latest)
