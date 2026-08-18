# Handoff de integración

> **Baseline revisada:** `e861aed65ed347504ec4a0c24c41b72c8e9c1341`, después de PR #145 (`fix: target legacy release card label`). Esta baseline incorpora también #140 (separación entre documentación y liveness externo), #142 (`/readyz` servido por la capa operacional), y #143–#145 (sincronización, versionado y targeting acotado del bridge público). Antes de terminar cualquier rama, compara de nuevo contra `origin/main`.

Esta guía evita que un cambio correcto de forma aislada revierta decisiones arquitectónicas posteriores. Cada PR debe preservar las fronteras entre publicación oficial, capa operacional, hub público, API reusable, paquete Python y documentación.

## Fronteras que deben preservarse

| Área | Contrato vigente | Archivos de alto riesgo |
|---|---|---|
| Hub público | `https://arancel-mx.vercel.app` sirve `website/`, búsqueda, metadata y rutas públicas bajo un solo dominio. | `website/`, `vercel.json`, `tests/test_public_site.py` |
| Capa operacional | `/v1/meta`, `/v1/search` y `/readyz` son read-only, respaldados por Neon y sincronizados desde releases verificadas. | `api/operational.py`, `api/sync_operational.py`, `src/arancel_mx/operational/` |
| FastAPI reusable | El resto de `/v1/*` y `/docs` se presenta en Vercel mediante proxy al runtime FastAPI. | `src/arancel_mx/api/`, `vercel.json`, `docs/external-consumption.md` |
| Runtime operacional de Vercel | `psycopg[binary]` se bundlea de forma aislada en `api/_vendor` y sólo se incluye en las funciones operativas. | `vercel.json`, `api/operational.py`, `api/sync_operational.py`, `.gitignore` |
| Paquete y dependencias | La librería pública conserva dependencias base y el extra `operational`; Vercel no debe convertir su driver aislado en dependencia base. | `pyproject.toml`, `requirements/`, packaging tests |
| Fuentes y liveness | Una URL puede seguir siendo fuente/documentación válida aunque su transporte externo sea inestable; la excepción debe ser explícita y testeada. | `scripts/check_documented_urls.py`, `tests/test_documented_urls.py`, docs de fuentes |
| Releases y fuentes | La release verificable sigue siendo la fuente de verdad. | `src/arancel_mx/sources/`, `src/arancel_mx/release/`, tests de pipeline/fuentes |
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
Vercel: /v1/meta + /v1/search + /readyz

Vercel: /v1/* restante + /docs
          ↓ proxy
   FastAPI reusable
```

Neon no sustituye el dataset canónico y Vercel no mueve el pipeline legal/de publicación a la capa web. La identidad reproducible permanece en la release, `manifest.json`, hashes y fuentes capturadas.

## Contrato operativo de Vercel

La versión de dataset visible en el hub y la publicada por `/v1/meta` deben corresponder a la misma release promovida. `/readyz` consulta la misma metadata activa desde la capa operacional y sólo responde ready cuando esa identidad existe. Si la identidad no está disponible o no puede validarse, el despliegue no debe presentar una versión alternativa como equivalente.

Configuración relevante:

- `ARANCEL_MX_DATABASE_URL` es el nombre canónico de la conexión operacional.
- `ARANCEL_MX_DATABASE_DATABASE_URL` se admite como compatibilidad controlada cuando la integración administrada de Neon genera ese nombre.
- `CRON_SECRET` es un secreto de Production enviado como Bearer token al cron operacional; no se registra ni reutiliza.
- `vercel.json` usa `python3.13 -m pip install --target api/_vendor 'psycopg[binary]>=3.3.4'` para construir el driver operacional con la misma familia de Python del runtime desplegado.
- `api/operational.py` y `api/sync_operational.py` cargan `api/_vendor` antes de importar el driver y son las únicas funciones que incluyen ese directorio mediante `functions.includeFiles`.
- `api/_vendor/` permanece ignorado por Git. Es un artefacto de build, no código fuente versionado.
- `requirements.txt` no debe reaparecer para este runtime: el driver aislado no debe convertirse en dependencia global por accidente.
- La librería Python mantiene su extra `operational` para instalaciones que sí necesiten conectividad PostgreSQL fuera del bundle de Vercel.

No elimines variables creadas por la integración administrada de Neon sólo porque una de ellas no se lea directamente en el código. Antes de limpiar aliases, verifica su origen y realiza un despliegue satisfactorio con la configuración resultante.

## Sincronización visual del hub

El bridge público no es la fuente de verdad de la release. Consulta `/v1/meta`, conserva la `dataset_tag` activa y actualiza únicamente el label heredado de la tarjeta de release después del render cuando sea necesario. Desde #145, el targeting está acotado a `.release-window code` y exige que su texto completo tenga el formato `release / data-YYYY.MM.DD`; no debe volver a recorrer o reemplazar texto arbitrario del DOM.

`website/index.html` referencia `site-bridge.js` con un query de versión para invalidar caché cuando cambia ese comportamiento.

Reglas:

- no hardcodear una release como identidad operativa del hub;
- conservar la sincronización con `/v1/meta` después de mutaciones/render tardío;
- limitar cualquier reescritura visual al elemento semántico que representa la release;
- versionar la referencia del bridge cuando cambie su comportamiento y la política de caché lo requiera;
- no editar bundles `website/assets/index-*.js` o `index-*.css` manualmente.

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

## Hub y routing

Cuando una rama toca la superficie pública:

- confirma raíz y rutas directas;
- conserva `hub-search.js` / `hub-search.css` si no estás cambiando búsqueda;
- verifica que `/v1/meta`, `/v1/search` y `/readyz` sigan resolviendo a la capa operacional;
- conserva el proxy para `/v1/:path*` y `/docs` mientras la arquitectura siga vigente;
- conserva la carga versionada de `site-bridge.js` mientras ese asset requiera invalidación de caché;
- conserva el targeting `.release-window code` para el label de release mientras exista ese componente;
- no agregues una segunda URL “canónica” en documentación si `https://arancel-mx.vercel.app` puede servir el mismo contrato.

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

PR #134 eliminó el runtime/debug collector de Manus del sitio público. Regeneraciones futuras deben conservar esa limpieza y sus tests.

## Dependencias y certificación

Cuando una rama toca dependencias o publicación de paquete, revísala después de cambios activos que también modifiquen `pyproject.toml`, `requirements/` o la configuración de build de Vercel. El paquete Python y las funciones operativas de Vercel no usan necesariamente el mismo mecanismo de instalación, por lo que cada plataforma debe probar el contrato que realmente ejecuta.

No reintroduzcas `requirements.txt` sólo para hacer visible el driver de Vercel. Si cambia el mecanismo de bundle, debe actualizarse conjuntamente `vercel.json`, los handlers operativos, sus tests y este handoff.

## Trabajos fuera de este handoff

Dependabot, ramas antiguas o issues funcionales deben evaluarse por separado. No mezcles una actualización de dependencias, una corrección de pipeline o una reconciliación NICO dentro de un PR puramente documental sólo para reducir el número de ramas.

Esta guía no sustituye [CONTRIBUTING.md](../CONTRIBUTING.md), [SECURITY.md](../SECURITY.md), las protecciones de `main` ni los checks requeridos. Es el mapa de integración para preservar decisiones ya verificadas.
