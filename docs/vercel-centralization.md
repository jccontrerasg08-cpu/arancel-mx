# Vercel Centralization

The public **core retrieval** surface is being centralized on Vercel Functions backed by the one active, verified Neon release. GitHub Actions remains the only system that captures official sources, reconciles evidence, builds the immutable GitHub Release, and publishes attestation. Neon is a versioned serving projection, not a source of truth.

| Public route family | Current target | Release identity |
|---|---|---|
| `/v1/meta`, `/readyz`, `/v1/search` | Vercel operational function | Active Neon release |
| Exact lookup, chapters, sections, parent, and children | Vercel operational function | Active Neon release |
| `ficha`, suggest, provenance, and national notes | Vercel operational function | Active Neon release |
| `/documentation` | Local React documentation hub | Public repository documents and route limits |

## Guardrail

Every record payload read from `current_operational_record` must carry the same `dataset_version` as `operational_active_release`. A mismatch is rejected at the shared operational-query boundary; public serving must never mix record data from one release with metadata from another.

## Evidence Promotion Status

The promotion loader stores source-document, record-provenance, and national-note evidence as an immutable `evidence_json` snapshot on the versioned operational release. Certified synchronization promotes that snapshot atomically with the active-record pointer.

The verified evidence routes for `ficha`, suggest, provenance, and national notes run on Vercel against that active release. The local `/documentation` route is the public discovery hub for documented limits and repository contracts. Routes outside the promoted read-only surface do not use an external proxy.
