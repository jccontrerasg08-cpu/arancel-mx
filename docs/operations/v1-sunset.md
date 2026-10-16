# Retiro de la API dinámica `/v1`

Runbook de la API dinámica que todavía sirve Vercel en `https://arancel-mx.vercel.app/v1/...`. Está **deprecada** desde el 2026-10-16 por la [decisión 0002](../decisions/0002-arquitectura-github-primero.md) y se retira el **2027-01-31**. Es para quien mantiene la plataforma hasta esa fecha y para quien ejecute el retiro.

El reemplazo es la API estática en `/data/v1`, descrita en [arquitectura](../architecture.md#archivos-de-la-api-estática) y en [consumo externo](../external-consumption.md#api-http-pública).

## Qué sigue funcionando hasta el retiro

```text
GitHub Release verificada
          ↓
sincronización operacional (cron semanal de Vercel)
          ↓
        Neon
          ↓
Vercel: metadatos, búsqueda, ficha y evidencia activa
```

| Ruta | Destino | Reemplazo estático |
|---|---|---|
| `/v1/meta`, `/readyz`, `/healthz` | `api/operational.py` | `/data/v1/meta.json` |
| `/v1/search`, `/v1/suggest` | `api/operational.py` | `/data/v1/search-index.json` + `records/{hs2}.json` |
| `/v1/lookup/{code}`, `/v1/ficha/{code}`, `parent`, `children` | `api/operational.py` | `/data/v1/records/{hs2}.json` |
| `/v1/codes/{code}/provenance` | `api/operational.py` | `/data/v1/provenance/{hs2}.json` |
| `/v1/chapters/{chapter}/national-notes` | `api/operational.py` | `/data/v1/national-notes/{hs2}.json` |
| `/v1/sections`, `/v1/chapters` | `api/operational.py` | `/data/v1/sections.json`, `/data/v1/chapters.json` |

Toda respuesta bajo `/v1` lleva estos encabezados, definidos en `vercel.json`:

- `Deprecation: @1792108800`
- `Sunset: Sun, 31 Jan 2027 00:00:00 GMT`
- `Link` con `rel="successor-version"` hacia el manifest estático y `rel="deprecation"` hacia la decisión 0002

## Contrato operativo mientras exista

- **Una sola release activa.** Cada registro leído de `current_operational_record` debe tener el mismo `dataset_version` que `operational_active_release`. Si no coinciden, la consulta se rechaza; nunca se mezclan datos de dos releases.
- **`/readyz`** sólo responde *ready* cuando la release activa existe en Neon.
- **Sin proxy externo.** Las rutas `/v1/*` no promovidas no se reenvían a ningún servicio de terceros.
- **El cron es un respaldo.** `api/sync_operational.py` descarga la última release, verifica el bundle completo y promueve en Neon de forma idempotente. No es fuente de verdad.

## Configuración

| Elemento | Valor |
|---|---|
| Conexión | `ARANCEL_MX_DATABASE_URL`. `ARANCEL_MX_DATABASE_DATABASE_URL` se acepta porque la integración de Neon genera ese nombre. |
| Cron | `CRON_SECRET`, enviado como Bearer token. |
| Driver | `buildCommand` ejecuta `python3.13 -m pip install --target api/_vendor 'psycopg[binary]>=3.3.4'`. `api/_vendor/` está en `.gitignore`. No se reintroduce `requirements.txt` para esto. |
| Arranque | `api/_runtime.py` antepone `src/` a `sys.path`. Las funciones incluyen `{api/_vendor/**,src/arancel_mx/**}`. |
| Límites | `maxDuration` de 30 s para la consulta y 60 s para la sincronización. |
| Paquete | El extra `operational` (`psycopg[binary]`) sólo existe para este runtime. |

## Pasos del retiro (a partir del 2027-01-31)

Cada paso es reversible hasta borrar la base de Neon.

1. Confirmar que GitHub Pages sirve la última release y que `published-bundle-canary.yml` está verde.
2. En `vercel.json`, eliminar `buildCommand`, `functions`, `crons`, las reescrituras `/v1*`, `/healthz` y `/readyz`, y el bloque de encabezados `/v1(.*)`. Las rutas `/v1/*` quedan en 404, o se redirigen a `/documentation` si se decide así en el PR.
3. Borrar `api/`, `src/arancel_mx/operational/`, `scripts/promote_operational_release.py`, el extra `operational` de `pyproject.toml` y sus pruebas en `tests/operations/`.
4. Conservar el job `api-runtime` de `ci.yml`: prueba el servidor FastAPI que sigue en el paquete. Sólo se borran las pruebas de `tests/operations/`.
5. Desplegar y comprobar que el sitio funciona sin funciones.
6. Borrar las variables de Neon y `CRON_SECRET` en Vercel. Después, borrar el proyecto de Neon.
7. Actualizar `CHANGELOG.md` (sección *Removed*), este documento y la [política de compatibilidad](../compatibility.md).

## Relacionado

- [Decisión 0002](../decisions/0002-arquitectura-github-primero.md)
- [Política de compatibilidad](../compatibility.md)
- [Arquitectura](../architecture.md)
