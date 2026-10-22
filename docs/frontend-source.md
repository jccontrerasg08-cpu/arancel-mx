# Fuente mantenible del frontend

Este documento explica cómo se desarrolla, compila y prueba el frontend de `arancel-mx` y de dónde obtiene sus datos. Está dirigido a quien cambie el sitio o el explorador. La interfaz principal se mantiene en `frontend/` (Vite + React); la salida compilada no se edita a mano. La mesa de comercio exterior sigue siendo una página estática independiente en `/trade` que la sincronización no sobrescribe.

## Desarrollo y compilación

El repositorio usa npm con `package-lock.json`.

| Objetivo | Comando | Resultado |
|---|---|---|
| Instalar dependencias | `npm ci` | Instala React, React Router, Vite y Playwright con las versiones exactas del lockfile. |
| Previsualizar fuente | `npm run dev:frontend` | Sirve la aplicación React desde `frontend/` con Vite para revisión local. |
| Compilar y sincronizar | `npm run build:frontend` | Ejecuta `scripts/build-frontend.mjs` y `scripts/sync-frontend-static.mjs`: genera la salida de Vite y la copia a `website/` (Vercel) y a `src/arancel_mx/api/static/site/` (FastAPI). |
| Probar contratos fuente | `node --test tests/e2e/*.test.mjs` | Verifica rutas, contenido declarativo, build, glosario y normalización de códigos. |
| Probar en navegador | `npm run test:e2e` | Ejecuta Playwright (`tests/e2e/*.spec.mjs`) contra el sitio servido por uvicorn. |

`scripts/sync-frontend-static.mjs` conserva `trade.html`, sus estilos, scripts y activos. Al copiar la aplicación principal, asigna al bundle JavaScript un nombre derivado de su SHA-256 y elimina sólo los bundles principales obsoletos. Así se mantiene la caché inmutable sin borrar activos independientes.

## Fuente de las rutas

El manifiesto central está en `frontend/src/routes.js`; `frontend/src/App.jsx` lo convierte en rutas React. El contenido editorial vive en `frontend/src/content.js` y `frontend/src/pages.jsx` contiene los componentes de cada superficie. El glosario se publica como módulo declarativo de 189 entradas en `frontend/src/glossary-data.js`.

| Superficie | Fuente principal | Comportamiento |
|---|---|---|
| `/`, `/documentation`, `/wiki`, `/glossary`, `/trust` | Componentes editoriales y contenido declarativo | Navegación, fuentes visibles, filtros y estados vacíos recuperables. |
| `/app`, `/app/record/:code`, `/app/chapter/:code`, `/chapters`, `/changes` | Componentes de consulta sobre la API estática | Consulta de la release, jerarquía, URLs compartibles, evidencia y controles de teclado. |
| `/records` | `localStorage` | Registros de investigación locales, sin cuenta ni almacenamiento en servidor. |
| `/trade` | Página estática independiente | Simulación orientativa, evidencia T-MEC, RRNA y expediente local. |

## Datos

El navegador lee la API estática de sólo lectura bajo `/data/v1` (`DATA_BASE` en `frontend/src/pages.jsx`) mediante el cliente `frontend/src/static-api.js`, que resuelve `lookup`, `ficha`, `parent`, `children`, `provenance`, `search` y `suggest` a partir de `meta.json`, `records/{hs2}.json`, `search-index.json` y el resto de archivos del árbol.

```text
navegador → /data/v1/...  ┬→ Vercel: rewrite a GitHub Pages (https://jccontrerasg08-cpu.github.io/arancel-mx/v1/)
                          └→ FastAPI local: app.py genera el árbol desde el dataset activo
```

- **Producción:** `vercel.json` reescribe `/data/v1/:path*` hacia GitHub Pages, que publica el pipeline oficial tras cada release verificada.
- **Local:** `uvicorn arancel_mx.api.app:app` sirve `/data/v1/...` y genera el árbol desde el dataset configurado la primera vez que se pide.

`tests/test_static_api.py` ejecuta `tests/frontend/static_api_parity.mjs` para comprobar que el cliente del navegador devuelve lo mismo que `arancel_mx.static_api.StaticApi` y que el `Dataset` de Python.

Si la API estática no responde, el explorador y la ficha muestran una capa mínima de ejemplos registrados, marcada como presentación de respaldo. Esos ejemplos no sustituyen la release, no amplían el dataset y no confirman decisiones legales, arancelarias, de origen o de clasificación.

## Verificación

Un cambio de frontend se valida con la suite Python, los contratos `node --test` y Playwright. Las comprobaciones HTTP externas pueden depender de la disponibilidad temporal de las autoridades; no deben ocultar fallos deterministas de build, rutas, seguridad o accesibilidad.

## Relacionado

- [Arquitectura](architecture.md#7-frontend)
- [Consumo externo](external-consumption.md)
- [Proceso de release](release-process.md#9-api-estática-en-github-pages)
- [Identidad visual](brand.md)
