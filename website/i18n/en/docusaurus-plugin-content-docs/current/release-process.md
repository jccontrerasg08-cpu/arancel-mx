# Release process

`arancel-mx` uses an autonomous fail-closed pipeline to build and publish official snapshots. The production workflow is **Official data pipeline**, defined in [`.github/workflows/official-data-pipeline.yml`](https://github.com/jccontrerasg08-cpu/arancel-mx/blob/main/.github/workflows/official-data-pipeline.yml), and runs daily at cron `17 11 * * *` in addition to supporting `workflow_dispatch`.

> Automatic publication should only be enabled in production after release immutability and `main` protections are enabled. Manual `workflow_dispatch` uses `publish=false` by default so a dry run can execute without mutations.

## 1. Tests and reproducible environment

Before external source access, `build-and-verify` installs the environment constrained by `requirements/production-build.txt` and runs `python -m pytest -q`. The stable merge check is `CI / test`.

Public package compatibility remains declared in `pyproject.toml`; the official build instead uses exact versions so scheduled execution does not silently change dependencies.

## 2. Official source capture

The end-to-end official dataset build is available through `scripts/build_official_dataset.py`; production uses `scripts/run_official_pipeline.py` to add comparison with the previous release and structured diagnostics.

Every registered snapshot is downloaded with source identity, SHA256, and `retrieved_at`. **`retrieved_at` means actual fetch time**, not `generated_at`.

`generated_at` identifies when the candidate/release was generated. Keeping both values separate avoids assigning the workflow's generation time to the source document.

## 3. Legal reconciliation gate

The registered Chamber of Deputies ledger is reconciled against DOF evidence and registered SNICE operational sources before publication. A legal discrepancy, missing required DOF evidence, snapshot ambiguity, parser failure, inconsistent checksum, or invalid validation result blocks the pipeline.

Reconciliation does not turn a technical observation into a legal opinion. The project preserves evidence and detects inconsistencies; it **does not constitute legal advice**.

## 4. Parsing, normalization, and validation

Captured bytes are processed with offline parsers. The candidate is materialized in DuckDB and validated before export. Gates include:

- HS2 → HS4 → HS6 → MX8 tariff fraction → NICO10 hierarchy;
- no duplicates or missing parents;
- coherent time intervals;
- valid public rates and metadata;
- complete provenance;
- publishable legal reconciliation.

If any gate fails, there is no path to the publisher job.

## 5. `no_change` and change detection

The pipeline downloads `manifest.json` from the latest valid release and compares registered source identity.

- No identity change: `no_change`, green run, publisher `skipped`, no tag/release.
- Changed sources with all gates passing: `built`, verified bundle can proceed to publication.
- Any failing gate: `failed`, publication blocked and diagnostics available to the notifier.

## 6. Manifest schema v2 and provenance

`manifest.json` uses `schema_version: "2"`, also referred to as **schema v2**. In addition to version, counts, hashes, and sources, the manifest records execution provenance.

Relevant fields include `generated_at`, `registry_version`, `registry_sha256`, `git_commit_sha`, `github_run_id`, `github_run_attempt`, `github_workflow_ref`, and `github_artifact_name`.

## 7. Exact publication contract

A valid build produces exactly **six assets**:

```text
release/
├── arancel_mx.duckdb
├── arancel_mx.csv
├── arancel_mx.json
├── manifest.json
├── SHA256SUMS
└── official-sources.tar.gz
```

The five files other than `SHA256SUMS` must be covered by checksums. `official-sources.tar.gz` preserves captured snapshots and `source_capture.json` needed to audit the build.

Before any GitHub Release mutation, `verify_publication_bundle()` requires the exact six-asset directory and verifies manifest/schema/provenance and hashes.

### Artifact attestation

When a changed verified build reaches the real `publish` job, GitHub Actions creates one SLSA provenance **artifact attestation** over those same six public files using first-party `actions/attest` and GitHub OIDC.

Before the publisher executes, each subject is verified against this repository and the exact signer workflow:

```bash
gh attestation verify arancel_mx.duckdb \
  --repo jccontrerasg08-cpu/arancel-mx \
  --signer-workflow jccontrerasg08-cpu/arancel-mx/.github/workflows/official-data-pipeline.yml
```

The same verification form applies to `arancel_mx.csv`, `arancel_mx.json`, `manifest.json`, `SHA256SUMS`, and `official-sources.tar.gz`.

The layers answer different questions:

- `SHA256SUMS` verifies local release-file digests.
- `manifest.json` records dataset/source/registry/validation/execution provenance.
- GitHub artifact attestation cryptographically links subject digests to the GitHub Actions workflow identity that produced and authorized them for publication.

Artifact attestation **is not a legal signature** over Mexican official documents. It does not replace DOF/Diputados evidence, source provenance, or blocking legal reconciliation.

A9 status until the next legitimate changed release is independently verified: **implemented / CI-verified; live attestation verification pending the next legitimate changed release**. `data-2026.08.11` predates A9 and is not retroactive attestation evidence.

## 8. Automatic publication and immutable release

The `publish` job can execute only when:

1. `build-and-verify` succeeded;
2. its output is exactly `built`;
3. the ref is `refs/heads/main`;
4. the run is scheduled or a trusted `workflow_dispatch` uses `publish=true`.

The publisher downloads the exact artifact `arancel-mx-${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}`, runs `verify_publication_bundle()` again, generates/verifies the six-asset attestation, and only then creates a **draft** GitHub Release for tag `data-YYYY.MM.DD`.

The six assets are uploaded to the draft and remotely verified by size and digest when GitHub provides a digest; otherwise they are downloaded again and SHA256 is recomputed. Only after that does the draft become public, followed by another read-back verification.

The policy is **immutable**: an existing tag or release is never overwritten.

### Same-date second change

If a second valid change occurs on the same date and `data-YYYY.MM.DD` already exists, the system does not overwrite that identity. It fails with category `release_tag_collision`. This **same-date** collision blocks publication and becomes an operational alert.

## 9. Failures, GitHub Issue, and recovery

**Any failure blocks publication.** Main steps write structured JSON diagnostics before returning a non-zero code. The workflow extracts bounded secret-free messages and then explicitly fails the job.

The `notify` job is the only job with `issues: write`:

- failed build: creates or updates a deterministic **GitHub Issue** keyed by stage + failure category;
- failed publish, including attestation creation/verification failure: creates or updates the corresponding Issue;
- later healthy run: performs **recovery**, comments, and closes automation-generated alerts;
- `no_change` with publisher `skipped` explicitly counts as healthy recovery.

User Issues without the hidden automation marker are never closed by recovery.

## 10. Permission boundaries

The workflow has global `contents: read`. Build stays read-only. Only `publish` receives `contents: write`; for A9 it also receives `attestations: write` and `id-token: write`. Only `notify` receives `issues: write`. No PAT, `write-all`, `artifact-metadata: write`, or `pull_request_target` is used.

Binaries, DuckDB databases, official snapshots, and release bundles are not written to Git history.

## Entrypoint compatibility

`scripts/build_official_dataset.py` remains the public build entrypoint. Production automation lives only in `.github/workflows/official-data-pipeline.yml`, so there are not two competing dataset schedules.
