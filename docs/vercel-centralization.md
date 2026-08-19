# Vercel Centralization

The public **core retrieval** surface is being centralized on Vercel Functions backed by the one active, verified Neon release. GitHub Actions remains the only system that captures official sources, reconciles evidence, builds the immutable GitHub Release, and publishes attestation. Neon is a versioned serving projection, not a source of truth.

| Public route family | Current target | Release identity |
|---|---|---|
| `/v1/meta`, `/readyz`, `/v1/search` | Vercel operational function | Active Neon release |
| Exact lookup, chapters, sections, parent, and children | Vercel operational function | Active Neon release |
| `ficha`, suggest, provenance, and national notes | Temporary FastAPI compatibility route | Awaiting the first evidence-bearing Neon promotion |
| `/openapi.json`, `/docs`, repository telemetry | Temporary FastAPI compatibility route | Discovery/telemetry migration not yet complete |

## Guardrail

Every record payload read from `current_operational_record` must carry the same `dataset_version` as `operational_active_release`. A mismatch is rejected at the shared operational-query boundary; public serving must never mix record data from one release with metadata from another.

## Next Promotion Gate

The promotion loader now stores source-document, record-provenance, and national-note evidence as an immutable `evidence_json` snapshot on the versioned operational release. The next certified sync creates the database column if needed and promotes this snapshot atomically with the active-record pointer.

Only after that verified promotion succeeds may the compatibility routes for `ficha`, suggest, provenance, and national notes be rewritten to Vercel. Before removing the remaining FastAPI proxy, the project must prove API response parity and publish a Vercel-owned OpenAPI artifact and documentation endpoint.

## FastAPI Role

FastAPI remains a **non-public reference adapter** during this transition. It must not regain ownership of already migrated public lookup or hierarchy routes. Do not remove its code or deployment manifest in the same change as the Vercel cutover; retire the hosted service only after the evidence routes, API discovery, and production smoke checks complete a verified release cycle.
