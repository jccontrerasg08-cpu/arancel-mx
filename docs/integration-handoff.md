# Handoff de integración

> **Baseline revisada:** `90840779e752ac7ef257923edda95f188d4d35ac`, después de PR #141 (`fix: build Vercel driver with Python 3.13`). Antes de terminar cualquier rama, compara de nuevo contra `origin/main`.

Esta guía mantiene integrables los cambios paralelos sin reintroducir acoplamientos que ya se eliminaron. Cada pull request debe respetar las fronteras actuales entre publicación oficial, capa operacional, hub público, API reusable y paquete Python.

## Fronteras que deben preservarse

| Área | Contrato vigente | Archivos con mayor riesgo de solapamiento |
|---|---|---|
| Hub público | `https://arancel-mx.vercel.app` sirve `website/`, mantiene rutas SPA, búsqueda arancelaria y metadata de confianza. | `website/`, `vercel.json`, `tests/test_public_site.py` |
| Capa operational de Vercel | `/v1/meta`, `/v1/search` y `/readyz` se resuelven en funciones read-only respaldadas por Neon; la sincronización operacional parte de releases verificadas. | `api/operational.py`, `api/sync_operational.py`, `src/arancel_mx/operational/`, tests de `operations/` |
| FastAPI reusable | El runtime FastAPI sigue siendo desplegable por separado. Vercel presenta bajo el mismo dominio las rutas restantes mediante **proxy** hacia `arancel-mx.fastapicloud.dev`. | `src/arancel_mx/api/`, `docs/external-consumption.md`, rutas proxy en `vercel.json` |
| Paquete y dependencias | Las actualizaciones coordinan `pyproject.toml`, `requirements/` y pruebas de instalación/distribución. | `pyproject.toml`, `requirements/`, `tests/package*`, workflows de publicación |
| Releases y fuentes | La release verificada sigue siendo la fuente de verdad. El pipeline conserva snapshots, reconciliación, manifest e identidad inmutable. | `src/arancel_mx/sources/`, `src/arancel_mx/release/`, `tests/pipeline/`, `tests/sources/` |
| CI | Los checks protegidos deben seguir cubriendo Python, runtime, análisis y publicación. | `.github/workflows/`, `tests/test_workflow_hardening.py` |

## Arquitectura del Central Hub

La separación anterior “sitio estático por un lado, toda la API por otro” ya no describe la superficie pública completa. El hub usa un modelo híbrido y deliberado:

```text
release verificada
      ↓
sync operacional idempotente
      ↓
Neon
      ↓
Vercel: /v1/meta + /v1/search + /readyz

Vercel: /v1/* restante + /docs
      ↓ proxy
FastAPI reusable
```

Esto **no** convierte Neon en la fuente canónica del dataset y **no** mueve el pipeline legal/de publicación a Vercel. La capa operational es una proyección read-only sincronizada desde releases certificadas. La identidad reproducible sigue viviendo en la release, manifest, hashes y fuentes capturadas.

### Contrato operativo de configuración

El Central Hub mantiene separadas la versión de la aplicación, la versión del paquete y la identidad inmutable del dataset. La versión de dataset visible en el sitio y la publicada por `/v1/meta` deben provenir de la misma release operativa promovida; si cualquiera no está disponible, el despliegue debe considerarse incompleto y no una versión alternativa válida.

Para la función operativa de Vercel, `ARANCEL_MX_DATABASE_URL` es el nombre canónico de configuración. Cuando la base proviene de la integración administrada de Neon, la función admite `ARANCEL_MX_DATABASE_DATABASE_URL` como compatibilidad controlada; no se deben copiar los valores de la integración a un segundo secreto sólo para satisfacer el código. `CRON_SECRET` es un secreto sensible de **Production** y Vercel lo transmite como token Bearer al cron definido en `vercel.json`. No se registra, documenta ni reutiliza fuera de ese flujo.

Vercel construye `psycopg[binary]` en `api/_vendor` mediante el `buildCommand` y lo incluye exclusivamente en `/api/operational` y `/api/sync_operational`. Los handlers cargan ese directorio antes de importar el driver; la librería pública conserva sus dependencias base y el extra `operational` para instalaciones que sí necesiten acceso directo a PostgreSQL. No se debe duplicar el driver en `requirements.txt` ni hacerlo una dependencia base sólo para satisfacer el bundle de Vercel.

Antes de limpiar variables en Vercel, identifica si son creadas por la integración administrada. Las variables de conexión derivadas de Neon no son código muerto aunque el Central Hub consuma sólo la URL principal; eliminarlas puede romper la integración o despliegues posteriores. Las únicas eliminaciones permitidas son aliases manuales no referenciados y validados después de un despliegue satisfactorio.

## Secuencia mínima para una rama paralela

1. Parte de `main` actualizado y registra el SHA base.
2. Conserva el cambio más pequeño que respete la frontera del área.
3. Ejecuta primero las pruebas específicas de la zona afectada.
4. Antes del PR, compara otra vez contra `main` y revisa conflictos de archivos, no sólo conflictos de Git.
5. Deja los checks completos y el preview de Vercel como gate de integración.
6. Usa squash merge, que es el método permitido por la configuración actual del repositorio.

Cuando una rama toca el hub, confirma raíz y ruta directa, conserva `hub-search.js`/`hub-search.css` si no estás modificando búsqueda y verifica que `/v1/meta` y `/readyz` sigan resolviendo a la función operational. Las rutas generales `/v1/:path*` y `/docs` deben conservar el proxy FastAPI mientras esa arquitectura siga vigente.

Cuando una rama toca dependencias o certificación del paquete, revísala después de las ramas de producto/sitio que también modifiquen `pyproject.toml`, `requirements/` o documentación raíz. Esto reduce conflictos y hace que la certificación pruebe el estado final.

## Presentación y branding

Los assets visuales y README pueden evolucionar sin tocar comportamiento de producción. La frontera segura actual es:

- `docs/assets/arancel-mx-*.svg` para GitHub, README, documentación y presentaciones;
- `website/assets/arancel-mx-mark.svg`, `arancel-mx-logo.svg` y `site-brand.css` para identidad del hub;
- no editar a mano `website/assets/index-*.js` ni `website/assets/index-*.css`, porque son bundles generados;
- `website/index.html` contiene runtime generado inline: cualquier cambio de metadata debe venir **únicamente de una regeneración reproducible del origen que controla ese archivo**, nunca de un parche manual post-build.

PR #134 eliminó el runtime/debug collector de Manus del sitio público. Cualquier regeneración futura debe conservar esa limpieza y los tests de `website/index.html` que la protegen.

## Estado de trabajos pendientes al crear esta guía

| Candidato | Área | Acción recomendada |
|---|---|---|
| PR #124, `httpx2` | Dependencias | Dejar que Dependabot termine rebase; no mezclar cambios manuales de branding en esa rama |
| PR #125, `setuptools` | Dependencias/build | Igual: rebase y checks completos después de cambios activos que toquen packaging |
| `fix/windows-helper-env-path-034` | Publicación/Windows | Comparar su único cambio útil contra `main` actual antes de rescatarlo; no mergear la rama obsoleta completa |

Esta guía no sustituye `CONTRIBUTING.md`, las protecciones de `main` ni los checks requeridos. Es el mapa de integración para evitar que un cambio correcto localmente revierta una decisión arquitectónica posterior.