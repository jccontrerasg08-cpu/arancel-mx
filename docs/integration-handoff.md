# Handoff de integración

> **Baseline revisada:** `53fa6cc959e70eee5329cbd42d517488a58cbc27`, después de PR #138 (`docs: compact repository front door and navigation`). Esta baseline incorpora también #140 (separación entre documentación y liveness externo), #142 (`/readyz` servido por la capa operacional) y #143–#145 (sincronización, versionado y targeting acotado del bridge público). Antes de terminar cualquier rama, compara de nuevo contra `origin/main`.

Esta guía evita que un cambio correcto de forma aislada revierta decisiones arquitectónicas posteriores. Cada PR debe preservar las fronteras entre publicación oficial, capa operacional, hub público, API reusable, paquete Python y documentación.

## Fronteras que deben preservarse

| Área | Contrato vigente | Archivos de alto riesgo |
|---|---|---|
| Hub público | `https://arancel-mx.vercel.app` sirve `website/` y presenta las rutas públicas bajo un solo dominio. La landing generada conserva su layout; el shell mantenible sólo agrega marca y sincronización acotada. | `website/`, `vercel.json`, `tests/test_public_site.py` |
| Capa operacional | Metadatos, búsqueda, ficha, jerarquía, procedencia, notas nacionales y `/readyz` son read-only, respaldados por Neon y sincronizados desde releases verificadas. | `api/operational.py`, `api/sync_operational.py`, `api/_runtime.py`, `src/arancel_mx/operational/` |
| FastAPI reusable | OpenAPI, `/docs` y las rutas `/v1/*` no promovidas se presentan en Vercel mediante proxy al runtime FastAPI. | `src/arancel_mx/api/`, `vercel.json`, `docs/external-consumption.md` |
| Runtime operacional de Vercel | El driver PostgreSQL se bundlea en `api/_vendor`; el paquete del proyecto se incluye desde `src/arancel_mx/**` y `api/_runtime.py` hace explícito el bootstrap del src-layout. | `vercel.json`, `api/_runtime.py`, handlers operativos, `.gitignore` |
| Caché del sitio | Sólo los bundles generados con nombre `index-*` son inmutables. Assets mantenibles con nombre estable deben revalidarse. | `vercel.json`, `website/index.html`, `website/assets/` |
| Paquete y dependencias | La librería pública conserva dependencias base y el extra `operational`; Vercel no debe convertir su driver aislado en dependencia base. | `pyproject.toml`, `requirements/`, packaging tests |
| Fuentes y liveness | Una URL puede seguir siendo fuente/documentación válida aunque su transporte externo sea inestable; la excepción debe ser explícita y testeada. | `scripts/check_documented_urls.py`, `tests/test_documented_urls.py`, docs de fuentes |
| Releases y fuentes | La release verificable sigue siendo la fuente de verdad. Neon es una proyección de serving. | `src/arancel_mx/sources/`, `src/arancel_mx/release/`, `src/arancel_mx/operational/` |
| CI | Los checks deben cubrir Python, runtime, browser, distribución y publicación. | `.github/workflows/`, tests de hardening |
| Presentación | README raíz es front door compacto; `docs/README.md` es navegación profunda; Vercel es la experiencia interactiva. | `README*.md`, `docs/`, assets de marca |

## Arquitectura del Central Hub

```text
GitHub Release verificada
          ↓
sync operacional idempotente
          ↓
        Neon
          ↓
Vercel: metadatos, búsqueda, ficha y evidencia activa

Vercel: OpenAPI, docs y rutas no promovidas
          ↓ proxy
   FastAPI reusable

Vercel: /
          ↓
website/ + shell mantenible
```

GitHub Releases siguen siendo la fuente canónica e inmutable. Neon no sustituye el dataset canónico y Vercel no mueve el pipeline legal/de publicación a la capa web. La identidad reproducible permanece en la release, `manifest.json`, hashes y fuentes capturadas.

## Contrato operativo de Vercel

La versión de dataset visible en el hub y la publicada por `/v1/meta` deben corresponder a la misma release promovida. `/readyz` consulta la misma metadata activa desde la capa operacional y sólo responde ready cuando esa identidad existe. Si la identidad no está disponible o no puede validarse, el despliegue no debe presentar una versión alternativa como equivalente.

Configuración relevante:

- `ARANCEL_MX_DATABASE_URL` es el nombre canónico de la conexión operacional.
- `ARANCEL_MX_DATABASE_DATABASE_URL` se admite como compatibilidad controlada cuando la integración administrada de Neon genera ese nombre.
- `CRON_SECRET` es un secreto de Production enviado como Bearer token al cron operacional; no se registra ni reutiliza.
- `vercel.json` usa `python3.13 -m pip install --target api/_vendor 'psycopg[binary]>=3.3.4'`. La versión debe mantenerse alineada con `.python-version` para compilar el driver con la familia del runtime desplegado.
- `api/_runtime.py` agrega el directorio `src/` al principio de `sys.path` antes de importar `arancel_mx` desde los handlers de Vercel.
- `api/operational.py` y `api/sync_operational.py` incluyen `{api/_vendor/**,src/arancel_mx/**}` mediante `functions.includeFiles`.
- La función read-only tiene `maxDuration: 30`; la sincronización certificada tiene `maxDuration: 60`. Son límites deliberadamente inferiores al máximo de plataforma para acotar fallos y consumo.
- `api/_vendor/` permanece ignorado por Git. Es un artefacto de build, no código fuente versionado.
- `requirements.txt` no debe reaparecer para este runtime: el driver aislado no debe convertirse en dependencia global por accidente.
- La librería Python mantiene su extra `operational` para instalaciones que sí necesiten conectividad PostgreSQL fuera del bundle de Vercel.

No elimines variables creadas por la integración administrada de Neon sólo porque una de ellas no se lea directamente en el código. Antes de limpiar aliases, verifica su origen y realiza un despliegue satisfactorio con la configuración resultante.

## Routing del hub

El orden de rewrites es parte del contrato:

1. Metadatos, búsqueda, sugerencias, ficha, jerarquía, procedencia, notas nacionales y `/readyz` llegan a la función operacional.
2. `/openapi.json`, `/docs` y las rutas `/v1/*` no promovidas se reescriben al runtime FastAPI.
3. El fallback SPA sólo aplica a rutas que no empiezan con `assets/` ni `api/`: `/((?!assets/|api/).*)`.

La exclusión del fallback evita que un asset inexistente o una Function mal referenciada termine respondiendo `website/index.html` con HTTP aparentemente exitoso. No amplíes el catch-all por comodidad.

Las rutas operacionales comparten dominio con FastAPI, pero siguen siendo adaptadores de serving distintos. Cualquier cambio de shape, validación, ranking, CORS o errores debe comprobarse contra el contrato público para evitar semantic drift entre Neon/Vercel y FastAPI/OpenAPI.

## Caché y assets

La política pública distingue dos clases:

- `/assets/index-(.*)` corresponde a bundles generados con nombre content-addressed y usa `Cache-Control: public, max-age=31536000, immutable`.
- `/assets/((?!index-).*)` cubre logo, mark, `site-brand.css`, `site-bridge.js` y otros assets mantenibles con nombre estable y usa `Cache-Control: public, max-age=0, must-revalidate`.

No marques como `immutable` un nombre estable que pueda cambiar entre deployments. El query de versión en `website/index.html` sirve como cutover explícito para clientes que hayan recibido la política histórica de caché larga; no sustituye una política de caché correcta.

Cuando exista un build reproducible para todos los assets del shell, la evolución preferida es usar nombres con hash de contenido y dejar que esos archivos entren en la clase inmutable automáticamente.

## Sincronización visual del hub

El bridge público no es la fuente de verdad de la release. Consulta `/v1/meta`, conserva la `dataset_tag` activa y actualiza únicamente el label heredado de la tarjeta de release después del render cuando sea necesario. El targeting está acotado a `.release-window code` y exige que su texto completo tenga el formato `release / data-YYYY.MM.DD`; no debe volver a recorrer o reemplazar texto arbitrario del DOM.

`website/index.html` referencia `site-bridge.js` con un query de versión para invalidar clientes que puedan conservar una versión histórica.

Reglas:

- no hardcodear una release como identidad operativa del hub;
- conservar la sincronización con `/v1/meta` después de mutaciones/render tardío;
- limitar cualquier reescritura visual al elemento semántico que representa la release;
- no editar bundles `website/assets/index-*.js` o `index-*.css` manualmente;
- no cargar `hub-search.js` ni `hub-search.css` antes de `#root`: la búsqueda sigue disponible como API en `/v1/search`, pero la landing original es la única aplicación visual de entrada;
- mantener el logo horizontal en el header mantenible y el mark compacto para favicon/identidad reducida;
- conservar la limpieza de runtime/debug/analytics heredados del generador.

Los archivos legacy de búsqueda pueden permanecer temporalmente en el repositorio mientras se decide su eliminación, pero no forman parte del shell público mientras exista este contrato.

## Cron y promoción operacional

El cron de Vercel sigue siendo un backstop de sincronización, no una fuente de verdad. Su handler descarga la release pública más reciente, verifica el bundle completo y sólo entonces promueve el candidato en Neon de forma idempotente.

La expresión vigente es semanal. Si el proyecto opera bajo Hobby, la ejecución del cron tiene precisión horaria y los límites de deployments del plan también pueden afectar previews independientes del estado del código. No conviertas un error de cuota de deployment en un cambio de arquitectura o en un bypass de CI.

Una evolución posterior puede disparar la promoción después de publicar una release certificada y conservar el cron semanal como reconciliación. Ese cambio requiere un diseño separado porque introduce un nuevo límite de confianza entre GitHub Actions y Vercel.

## Fuentes documentadas vs liveness de CI

#140 formalizó una frontera importante: **documentar una URL oficial y exigir que siempre responda desde GitHub Actions son contratos distintos**.

VUCEM y algunos endpoints de Diputados pueden terminar TLS o agotar timeout desde runners modernos. Deben seguir documentados y validados sintácticamente, pero sólo quedar fuera del probe live mediante `EXTERNALLY_UNPROBEABLE_URLS`, con tests que garanticen que cada excepción siga perteneciendo al conjunto documentado. SNICE y DOF canónicos continúan siendo probes activos.

No elimines una fuente oficial sólo para volver verde CI. Tampoco agregues una excepción de liveness sin evidencia de fallo de transporte y sin conservar la URL en el conjunto documentado.

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

## Presentación y documentación

La frontera mantenible de marca y documentación es:

- `docs/assets/arancel-mx-*.svg` para GitHub, documentación y presentaciones;
- `website/assets/arancel-mx-mark.svg`, `arancel-mx-logo.svg` y `site-brand.css` para identidad del hub;
- `README.md` / `README.en.md` como landing técnica breve;
- `docs/README.md` como índice canónico de documentación profunda;
- `docs/project-overview.md` para arquitectura conceptual y límites de producto;
- `docs/research/` para investigación y mapas especializados que no deben saturar la raíz del repositorio.

El README debe dirigir primero al hub público para interacción, a GitHub Releases para bytes verificables y a `docs/README.md` para profundidad técnica. No debe duplicar manuales completos de CLI, API, fuentes o release engineering.

No edites manualmente `website/assets/index-*.js`, `website/assets/index-*.css` ni runtime generado para cambios de branding. Los cambios generados deben entrar mediante la fuente y regeneración reproducible correspondiente.

## Referencias primarias de Vercel

- [Project configuration with `vercel.json`](https://vercel.com/docs/project-configuration/vercel-json)
- [Python Runtime](https://vercel.com/docs/functions/runtimes/python)
- [Function maximum duration](https://vercel.com/docs/functions/configuring-functions/duration)
- [Cache-Control headers](https://vercel.com/docs/caching/cache-control-headers)
- [Managing Cron Jobs](https://vercel.com/docs/cron-jobs/manage-cron-jobs)
- [Cron usage and pricing](https://vercel.com/docs/cron-jobs/usage-and-pricing)
- [Platform limits](https://vercel.com/docs/limits)

Estas referencias son de plataforma y pueden cambiar. Cuando una decisión dependa de cuota, duration o precisión de cron, verifica la documentación vigente y el plan efectivo antes de modificar el código.

## Dependencias y certificación

Cuando una rama toca dependencias o publicación de paquete, revísala después de cambios activos que también modifiquen `pyproject.toml`, `requirements/` o la configuración de build de Vercel. El paquete Python y las funciones operativas de Vercel no usan necesariamente el mismo mecanismo de instalación, por lo que cada plataforma debe probar el contrato que realmente ejecuta.

No reintroduzcas `requirements.txt` sólo para hacer visible el driver de Vercel. Si cambia el mecanismo de bundle, debe actualizarse conjuntamente `vercel.json`, los handlers operativos, sus tests y este handoff.

## Trabajos fuera de este handoff

Dependabot, ramas antiguas o issues funcionales deben evaluarse por separado. No mezcles una actualización de dependencias, una corrección de pipeline o una reconciliación NICO dentro de un PR de superficie pública sólo para reducir el número de ramas.

Esta guía no sustituye [CONTRIBUTING.md](../CONTRIBUTING.md), [SECURITY.md](../SECURITY.md), las protecciones de `main` ni los checks requeridos. Es el mapa de integración para preservar decisiones ya verificadas.
