# Handoff de integración

> **Baseline vigente:** `main` después de la integración del sitio público independiente y su corrección de rutas directas. Antes de modificar cualquier rama, actualiza contra `origin/main`.

Esta guía mantiene los cambios paralelos integrables sin convertir el repositorio en un sistema de coordinación complejo. El objetivo es que cada pull request represente un contrato de producto, datos o publicación comprobable y que no reintroduzca acoplamientos ya eliminados.

## Fronteras que deben preservarse

| Área | Contrato vigente | Archivos con mayor riesgo de solapamiento |
|---|---|---|
| Sitio público | `https://arancel-mx.vercel.app` se despliega estáticamente desde `website/`, con rutas SPA directas y guías enlazadas. | `website/`, `vercel.json`, `tests/test_public_site.py`, README. |
| FastAPI | Es una superficie reutilizable y desplegable por separado; Vercel no ejecuta su entrypoint. | `src/arancel_mx/api/`, `pyproject.toml`, `docs/external-consumption.md`. |
| Paquete y dependencias | Las actualizaciones coordinan `pyproject.toml`, archivos en `requirements/` y pruebas de instalación/distribución. | `pyproject.toml`, `requirements/`, `tests/package*`, workflows de publicación. |
| Releases y fuentes | El pipeline conserva snapshots, reconciliación, manifest e identidad inmutable de release. | `src/arancel_mx/sources/`, `src/arancel_mx/release/`, `tests/pipeline/`, `tests/sources/`. |
| CI | Los checks protegidos deben seguir cubriendo Python, Chromium, runtime, análisis y publicación. | `.github/workflows/`, `tests/test_workflow_hardening.py`. |

## Secuencia mínima para una rama paralela

Actualiza la rama con `origin/main` justo antes de abrir o terminar el pull request. Resuelve los conflictos en la rama de trabajo, no en `main`, y conserva el cambio más pequeño que respete el contrato listado arriba. Ejecuta las pruebas de la zona afectada localmente; el pull request debe esperar los checks protegidos completos antes de un merge squash.

Cuando una rama toca el sitio público, confirma tanto la raíz como una ruta directa, por ejemplo `/documentation`, con una solicitud GET o en Chrome. `vercel.json` usa `cleanUrls`, por lo que el fallback SPA debe reescribir `/(.*)` hacia `/`, no hacia `/index.html`. También confirma que `/v1/meta` no vuelva a ser una API coalojada en el sitio público.

Cuando una rama toca dependencias o certificación del paquete, revísala después de las ramas de producto y sitio si modifica `pyproject.toml`, `requirements/` o documentación raíz. Esto reduce conflictos y asegura que la validación de distribución se ejecute sobre el estado final.

## Estado de los trabajos pendientes

| Candidato | Área | Orden recomendado | Acción antes de merge |
|---|---|---|---|
| Actualizaciones de Dependabot | Dependencias de producción | Después de cualquier cambio activo a `pyproject.toml` o `requirements/`. | Rebase contra `main`, ejecutar checks completos y revisar el runtime FastAPI. |
| Corrección portable de certificación Windows | Publicación y documentación | Después del sitio público; toca documentación y `pyproject.toml`. | Rebase, resolver los cambios de README/documentación y volver a ejecutar las certificaciones de paquete. |

Esta guía no sustituye `CONTRIBUTING.md`, las protecciones de `main` ni los checks requeridos. Es un mapa de integración para que los cambios de los distintos agentes lleguen a esos controles con el menor conflicto posible.

## Contrato operativo de Central Hub

El Central Hub mantiene separadas la versión de la aplicación, la versión del paquete y la identidad inmutable del dataset. La versión de dataset visible en el sitio y la publicada por `/v1/meta` deben provenir de la misma release operativa promovida; si cualquiera no está disponible, el despliegue debe considerarse incompleto y no una versión alternativa válida.

Para la función operativa de Vercel, `ARANCEL_MX_DATABASE_URL` es el nombre canónico de configuración. Cuando la base proviene de la integración administrada de Neon, la función admite `ARANCEL_MX_DATABASE_DATABASE_URL` como compatibilidad controlada; no se deben copiar los valores de la integración a un segundo secreto sólo para satisfacer el código. `CRON_SECRET` es un secreto sensible de **Production** y Vercel lo transmite como token Bearer al cron definido en `vercel.json`. No se registra, documenta ni reutiliza fuera de ese flujo.

Antes de limpiar variables en Vercel, identifica si son creadas por la integración administrada. Las variables de conexión derivadas de Neon no son código muerto aunque el Central Hub consuma sólo la URL principal; eliminarlas puede romper la integración o despliegues posteriores. Las únicas eliminaciones permitidas son aliases manuales no referenciados y validados después de un despliegue satisfactorio.
