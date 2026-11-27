# Decisión 0005: los diffs entre releases se precalculan en la API estática

- **Estado:** aceptada
- **Fecha:** 2026-11-24
- **Responsable:** @jccontrerasg08-cpu
- **Revisión:** el propietario delegó la decisión el 2026-11-24 («needs your call on where precomputed diffs live. do it»)
- **Relacionada con:** [decisión 0002](0002-arquitectura-github-primero.md) (GitHub como origen y servidor de datos) y el RFC de diff entre releases (#308).

## Contexto

`arancel-mx data diff` compara dos releases en la máquina de quien lo ejecuta: descarga y verifica ambas (unos 25 MB cada una) y luego compara. Para mostrar los cambios en el sitio web hace falta el mismo reporte sin que el navegador descargue dos bases DuckDB. Las opciones eran:

| Opción | Problema |
|---|---|
| Calcular en una función de Vercel | Contradice la decisión 0002: Vercel sólo sirve el frontend; además la función tendría que descargar dos releases por petición. |
| Publicar el diff como asset de la release | Cambia el contrato de los seis assets canónicos, que no se toca sin aprobación. |
| Calcular en el navegador con DuckDB-WASM | Descarga pesada para cada visitante (RFC #309, aún en diseño). |
| **Precalcular en el job `pages` y servirlo con `/data/v1`** | Ninguno de los anteriores. |

## Decisión

El job `pages` del flujo oficial (`scripts/build_static_pages.py`), que ya publica `/data/v1` en `gh-pages`, compara la release que publica con la **release publicada inmediatamente anterior** y agrega a la API estática:

- `diffs/index.json`: la comparación más reciente (`latest`), con conteos por tipo de cambio y el estado de las tablas auxiliares;
- `diffs/<desde>--<hasta>.json`: el mismo reporte que `arancel-mx data diff --format json`.

Ambos archivos quedan en el `manifest.json` de la API estática con su SHA-256 y los verifica `verify_static_api`, igual que el resto del árbol.

Reglas:

1. **Ambas releases se descargan con el cliente de consumo y deben pasar la verificación.** Si la anterior no está verificada, no se publica ninguna comparación.
2. **Una falla al obtener la release anterior nunca bloquea la publicación de los datos.** El índice queda con `diffs: []` y la razón (`reason`); nunca se publica un diff vacío que se lea como «sin cambios».
3. El reporte conserva la nota de que una diferencia entre snapshots **no es un evento legal**.
4. No se agregan servicios, credenciales ni assets a la release. El job usa el `ARANCEL_MX_GITHUB_TOKEN` que ya recibe para consultar releases.

## Consecuencias

- El sitio puede mostrar «qué cambió en la última release» leyendo un JSON estático de `/data/v1/diffs/`.
- Sólo se conserva la comparación más reciente; un historial de comparaciones requeriría conservar archivos anteriores de `gh-pages` y se decidirá aparte.
- Para revertir: `--diff-from none` en el job `pages`, o revertir el cambio; los demás archivos de la API no cambian.
