# Retiro de la API dinámica `/v1`

**Estado: retirada el 2026-11-20** por decisión del propietario, antes de la fecha anunciada (2027-01-31). La API dinámica de Vercel sobre Neon (`api/operational.py`), su cron semanal de sincronización (`api/sync_operational.py`) y la proyección `arancel_mx.operational` ya no existen en el repositorio. El reemplazo es la API estática de [decisión 0002](../decisions/0002-arquitectura-github-primero.md) en `/data/v1`, descrita en [arquitectura](../architecture.md#archivos-de-la-api-estática) y en [consumo externo](../external-consumption.md#api-http-pública).

## Qué pasa con las direcciones antiguas

`vercel.json` redirige de forma permanente (308):

| Antes | Ahora |
|---|---|
| `/v1/meta` | `/data/v1/meta.json` |
| `/v1/sections` | `/data/v1/sections.json` |
| `/v1/chapters` | `/data/v1/chapters.json` |
| `/v1` y cualquier otra `/v1/...` (`search`, `suggest`, `lookup`, `ficha`, `codes/...`, `repository`, `national-notes`) | `/documentation` |
| `/healthz`, `/readyz` | sin ruta (404); el estado del servicio lo vigila `check_public_service.py` sobre `/data/v1` |

Para lo que fue `search`, `lookup`, `ficha`, `parent`, `children`, `provenance` y `national-notes`, el equivalente es `/data/v1/search-index.json` más `/data/v1/records/{hs2}.json`, `/data/v1/provenance/{hs2}.json` y `/data/v1/national-notes/{hs2}.json`. El explorador y el escritorio de comercio ya los usaban.

## Qué se retiró

- `api/operational.py`, `api/sync_operational.py`, `api/_runtime.py` y el `buildCommand` que instalaba `psycopg` con hashes.
- `crons`, `functions` y los encabezados `Deprecation`/`Sunset` de `vercel.json`.
- `src/arancel_mx/operational/`, `scripts/promote_operational_release.py`, `requirements/vercel.txt`, el extra `operational` de `pyproject.toml` y las pinas de `psycopg` en `requirements/production-build.txt`.
- Las pruebas de `tests/operations/` que dependían de lo anterior. Quedan las de la función de balanza comercial (`api/trade_balance.py`) y las de contrato de `vercel.json`.

El servidor FastAPI sigue en el paquete (`arancel_mx.api`) y el job `api-runtime` de CI lo sigue probando.

## Pasos pendientes fuera del repositorio (requieren tu cuenta)

El código ya no usa ninguno de estos recursos, así que no hay prisa ni orden obligatorio:

1. En Vercel (Settings → Environment Variables), borrar `ARANCEL_MX_DATABASE_URL`, `ARANCEL_MX_DATABASE_DATABASE_URL` y `CRON_SECRET`.
2. En Neon, borrar el proyecto de la base. **Es lo único irreversible**: hasta entonces se puede volver atrás.
3. Desinstalar la integración de Neon en Vercel.

## Reversión

Revertir el commit que retiró la función restaura `api/`, el cron y las reescrituras. Mientras la base de Neon exista, la sincronización semanal la vuelve a poblar sola.
