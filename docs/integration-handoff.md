# Handoff de integración

> **Baseline revisada:** `c1be4bf4e8da831ab7bd1da0667d794076cc16e2`, después de PR #139 (`fix: bundle Vercel operational driver in isolation`). Antes de terminar cualquier rama, compara de nuevo contra `origin/main`.

Esta guía evita que un cambio correcto de forma aislada revierta decisiones arquitectónicas posteriores. Cada PR debe preservar las fronteras entre publicación oficial, capa operacional, hub público, API reusable y paquete Python.

## Fronteras que deben preservarse

| Área | Contrato vigente | Archivos de alto riesgo |
|---|---|---|
| Hub público | `https://arancel-mx.vercel.app` sirve `website/`, búsqueda, metadata y rutas públicas bajo un solo dominio. | `website/`, `vercel.json`, `tests/test_public_site.py` |
| Capa operacional | `/v1/meta` y `/v1/search` son read-only, respaldados por Neon y sincronizados desde releases verificadas. | `api/operational.py`, `api/sync_operational.py`, `src/arancel_mx/operational/` |
| FastAPI reusable | El resto de `/v1/*`, `/docs` y `/readyz` se presenta en Vercel mediante proxy al runtime FastAPI. | `src/arancel_mx/api/`, `vercel.json`, `docs/external-consumption.md` |
| Runtime operacional de Vercel | `psycopg[binary]` se bundlea de forma aislada en `api/_vendor` y sólo se incluye en las dos funciones operativas. | `vercel.json`, `api/operational.py`, `api/sync_operational.py`, `.gitignore` |
| Paquete y dependencias | La librería pública conserva dependencias base y el extra `operational`; Vercel no debe convertir su driver aislado en dependencia base. | `pyproject.toml`, `requirements/`, packaging tests |
| Releases y fuentes | La release verificable sigue siendo la fuente de verdad. | `src/arancel_mx/sources/`, `src/arancel_mx/release/`, tests de pipeline/fuentes |
| CI | Los checks deben cubrir Python, runtime, browser, distribución y publicación. | `.github/workflows/`, tests de hardening |
| Presentación | README raíz es front door compacto; `docs/README.md` es navegación profunda. | `README*.md`, `docs/`, assets de marca |

## Arquitectura del Central Hub

```text
GitHub Release verificada
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

Neon no sustituye el dataset canónico y Vercel no mueve el pipeline legal/de publicación a la capa web. La identidad reproducible permanece en la release, manifest, hashes y fuentes capturadas.

## Contrato operativo de Vercel

La versión de dataset visible en el hub y la publicada por `/v1/meta` deben corresponder a la misma release promovida. Si esa identidad no está disponible o no puede validarse, el despliegue no debe presentar una versión alternativa como equivalente.

Configuración relevante:

- `ARANCEL_MX_DATABASE_URL` es el nombre canónico de la conexión operacional.
- `ARANCEL_MX_DATABASE_DATABASE_URL` se admite como compatibilidad controlada cuando la integración administrada de Neon genera ese nombre.
- `CRON_SECRET` es un secreto de Production enviado como Bearer token al cron operacional; no se registra ni reutiliza.
- Desde #139, `vercel.json` usa un `buildCommand` que instala `psycopg[binary]>=3.3.4` en `api/_vendor`.
- `api/operational.py` y `api/sync_operational.py` cargan `api/_vendor` antes de importar el driver y son las únicas funciones que incluyen ese directorio mediante `functions.includeFiles`.
- `api/_vendor/` permanece ignorado por Git. Es un artefacto de build, no código fuente versionado.
- `requirements.txt` ya no debe existir para este runtime: #139 eliminó el archivo para evitar que el driver operacional se convierta en dependencia global por accidente.
- La librería Python mantiene su extra `operational` para instalaciones que sí necesiten conectividad PostgreSQL fuera del bundle de Vercel.

No elimines variables creadas por la integración administrada de Neon sólo porque una de ellas no se lea directamente en el código. Antes de limpiar aliases, verifica su origen y realiza un despliegue satisfactorio con la configuración resultante.

## Secuencia mínima para una rama paralela

1. Parte del `main` actualizado y registra el SHA base.
2. Relee los archivos/contratos del área que tocarás.
3. Introduce el cambio más pequeño que respete esa frontera.
4. Ejecuta primero las pruebas específicas de la zona.
5. Compara otra vez contra `main` antes del PR o merge.
6. Revisa conflictos semánticos de archivos, no sólo el indicador de merge de Git.
7. Usa CI completo, browser/runtime smoke y preview de Vercel como gates cuando correspondan.
8. Conserva el método de merge permitido por la configuración vigente del repositorio.

Si `main` avanza durante una revisión, detén la validación final, inspecciona el nuevo commit/PR y después integra o rebasea de forma explícita. No reutilices un CI verde de un head anterior como evidencia del head nuevo.

## Hub y routing

Cuando una rama toca la superficie pública:

- confirma raíz y rutas directas;
- conserva `hub-search.js` / `hub-search.css` si no estás cambiando búsqueda;
- verifica que `/v1/meta` y `/v1/search` sigan resolviendo a la capa operacional;
- conserva el proxy para `/v1/:path*`, `/docs` y `/readyz` mientras la arquitectura siga vigente;
- no agregues una segunda URL “canónica” en documentación si el dominio público puede servir el mismo contrato.

## Presentación y documentación

La frontera mantenible de marca es:

- `docs/assets/arancel-mx-*.svg` para GitHub, documentación y presentaciones;
- `website/assets/arancel-mx-mark.svg`, `arancel-mx-logo.svg` y `site-brand.css` para identidad del hub;
- `README.md` / `README.en.md` como landing técnica breve;
- `docs/README.md` como índice canónico de documentación profunda;
- `docs/project-overview.md` para arquitectura conceptual y límites de producto.

No edites manualmente `website/assets/index-*.js`, `website/assets/index-*.css` ni el runtime generado dentro de `website/index.html` para cambios de branding. Esos cambios deben entrar mediante la fuente y regeneración reproducible correspondiente.

PR #134 eliminó el runtime/debug collector de Manus del sitio público. Regeneraciones futuras deben conservar esa limpieza y sus tests.

## Dependencias y certificación

Cuando una rama toca dependencias o publicación de paquete, revísala después de cambios activos que también modifiquen `pyproject.toml`, `requirements/` o la configuración de build de Vercel. El paquete Python y las funciones operativas de Vercel no usan necesariamente el mismo mecanismo de instalación, por lo que cada plataforma debe probar el contrato que realmente ejecuta.

No reintroduzcas `requirements.txt` sólo para hacer visible el driver de Vercel. Si cambia el mecanismo de bundle, debe actualizarse conjuntamente `vercel.json`, los handlers operativos, sus tests y este handoff.

## Trabajos fuera de este handoff

Dependabot, ramas antiguas o issues funcionales deben evaluarse por separado. No mezcles una actualización de dependencias, una corrección de pipeline o una reconciliación NICO dentro de un PR puramente documental sólo para reducir el número de ramas.

Esta guía no sustituye [CONTRIBUTING.md](../CONTRIBUTING.md), [SECURITY.md](../SECURITY.md), las protecciones de `main` ni los checks requeridos. Es el mapa de integración para preservar decisiones ya verificadas.
