# Official sources

`arancel-mx` only admits documents to the official build when they are discovered through the versioned source registry and allowed domain adapters. The existence of a snapshot on an official page is not enough to make it publishable: identity, provenance, and legal reconciliation must pass the pipeline gates.

## Domains and roles

- `diputados.gob.mx`: registered LIGIE ledger, consolidated text, reforms, and related legislative documents.
- `dof.gob.mx`: primary evidence of publication, amendment, and applicable legal validity.
- `snice.gob.mx`: structured LIGIE, NICO, national-note, indicator, and related datasets from the Ministry of Economy.
- `ventanillaunica.gob.mx`: **independent operational cross-check under characterization**. VUCEM is not part of `source_registry`, is not `authoritative_for_tariff`, and is not a `publication_gate` during this phase.

The separation is intentional. An official source may be useful for structure, discovery, or cross-checking without automatically becoming the legal or tariff authority for every field.

## Versioned registry

`src/arancel_mx/sources/source_registry.json` defines each source set, `registry_version`, canonical page, source role, legal/discovery authority, expected media profiles, and classification rules.

The registry acts as both an allowlist and a component of reproducible provenance. Changing it changes which documents may enter the pipeline, so registry changes must be reviewable and backed by offline tests/fixtures.

VUCEM **is not added to the registry simply because a usable URL pattern exists**. Before any incorporation proposal, a separate characterization must cover 100+ Mexican tariff fractions, review coverage, structural variants, correspondence with the canonical dataset, and evidence of update lag. See the repository's VUCEM characterization documentation.

## Allowlist and discovery

Production adapters accept only registered official hosts. Out-of-policy redirects, unexpected extensions, auxiliary pages, zero candidates, or multiple equally valid candidates fail closed instead of selecting a source through weak heuristics.

Each source role has explicit expectations. Proposal or analytical-indicator pages may provide context or observations, but they do not automatically replace applicable legal evidence.

The VUCEM characterization tool uses a separate research boundary and does not feed the official build. Its results remain diagnostic until a future, separately reviewed proposal changes that contract.

## Capture identity

Every production download preserves at least final URL, SHA256, size, media type, provenance, and `retrieved_at`.

`retrieved_at` is the actual HTTP retrieval time. It is not the dataset-generation time or a legal effective date. The manifest separately contains `generated_at` for the execution that produced the candidate/release.

A parse can only be reused when captured identity and relevant parser/schema/registry versions remain compatible.

## Diputados ledger + DOF reconciliation

The registered Chamber of Deputies ledger anchors which legal documents the build must be able to explain. The pipeline reconciles that ledger with **DOF** evidence and registered SNICE sources.

Reconciliation is a **blocking gate** before publication. The build is blocked when an expected legal entry lacks sufficient DOF evidence, documentary identities do not agree, or a material **discrepancy** cannot be explained by registered rules.

Priority is never silently guessed: legal publication/text governs validity while operational datasets provide usable structure. Material discrepancies remain visible in diagnostics and block **publication**.

This does not turn the repository into legal advice. The system verifies consistency between observed evidence and registered rules; final legal validity depends on the applicable official publications.

## VUCEM as a pre-registry cross-check

The VUCEM Tariff Classifier is studied through `scripts/characterize_vucem.py` using the known individual-page pattern. Reports preserve:

```text
source_role = independent_operational_cross_check
authoritative_for_tariff = false
publication_gate = false
```

The sample is drawn from canonical `fraccion8` CSV rows and distributed across chapters. The tool records coverage, errors, code presence, description correspondence, and a structural `schema_fingerprint`.

`registry_review_ready=true` only means that at least 100 pages were retrieved successfully and a human review can begin. **It does not add VUCEM to `source_registry` or change the authority hierarchy.** Update lag requires repeated observations around real changes confirmed by registered sources.

## Changes and no-op behavior

After production sources are captured and reconciled, their identity is compared with the latest published `manifest.json`. When nothing changed, the pipeline returns `no_change`, finishes green, and does not create a new release. When sources changed, publication still requires every legal/parser/validation gate to pass.

Changes observed only by the VUCEM characterization process do not alter this result during the pre-registry phase.

## Preserved evidence

A valid release includes `official-sources.tar.gz`, which preserves captured official bytes and `source_capture.json`. Hashes make it possible to reconstruct the exact snapshots observed by a build even if the official page changes later.

VUCEM characterization reports are separate research artifacts and are not automatically added to the six-asset production release contract.

## Offline fixtures

Pull-request tests use small sanitized fixtures under `tests/fixtures/` and do not depend on DOF, Diputados, SNICE, or VUCEM availability at test time. Every parser, reconciliation, or source-registry change should include a reproducible fixture or equivalent synthetic construction.
