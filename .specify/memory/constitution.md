# Constitución de arancel-mx

Reglas que toda especificación, plan, lista de tareas e implementación hecha con Spec Kit debe respetar. Resumen las normas vigentes del repositorio; ante cualquier diferencia manda el documento canónico enlazado.

## Principios

### I. Una sola fuente de verdad, publicada con evidencia

Ninguna superficie (sitio, API estática, CLI, paquete) muestra datos arancelarios que no estén en una release verificada `data-YYYY.MM.DD`. Cada dato conserva su procedencia: fuente oficial, URL, SHA-256 y fecha de captura. Las fuentes oficiales (DOF, Cámara de Diputados, SNICE, SAT) son la autoridad; un portal de terceros nunca lo es.

Canónico: [Arquitectura §8](../../docs/architecture.md), [Fuentes y reconciliación](../../docs/sources.md).

### II. Fail-closed (NO NEGOCIABLE)

Una discrepancia legal, un parser ambiguo o una verificación fallida bloquean la publicación. Nunca se corrigen datos en silencio. Una corrección a lo que publica SNICE sólo entra por un registro empaquetado (`description_corrections.json`, `rate_corrections.json`) que cita el PDF oficial con su SHA-256, se aplica sólo mientras SNICE publique exactamente el valor registrado y queda reportada en el manifest. Lo que no se puede fechar o verificar se deja vacío, no se inventa.

Canónico: [Modelo de datos](../../docs/data-model.md), [Proceso de release](../../docs/release-process.md).

### III. Releases inmutables y contratos estables

Un tag de release publicado no se reescribe. El formato `data-YYYY.MM.DD`, el esquema del dataset, la API estática `/data/v1`, el CLI y el paquete son contratos públicos: un cambio incompatible exige versión, consumidor identificado, pruebas y plan de transición. Una base publicada debe abrir en la versión mínima de DuckDB que declara el paquete.

Canónico: [Política de compatibilidad](../../docs/compatibility.md).

### IV. Recuperar, no clasificar

`search` y `suggest` recuperan evidencia. arancel-mx no clasifica mercancías, no determina contribuciones, origen ni permisos y no da asesoría legal. Toda interfaz que pueda leerse como consejo lo aclara.

Canónico: [Arquitectura §8](../../docs/architecture.md), [Guía de estilo](../../docs/documentation-style.md).

### V. Cambio mínimo, probado y reversible

Se reutiliza lo que existe antes de escribir algo nuevo; no se agregan abstracciones ni dependencias que nadie pidió (método Ponytail). Toda lógica no trivial llega con una prueba que falla antes del cambio y pasa después. Cada cambio declara alcance, verificación y forma de revertirlo, y nada se afirma como «desplegado» o «actualizado» sin una observación que lo respalde.

Canónico: [Política de desarrollo verificable](../../docs/governance/DEVELOPMENT_POLICY.md), [CONTRIBUTING.md](../../CONTRIBUTING.md).

## Restricciones

- **Sólo lectura hacia fuera:** ninguna superficie pública acepta escrituras ni pide credenciales.
- **Mínimo privilegio en CI:** permisos de escritura en un solo job cada uno, acciones fijadas por SHA, valores dinámicos por `env:`.
- **Sin secretos ni datos privados** en Git, fixtures, artefactos ni logs.
- **Stack:** Python 3.11 con `requirements/production-build.txt` fijado; frontend Vite + React compilado a `src/arancel_mx/api/static/site/`; datos en DuckDB.
- **Idioma:** documentación y textos de interfaz en español, siguiendo la [guía de estilo](../../docs/documentation-style.md); nombres de archivo en inglés `kebab-case`.

## Flujo de trabajo y calidad

- Las especificaciones van en `specs/NNN-nombre/` y se escriben en español.
- Antes de abrir un PR: `ruff check src tests scripts`, `mypy src/arancel_mx`, `python -m pytest -q` y, si cambia el frontend, `npm run build:frontend` con las pruebas de Playwright. CI repite estas puertas; un PR sólo se fusiona en verde.
- Un cambio transversal (API, esquema, release, seguridad, automatización) lleva una decisión en `docs/decisions/` con la [plantilla](../../docs/decisions/0000-template.md).
- `/speckit-plan` y `/speckit-analyze` deben comprobar cada principio de esta constitución y justificar por escrito cualquier excepción.

## Gobierno

Esta constitución no sustituye a la [Política de desarrollo verificable](../../docs/governance/DEVELOPMENT_POLICY.md); cuando difieran, se aplica la regla más protectora y la diferencia se resuelve con una decisión. Una enmienda se hace por pull request, sube la versión (MAYOR si elimina o redefine un principio, MENOR si agrega uno, PARCHE si aclara redacción) y actualiza las fechas.

**Versión**: 1.0.0 | **Ratificada**: 2026-11-06 | **Última enmienda**: 2026-11-06
