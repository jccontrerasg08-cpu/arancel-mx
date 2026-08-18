# Handoff de integración

> **Baseline revisada:** `fb727ac87e451e3835afad315af29925452e7fc8`, después de PR #132 (`feat: centralize verified data hub on Vercel`). Antes de terminar cualquier rama, compara de nuevo contra `origin/main`.

Esta guía mantiene integrables los cambios paralelos sin reintroducir acoplamientos que ya se eliminaron. Cada pull request debe respetar las fronteras actuales entre publicación oficial, capa operacional, hub público, API reusable y paquete Python.

## Fronteras que deben preservarse

| Área | Contrato vigente | Archivos con mayor riesgo de solapamiento |
|---|---|---|
| Hub público | `https://arancel-mx.vercel.app` sirve `website/`, mantiene rutas SPA, búsqueda arancelaria y metadata de confianza. | `website/`, `vercel.json`, `tests/test_public_site.py` |
| Capa operational de Vercel | `/v1/meta` y `/v1/search` se resuelven en funciones read-only respaldadas por Neon; la sincronización operacional parte de releases verificadas. | `api/operational.py`, `api/sync_operational.py`, `src/arancel_mx/operational/`, tests de `operations/` |
| FastAPI reusable | El runtime FastAPI sigue siendo desplegable por separado. Vercel presenta bajo el mismo dominio las rutas restantes mediante **proxy** hacia `arancel-mx.fastapicloud.dev`. | `src/arancel_mx/api/`, `docs/external-consumption.md`, rutas proxy en `vercel.json` |
| Paquete y dependencias | Las actualizaciones coordinan `pyproject.toml`, `requirements/` y pruebas de instalación/distribución. | `pyproject.toml`, `requirements/`, `tests/package*`, workflows de publicación |
| Releases y fuentes | La release verificada sigue siendo la fuente de verdad. El pipeline conserva snapshots, reconciliación, manifest e identidad inmutable. | `src/arancel_mx/sources/`, `src/arancel_mx/release/`, `tests/pipeline/`, `tests/sources/` |
| CI | Los checks protegidos deben seguir cubriendo Python, runtime, análisis y publicación. | `.github/workflows/`, `tests/test_workflow_hardening.py` |

## Qué cambió con #132

La separación anterior “sitio estático por un lado, toda la API por otro” ya no describe la superficie pública completa. Ahora el hub usa un modelo híbrido y deliberado:

```text
release verificada
      ↓
sync operacional idempotente
      ↓
Neon
      ↓
Vercel: /v1/meta + /v1/search

Vercel: /v1/* restante + /docs + /readyz
      ↓ proxy
FastAPI reusable
```

Esto **no** convierte Neon en la fuente canónica del dataset y **no** mueve el pipeline legal/de publicación a Vercel. La capa operational es una proyección read-only sincronizada desde releases certificadas. La identidad reproducible sigue viviendo en la release, manifest, hashes y fuentes capturadas.

## Secuencia mínima para una rama paralela

1. Parte de `main` actualizado y registra el SHA base.
2. Conserva el cambio más pequeño que respete la frontera del área.
3. Ejecuta primero las pruebas específicas de la zona afectada.
4. Antes del PR, compara otra vez contra `main` y revisa conflictos de archivos, no sólo conflictos de Git.
5. Deja los checks completos y el preview de Vercel como gate de integración.
6. Usa squash merge, que es el método permitido por la configuración actual del repositorio.

Cuando una rama toca el hub, confirma raíz y ruta directa, conserva `hub-search.js`/`hub-search.css` si no estás modificando búsqueda y verifica que `/v1/meta` siga resolviendo a la función operational. Las rutas generales `/v1/:path*`, `/docs` y `/readyz` deben conservar el proxy FastAPI mientras esa arquitectura siga vigente.

Cuando una rama toca dependencias o certificación del paquete, revísala después de las ramas de producto/sitio que también modifiquen `pyproject.toml`, `requirements/` o documentación raíz. Esto reduce conflictos y hace que la certificación pruebe el estado final.

## Presentación y branding

Los assets visuales y README pueden evolucionar sin tocar comportamiento de producción. La frontera segura actual es:

- `docs/assets/arancel-mx-*.svg` para GitHub, README, documentación y presentaciones;
- `website/assets/arancel-mx-mark.svg`, `arancel-mx-logo.svg` y `site-brand.css` para identidad del hub;
- no editar a mano `website/assets/index-*.js` ni `website/assets/index-*.css`, porque son bundles generados;
- tratar `website/index.html` con especial cuidado: contiene runtime generado inline, por lo que cambios de metadata deben venir de una regeneración reproducible o de una edición que pueda verificarse byte a byte.

## Estado de trabajos pendientes al crear esta guía

| Candidato | Área | Acción recomendada |
|---|---|---|
| PR #124, `httpx2` | Dependencias | Dejar que Dependabot termine rebase; no mezclar cambios manuales de branding en esa rama |
| PR #125, `setuptools` | Dependencias/build | Igual: rebase y checks completos después de cambios activos que toquen packaging |
| `fix/windows-helper-env-path-034` | Publicación/Windows | Comparar su único cambio útil contra `main` actual antes de rescatarlo; no mergear la rama obsoleta completa |

Esta guía no sustituye `CONTRIBUTING.md`, las protecciones de `main` ni los checks requeridos. Es el mapa de integración para evitar que un cambio correcto localmente revierta una decisión arquitectónica posterior.