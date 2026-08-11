# Data model

## Identifiers

Source documents and canonical records receive deterministic identifiers derived from stable attributes. SHA256 hashes identify captured bytes; a URL by itself does not identify a documentary version.

## Tariff hierarchy

Supported levels are `hs2`, `hs4`, `hs6`, `fraccion8`, and `nico10`. Each code preserves its parent components. A Mexican tariff fraction requires its active HS6 parent and a NICO requires its active tariff fraction within the same LIGIE version.

## Tariff-rate representation

Import (`IGI`) and export (`IGE`) rates preserve original text, a normalized type, and a numeric value only when appropriate. Types include ad valorem, exempt, prohibited, specific, compound, and unknown rates. Descriptive HS levels do not inherit rates.

## Validity and observation times

`effective_from` and `effective_to` represent known legal intervals. `observed_at`, `retrieved_at`, `published_at`, `updated_at`, and `generated_at` are not interchangeable.

- `retrieved_at`: **actual fetch time**, when the pipeline actually retrieved official snapshot bytes.
- `generated_at`: time when the reproducible candidate/release was generated.
- `published_at`: publication date/time only when supplied by the source or evidence.
- `effective_from` / `effective_to`: known legal validity interval.

Observing or downloading a document does not justify inventing its publication or effective date. Keeping `retrieved_at` separate from `generated_at` prevents a workflow timestamp from becoming a false property of the source.

## Documentary provenance

Each canonical record identifies a primary source and can include additional evidence. Provenance preserves authority, URL, hash, documentary role, source role, and source-registry reference. Proposals and analytical indicators are not presented as current legal tariffs.

Captured identity remains linked to the registry version and the bytes used by the build so published content can be audited even if an official URL later changes.

## Public manifest schema v2

The public release uses `schema_version: "2"`. The manifest separates dataset metadata, source identity, reconciliation, and GitHub Actions provenance.

Relevant provenance fields include:

```text
schema_version
registry_version
registry_sha256
git_commit_sha
github_run_id
github_run_attempt
github_workflow_ref
github_artifact_name
generated_at
```

`registry_sha256` fixes the identity of the source registry used. `github_run_id`, `github_run_attempt`, `github_workflow_ref`, and `github_artifact_name` link a release to the exact Actions artifact that was validated.

## Internal DuckDB and distributable DuckDB

The internal warehouse uses a broader schema for capture, staging, and reproducible construction. Operational tables include `source_registry`, `source_discovery_run`, `source_discovery_item`, `source_capture`, `staging_arancel_row`, and `arancel_quarantine`, in addition to canonical tables.

The public `arancel_mx.duckdb` file is not a complete copy of that warehouse. The exporter creates a new distributable DuckDB and copies only canonical or public-audit tables. The minimum consumer-certification contract includes:

```text
source_document
hs_code
tariff_fraction
nico
tariff_rate
canonical_record
record_provenance
dataset_release
arancel_mx  (view)
```

Additional public tables/views for NICO versions/amendments, national notes, and indicators may be included when they belong to the distributable model.

`source_registry` **is not embedded in the public DuckDB**. The exact registry identity used to build a release is preserved in `manifest.json` through `registry_version` and `registry_sha256`, and in corresponding release metadata. This prevents operational pipeline state from being confused with the public dataset-consumption contract.

The public `arancel_mx` view exposes codes, description, hierarchy, unit, rates, validity, version, current state, and verifiable provenance. Column order is checked against the canonical `PUBLIC_COLUMNS` contract.

### Minimum DuckDB compatibility

The package declares `duckdb>=1.1`. CI protects that promise with an executed test rather than documentation alone: it first generates an `arancel_mx.duckdb` using the current production exporter, then opens that same file read-only in an isolated environment with `duckdb==1.1.0`.

The probe queries the `arancel_mx` view and `dataset_release`. If a future builder upgrade produces a database that 1.1.0 can no longer consume, `CI / test` fails before integration. The minimum supported version should only change through an explicit reviewed change backed by executed evidence.

## `dataset_release.release_metadata_json`

`dataset_release.release_metadata_json` preserves **internal release provenance**. It is internal materialization/release-traceability metadata, not a column in the public `arancel_mx` tabular contract.

It may preserve information needed to audit a build, such as manifest version, registry identity, commit, and execution metadata. The public source of truth for external consumers remains the verified release bundle and its `manifest.json`; the internal JSON helps reconstruct how the warehouse reached that state.

## Separation between evidence, data, and release

The model distinguishes three layers:

1. captured evidence with identity and `retrieved_at`;
2. normalized/reconciled records with validity and provenance;
3. release metadata with `generated_at`, schema/provenance, and artifact hashes.

This separation allows the same observed snapshot to be processed deterministically without attributing timestamps or legal states inferred only from build time.
