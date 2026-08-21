# Fuente mantenible del frontend

La interfaz pública principal de arancel-mx se mantiene en `frontend/`. Esta fuente sustituye la dependencia de editar un bundle generado y conserva las rutas públicas que sirve FastAPI y publica Vercel. La mesa de comercio exterior continúa como una superficie estática independiente en `/trade`; el proceso de sincronización no la sobrescribe.

## Desarrollo y compilación

| Objetivo | Comando | Resultado |
|---|---|---|
| Instalar dependencias | `pnpm install` | Instala React, React Router, Vite y herramientas de prueba bloqueadas por el lockfile. |
| Previsualizar fuente | `pnpm dev:frontend` | Sirve la aplicación React desde `frontend/` para revisión local. |
| Compilar y sincronizar | `pnpm build:frontend` | Genera la salida de Vite y sincroniza únicamente los activos de la aplicación principal con `website/` y los estáticos de FastAPI. |
| Probar contratos fuente | `node --test tests/e2e/*.test.mjs` | Verifica rutas, contenido declarativo, build, glosario y paridad estructural. |

El script `scripts/sync-frontend-static.mjs` conserva `trade.html`, sus estilos, scripts y activos. Al copiar la aplicación principal, asigna al bundle JavaScript un nombre derivado de su SHA-256 y elimina sólo bundles principales obsoletos. Esto mantiene caché inmutable sin eliminar activos independientes.

## Fuente de las rutas

El manifiesto central está en `frontend/src/routes.js`; `frontend/src/App.jsx` convierte ese manifiesto en rutas React. El contenido editorial se conserva en `frontend/src/content.js`, mientras que `frontend/src/pages.jsx` contiene los componentes y comportamientos de cada superficie. El glosario recuperado se publica como módulo declarativo de 189 entradas y puede regenerarse desde el bundle histórico mediante `scripts/recover-glossary-from-bundle.mjs`.

| Superficie | Fuente principal | Comportamiento mantenido |
|---|---|---|
| `/`, `/documentation`, `/wiki`, `/glossary`, `/trust` | Componentes editoriales y contenido declarativo | Navegación, fuentes visibles, filtros y estados vacíos recuperables. |
| `/app`, `/app/record/:code`, `/app/chapter/:code`, `/chapters`, `/changes` | Componentes de consulta y API pública | Consulta de release, jerarquía, URLs compartidas, evidencia local y controles de teclado. |
| `/records` | Persistencia delimitada a `localStorage` | Registros de investigación locales, sin cuenta ni almacenamiento de servidor. |
| `/trade` | Página estática independiente | Simulación orientativa, evidencia T-MEC, RRNA y expediente local. |

## Datos y recuperación

La API pública sigue siendo la fuente primaria de resultados, jerarquía y procedencia. Cuando la release no está disponible temporalmente, Explorer y los enlaces de registros presentan una capa mínima de ejemplos observados de la interfaz histórica. Esos ejemplos se muestran como presentación de respaldo y no sustituyen la API, no amplían el dataset ni confirman decisiones legales, arancelarias, de origen o de clasificación.

## Verificación

La distribución debe validarse con la suite Python, contratos de frontend y pruebas de navegador. Las comprobaciones HTTP externas pueden depender de disponibilidad temporal de autoridades; no deben ocultar fallos deterministas de build, rutas, seguridad o accesibilidad.
