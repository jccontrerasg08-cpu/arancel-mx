# Production hardening and autonomous release design

Date: 2026-08-10

## Objective

Make `arancel-mx` operate autonomously in production while remaining fail-closed. A release is published automatically only when registered official sources are reachable, internally consistent, reconciled, fully parsed, validated, reproducible, and cryptographically verified. Any unexpected difference, parser breakage, source disagreement, checksum mismatch, test failure, or publication failure must block publication and produce a visible GitHub alert.

## Core principles

1. **Fail closed**: uncertainty or inconsistency blocks publication.
2. **No silent fallback**: unexpected source/schema changes are surfaced, not guessed through.
3. **Minimum permissions**: repository default `GITHUB_TOKEN` remains read-only; write permissions are granted only to the exact jobs that need them.
4. **Immutable published data**: published dataset releases are immutable and versioned as `data-YYYY.MM.DD`.
5. **Traceable chain of custody**: every release records the source bytes, source hashes, Git commit, workflow run, artifact identity, validation results, and release asset hashes.
6. **Deterministic logical output**: equal source bytes and equal build inputs produce the same canonical logical dataset and deterministic text/archive artifacts.
7. **No generated datasets in Git history**: release assets remain in GitHub Actions artifacts and GitHub Releases, not committed to `main`.

## Desired operating model

```text
scheduled/manual trigger
        |
        v
source discovery + capture
SNICE / Diputados / DOF
        |
        v
change and identity checks
        |
   +----+----+
   |         |
no change   changed
   |         |
 success     v
          reconciliation
              |
       +------+------+
       |             |
      fail           pass
       |             |
       v             v
 alert + stop     parse/build
                     |
                     v
               canonical validation
                     |
              +------+------+
              |             |
             fail           pass
              |             |
              v             v
          alert+stop    release package
                             |
                             v
                     draft GitHub Release
                             |
                             v
                    upload six assets
                             |
                             v
                     verify published bytes
                             |
                      +------+------+
                      |             |
                     fail           pass
                      |             |
                      v             v
               delete/leave       publish
               draft + alert     immutable
```

A scheduled execution with no meaningful source change exits successfully without creating a new release.

## Workflow architecture

### 1. `ci.yml`

Purpose: offline code-quality and packaging gate for pull requests and pushes.

Required behavior:
- `contents: read`
- Python 3.11
- install development dependencies
- run `python -m pytest -q`
- run `python -m build`
- run `git diff --check`
- no source network access
- no repository writes
- unique job name suitable for a required status check

This workflow becomes the required merge check for `main`.

### 2. `official-data-pipeline.yml`

Purpose: autonomous official-data build, validation, and release orchestration.

Triggers:
- daily scheduled execution
- `workflow_dispatch`

Concurrency:
- one production data pipeline at a time
- later scheduled runs must not race with publication

Stages:
1. offline regression tests
2. resolve build metadata
3. discover registered sources
4. fetch source bytes with strict host/media/size/time boundaries
5. compare source identity to previous published release state
6. stop successfully when there is no meaningful source change
7. reconcile legal/operational evidence
8. parse LIGIE/NICO and consolidated hierarchy sources
9. materialize candidate DuckDB transactionally
10. run canonical database validations
11. export DuckDB/CSV/JSON
12. verify cross-format equivalence
13. create source archive and checksums
14. create draft release
15. upload all six release assets
16. independently verify uploaded assets
17. publish the draft release

Only the publication job receives `contents: write`. All build and validation jobs remain read-only.

### 3. `data-alert.yml` as a reusable alerting workflow or equivalent dedicated alert job

Purpose: create/update GitHub Issues for production data failures.

Permissions:
- `contents: read`
- `issues: write`

Alert identity must be deterministic enough to avoid duplicate issue spam. Failures with the same stage and source category update the existing open issue. A materially different failure opens a new issue.

Issue title format:

```text
[DATA ALERT] <stage>: <short failure category>
```

Issue body includes:
- workflow run URL/ID
- run attempt
- commit SHA
- candidate dataset version
- failing stage
- source/dataset key when applicable
- expected vs observed values
- relevant source URLs
- expected and observed SHA-256 when applicable
- parser/profile/schema/registry versions
- exception/error summary
- publication state: `BLOCKED`

Labels:
- `data-alert`
- `automation`
- `release-blocked`
- stage/source-specific label when useful

Recovery behavior:
- after a later successful production run, matching open alerts receive a recovery comment and are closed automatically

## Change detection

The pipeline must not publish a release merely because the calendar date changed.

A meaningful source change is detected by comparing the current captured-source identity against the previous successfully published release. At minimum compare:
- final official URL
- content SHA-256
- dataset/document role
- source registry identity/version

A change in HTML discovery layout with identical authoritative document bytes does not create a new dataset release unless it changes a required captured source or blocks confident discovery.

Ambiguous source discovery is a hard failure.

## Legal and source reconciliation gate

The existing reconciliation capability must become part of the official build path rather than a separate optional CLI-only step.

Publication is blocked when:
- required legal evidence is missing
- Diputados ledger dates/roles do not have the expected supporting evidence
- SNICE operational documents contradict required legal evidence
- a registered authoritative source disappears unexpectedly
- multiple equally current candidate snapshots cannot be disambiguated
- source roles cannot be classified confidently from the registry

Reconciliation results are persisted in release metadata.

No row is labeled with stronger legal validity than its evidence supports. `observed_snapshot` remains valid when only observation is known. Legal effective dates are populated only when supported by evidence.

## Timestamp semantics

The pipeline must preserve distinct meanings:

- `retrieved_at`: actual timestamp when source bytes were fetched
- `observed_at`: logical observation date for the source snapshot
- `generated_at`: build/release generation timestamp
- `published_at`: official publication date when established
- `effective_from` / `effective_to`: legal validity interval only when established

`generated_at` must no longer be reused as a substitute for `retrieved_at`.

## Release manifest contract

The manifest is extended to include:

- `dataset_version`
- `schema_version`
- `ligie_version`
- `registry_version`
- `registry_sha256`
- `effective_as_of`
- `generated_at`
- `git_commit_sha`
- `github_run_id`
- `github_run_attempt`
- `github_workflow_ref`
- artifact identity when available before final packaging
- row count
- level counts
- reconciliation status/results
- validation status/results
- complete source-document metadata and SHA-256 values
- artifact SHA-256 map

Release publication must be derivable and auditable from this manifest without reconstructing provenance manually from the GitHub UI.

## Release publication sequence

To support immutable GitHub Releases safely:

1. choose candidate tag `data-YYYY.MM.DD`
2. ensure tag/release does not already exist
3. create a draft release targeting the exact validated commit
4. upload exactly:
   - `arancel_mx.duckdb`
   - `arancel_mx.csv`
   - `arancel_mx.json`
   - `manifest.json`
   - `SHA256SUMS`
   - `official-sources.tar.gz`
5. download or query the uploaded assets and verify expected size/hash identity
6. publish the draft
7. verify the resulting release is complete

No existing data release is overwritten. Tag reuse is forbidden.

## GitHub repository settings

### Actions

Keep repository default workflow permissions at:

- **Read repository contents and packages permissions**

Write permissions are declared explicitly per job.

The setting **Allow GitHub Actions to create and approve pull requests** may remain enabled for future maintenance automation, but production release correctness must not depend on automated PR approval. No workflow should self-approve application/data logic changes to bypass review protections.

### Immutable releases

Enable repository release immutability before the autonomous publisher is enabled.

### `main` ruleset

Target the default branch and enforce:
- require pull request before merging
- require CI status check
- require branch to be up to date before merging
- require conversation resolution
- block force pushes
- block branch deletion
- use linear history if the repository chooses squash-only merges

The live official-source build is not required on every pull request because temporary official-site outages must not block ordinary code changes. Offline CI is the merge gate; production source validation is the release gate.

### Merge strategy

Preferred repository policy:
- squash merge enabled
- merge commits disabled
- rebase merge disabled
- automatically delete merged head branches enabled
- auto-merge may be enabled for maintenance PRs after required checks are configured

## Dependency hardening

Library compatibility ranges remain in `pyproject.toml`, but official production dataset builds use a committed exact constraints/lock input so dependency upgrades do not occur silently between scheduled builds.

Add Dependabot coverage for:
- Python dependencies
- GitHub Actions

GitHub Actions references remain pinned to full commit SHAs. Dependabot is responsible for opening reviewed update PRs for those pins.

## HTTP and parser hardening

Required changes:
- all source discovery requests use explicit configured timeouts
- redirects are validated against allowed hosts
- source body size limits are enforced
- declared/inferred media types are validated
- malformed encodings fail explicitly
- migrate deprecated PyMuPDF `fitz` import usage to supported `pymupdf` import behavior
- parser profile ambiguity is a hard failure
- unknown workbook/PDF structural drift opens an alert rather than guessing a parse profile

## `update` command semantics

The CLI must no longer imply state mutation when it only performs a check.

Preferred design:
- keep a read-only check command with explicit naming/behavior
- make state mutation an explicit operation that persists the accepted snapshot only after the required jobs succeed

The production workflow uses the full build/reconciliation pipeline as the source of truth, not a state file updated ahead of successful validation.

## Testing strategy

### Unit tests

Add or extend tests for:
- source change identity calculation
- no-change behavior
- timestamp semantics
- reconciliation blocking behavior
- alert key/deduplication logic
- manifest provenance fields
- release-tag collision handling
- source timeout behavior
- parser structural-drift failure
- immutable publication preconditions

### Integration tests

Use offline fixtures/fakes to simulate:
- unchanged sources
- one valid changed source
- ambiguous current source
- missing legal evidence
- LIGIE/NICO parent mismatch
- malformed workbook layout
- checksum mismatch
- failed release upload verification
- recovered alert

### Workflow contract tests

Static workflow tests verify:
- read-only default permissions
- publication job is the only job with `contents: write`
- alert job is the only job with `issues: write`
- pinned action SHAs
- timeout limits
- concurrency definition
- tests run before network build
- release occurs only after reconciliation and validation
- failure paths invoke alerting

## Failure modes and expected behavior

| Failure | Publication | Workflow | Notification |
|---|---|---|---|
| No source change | none | success | none |
| Official site transient failure | blocked | failure | issue/update |
| Source host/type mismatch | blocked | failure | issue/update |
| New ambiguous snapshot | blocked | failure | issue/update |
| Reconciliation discrepancy | blocked | failure | issue/update |
| Parser/profile drift | blocked | failure | issue/update |
| Canonical validation failure | blocked | failure | issue/update |
| Cross-format mismatch | blocked | failure | issue/update |
| Release asset hash mismatch | blocked | failure | issue/update |
| Existing candidate tag | blocked | failure | issue/update |
| Successful changed dataset | immutable release | success | close matching recovered alerts |

## Security boundary

Untrusted pull-request code must never execute with production write permissions or production secrets.

Avoid `pull_request_target` for code execution. Scheduled/manual production publication runs only trusted code from the protected default branch.

No external PAT is required for normal publication if `GITHUB_TOKEN` permissions are sufficient. Add secrets only when a capability cannot be achieved safely with the built-in token.

## Completion criteria

The hardening project is complete when all of the following are true:

1. `main` offline CI is green and required.
2. production pipeline runs from trusted `main`.
3. unchanged sources create no release.
4. valid changed sources produce a fully verified immutable release automatically.
5. any discrepancy or failure blocks release and creates/updates a GitHub Issue.
6. recovery closes the corresponding alert automatically.
7. the manifest contains complete source/build/release provenance.
8. release assets can be verified independently with checksums and GitHub immutable-release verification.
9. no production dataset asset is committed into Git history.
10. documentation accurately describes the automated behavior and failure semantics.
