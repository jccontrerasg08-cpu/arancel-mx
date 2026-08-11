# Production certification

This runbook documents the repository's controlled production-certification workflow and the evidence required before its GitHub write boundaries are considered healthy.

> The certification workflow is intentionally separate from the official tariff-data pipeline. It must never publish a production `data-*` release or create a production `[DATA ALERT]` issue.

## Certified live baseline

The release and Issue write boundaries were successfully exercised from protected `main` on 2026-08-11 UTC.

- Workflow: `Production certification`
- Run: `31450616908`
- Commit: `a14c57ee3aeeb982e6aa7077ae1b34582585db8b`
- Overall conclusion: `success`
- `offline`: `success`
- `release-boundary`: `success`
- `issue-boundary`: `success`
- Temporary release tag: `certification-31450616908`
- Final release state: absent
- Final tag/ref state: absent
- Certification Issue: `#28`, `[CERTIFICATION ALERT] 31450616908`, closed
- Production release `data-2026.08.10`: unchanged

This evidence certifies the isolated GitHub write boundaries only. It does not replace the official-source, legal-reconciliation, release-integrity, timestamp, or artifact-attestation gates documented elsewhere in the repository.

## Safety boundaries

The workflow is manual-only (`workflow_dispatch`) and runs from trusted `main`.

Its namespaces are deliberately isolated:

```text
Temporary release/tag: certification-<github-run-id>
Certification Issue:   [CERTIFICATION ALERT] <github-run-id>
Production release:    data-YYYY.MM.DD
Production alert:      [DATA ALERT] ...
```

The certification helpers reject production namespaces. A certification release remains a draft/prerelease for its entire lifetime and is deleted after verification. A certification Issue is closed and retained as an auditable trace.

Permissions are job-scoped:

```text
offline            contents: read
release-boundary   contents: write
issue-boundary     contents: read + issues: write
```

The workflow uses the built-in `github.token`; no external PAT is required.

## Manual dispatch

In GitHub:

1. Open **Actions**.
2. Select **Production certification**.
3. Choose **Run workflow**.
4. Select branch **main**.
5. Run the workflow.

Do not dispatch the live mutation workflow from a pull-request branch.

Before dispatch, verify:

```text
main is protected
required check `test` is green on current main
no open production DATA ALERT is attributable to current main
no certification draft/tag already exists for the new run
workflow permissions still match this runbook
```

## Expected successful lifecycle

The release boundary performs this lifecycle:

```text
preflight for existing certification resources
create temporary draft/prerelease
persist exact temporary release ID locally
upload certification-proof.json
verify asset metadata/digest
DELETE the exact draft by release ID
DELETE the temporary certification tag/ref if present
verify release absence by ID and listing
verify tag/ref absence
always-run cleanup repeats the absence check
```

The Issue boundary creates an isolated certification Issue, verifies it, records completion, and closes it. The Issue remains closed as audit evidence.

A successful run must finish with all three jobs green and these postconditions:

```text
0 remaining certification drafts for the run
0 remaining certification tags/refs for the run
1 closed [CERTIFICATION ALERT] Issue for the run
0 new data-* tags
0 production releases modified by certification
main SHA unchanged by certification
```

If any cleanup postcondition fails, stop. Remove only the exact certification resource after independently checking its run ID and namespace. Never delete or edit a `data-*` release while repairing certification cleanup.

## Inspecting evidence

For the certified baseline, inspect:

```text
Actions → Production certification → run 31450616908
Issues  → #28 [CERTIFICATION ALERT] 31450616908
Releases → confirm no Production certification 31450616908 draft remains
Tags     → confirm certification-31450616908 is absent
```

The release-boundary log must contain a final result equivalent to:

```json
{
  "release_absent": true,
  "status": "passed",
  "tag": "certification-31450616908",
  "tag_absent": true
}
```

The Issue-boundary result must identify the certification Issue with `state: "closed"`.

## Package artifact smoke certification

Build the distributions first:

```bash
python -m build
```

Then exercise both artifacts in isolated virtual environments outside the repository checkout:

```bash
python scripts/certify_package_install.py dist/*.whl
python scripts/certify_package_install.py dist/*.tar.gz
```

Each clean install verifies:

```text
import arancel_mx
python -m arancel_mx --help
arancel-mx --help
packaged sources/source_registry.json is present
```

CI runs the same wheel and sdist smoke boundary.

## Public bundle verification

A public bundle is valid only when it contains exactly:

```text
arancel_mx.duckdb
arancel_mx.csv
arancel_mx.json
manifest.json
SHA256SUMS
official-sources.tar.gz
```

Run the independent certification layer against a prepared release directory:

```bash
python - <<'PY'
from pathlib import Path
from arancel_mx.certification import certify_bundle

report = certify_bundle(Path("out/release"))
print(report)
assert report.passed
PY
```

This checker validates the exact asset set, checksums, source archive safety and source identities, and CSV/JSON logical equivalence. DuckDB has its own consumer-contract and minimum-version probe.

For the documented minimum DuckDB compatibility boundary:

```bash
python scripts/check_duckdb_compat.py out/release/arancel_mx.duckdb
```

The repository CI additionally executes this probe in an isolated DuckDB `1.1.0` environment.

## Routine verification commands

Before merging certification-related changes:

```bash
python -m pytest -q
python -m build
git diff --check
```

A certification workflow PR must also show that:

```text
it is based on current protected main
GitHub API/action assumptions were rechecked against official documentation when they could have changed
least-privilege permissions are preserved
external Actions remain full-SHA pinned
no credentials or generated production datasets are committed
cleanup is fail-closed and independently verified
live mutation happens only after merge from trusted main
```

## Failure recovery

If a live certification run fails:

1. Read the exact job log before changing code.
2. Check Releases, Tags, and Issues independently through GitHub, because list endpoints can be eventually consistent.
3. Identify the exact `certification-<run-id>` resource before cleanup.
4. Never infer ownership from a partial name or delete a production `data-*` release.
5. Add a RED test reproducing the live failure before implementing a fix.
6. Merge the fix only after the normal repository gate passes.
7. Remove any legacy orphan created by code that predates reliable persisted cleanup state.
8. Re-run `Production certification` from protected `main` and require all postconditions again.

## Scope of this certification

The successful live run proves that the repository can safely exercise and roll back its isolated GitHub release-write boundary and can create/close an isolated Issue with least-privilege job permissions.

It does **not** by itself prove:

- that an official tariff-source update exists;
- that legal reconciliation will pass for a future source change;
- that a future production release will be immutable;
- that artifact attestations are configured and verifiable;
- or that every external official source is currently reachable.

Those are separate production gates and must be certified independently.
