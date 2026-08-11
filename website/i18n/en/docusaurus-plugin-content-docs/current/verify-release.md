# Verify a release

Verification should work for an external consumer without trusting an editable repository checkout.

## 1. Confirm the six assets

A valid data release must contain exactly:

```text
arancel_mx.duckdb
arancel_mx.csv
arancel_mx.json
manifest.json
SHA256SUMS
official-sources.tar.gz
```

## 2. Verify SHA256SUMS

On systems with `sha256sum`:

```bash
sha256sum -c SHA256SUMS
```

Every listed file must validate. A missing asset, an unexpected asset in the six-file contract, or a digest mismatch requires investigation before consuming the release.

## 3. Inspect manifest.json

At minimum, check:

```text
schema_version
dataset_version
generated_at
registry_version
registry_sha256
git_commit_sha
github_run_id
github_run_attempt
github_workflow_ref
github_artifact_name
source_identity
reconciliation
```

Publishable reconciliation state and source identity must correspond to the bundle being verified.

## 4. Open DuckDB as a consumer

For example:

```sql
SELECT COUNT(*) FROM arancel_mx;
SELECT level, COUNT(*)
FROM arancel_mx
GROUP BY level
ORDER BY level;
```

For a deeper independent audit, compare a sample keyed by `record_id` across DuckDB, CSV, and JSON.

## 5. Inspect preserved official sources

`official-sources.tar.gz` preserves captured documents and capture metadata. Archive hashes must agree with the source identity recorded by the manifest/capture metadata.

## 6. GitHub artifact attestations

Releases produced after the A9 attestation layer is integrated may include GitHub-verifiable build provenance. For an asset that has an attestation:

```bash
gh attestation verify arancel_mx.duckdb \
  --repo jccontrerasg08-cpu/arancel-mx \
  --signer-workflow jccontrerasg08-cpu/arancel-mx/.github/workflows/official-data-pipeline.yml
```

Repeat for every published subject. An attestation proves build/workflow provenance, not the legal correctness of the underlying data.

Do not retroactively attribute attestations to releases created before the mechanism was integrated.
