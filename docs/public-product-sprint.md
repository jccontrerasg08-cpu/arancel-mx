# Public Product Sprint

## Goal

Make the verified `arancel-mx` dataset useful as a public research product without changing its read-only, non-classification, immutable-release boundary.

## Assumptions and Success Criteria

The public page remains a same-origin static client served by FastAPI. It must query only existing verified GET endpoints and must not download, capture, reconcile, classify, calculate transaction taxes, collect personal data, create accounts, or trigger the official pipeline.

| User need | Existing contract reused | Success criterion |
|---|---|---|
| Durable research link | `/v1/ficha/{code}` and `/v1/codes/{code}/provenance` | `/app/record/{code}` opens the exact verified record, hierarchy, release identity, provenance, and next steps. |
| Browse a product family | `/v1/chapters`, `/v1/codes/{code}/children`, `/v1/ficha/{code}` | `/app/chapter/{hs2}` opens the verified chapter and its direct descendants. |
| Understand validity and official context | Ficha effective dates, validity basis, provenance, `/v1/chapters/{chapter}/national-notes` | A record view presents only recorded dates, national notes, and official source links; it makes no reform interpretation. |
| Keep a private research list | Browser `localStorage` and `Blob` download | A user can opt in to save a record snapshot and export it locally; nothing is sent to the service. |
| Continue across product surfaces | Existing API, release, PyPI, CLI links | Record-specific next steps link to the exact API endpoint, GitHub release, CLI commands, and official source evidence. |

## Deliberate Scope Boundaries

This sprint does not reproduce a cost calculator, treaty/origin eligibility tool, paid report, lead form, account system, background monitoring, cloud synchronization, or a public source scraper. Those features would require separate legal, operational, privacy, and product designs. The smaller evidence-first workflow covers the immediate user need: explore a verified record, understand its hierarchy and validity, retain a private local snapshot, and move to the API/CLI or official source.

## Route Model

The existing `/app` document is served at three stable client routes: `/app`, `/app/record/{code}`, and `/app/chapter/{chapter}`. The client reads the path and requests the existing API endpoints; canonical sharing works because the page loads the same verified release on every route. The current FastAPI app does not have record-specific server-rendered metadata, so search-engine-oriented per-record metadata is deferred until a separate rendering layer is justified.

## Verification

The non-trivial browser interactions require focused Playwright checks: a durable record URL, a chapter URL, saved-local snapshot behavior, export, national-note/source display where the fixture contains it, and keyboard-accessible controls. Existing Python route tests protect the static-route availability.

> ponytail: `localStorage` is appropriate for a small, user-controlled research list. Its known ceiling is browser quota and per-browser scope; upgrade to IndexedDB only if saved snapshots become materially larger or require indexed offline filtering.

## Local Chrome Validation

The durable route `/app/record/85171301` was checked against the seeded verified release in Chrome. It rendered the exact fraction, registered source title and SHA256, hierarchy from HS2 to NICO, release identity, recorded validity basis, 21 chapter national notes, API/CLI/release next steps, and the local-only save control. The browser displayed the explicit non-classification boundary throughout the workflow.
