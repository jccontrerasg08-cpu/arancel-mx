# Supply-Chain and Timestamp Certification Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Complete the production-certification spec by proving artifact provenance and release-integrity verification while making timestamp semantics explicit and testable without weakening the existing data pipeline.

**Architecture:** Extend the existing official-data workflow only at provenance boundaries. Artifact attestations supplement, rather than replace, SHA-256 and manifest verification. Keep the existing `generated_at` field for schema compatibility and define it consistently as the build-start generation timestamp, while `retrieved_at` remains the actual per-source fetch time.

**Tech Stack:** GitHub Actions artifact attestations, GitHub CLI verification, existing manifest schema v2, Python/pytest, existing release package functions.

## Global Constraints

- Do not replace `SHA256SUMS`, manifest artifact hashes, or remote release verification with attestations.
- Attestation jobs receive only `contents: read`, `id-token: write`, and `attestations: write`.
- All GitHub Actions are pinned to full commit SHAs.
- `generated_at` remains a manifest/schema-v2 field; this plan does not rename or remove it.
- `generated_at` is defined as the timestamp captured at build start for the candidate run.
- `retrieved_at` remains the actual timestamp after each official source body is fetched.
- Therefore a healthy live build may have `generated_at <= retrieved_at`; the timestamps are intentionally different semantics.
- No legal `published_at`/`effective_*` timestamp may be inferred from workflow time.
- Immutable-release verification is performed only against a newly automated immutable release; the historical pre-hardening `data-2026.08.10` release is not rewritten.

---

### Task 1: Lock timestamp semantics with tests and documentation

**Files:**
- Create: `tests/release/test_timestamp_semantics.py`
- Modify: `docs/data-model.md`
- Modify: `README.md`
- Modify: `README.en.md`
- Modify only if existing behavior contradicts the chosen contract: `src/arancel_mx/release/metadata.py`

**Interfaces:**
- Consumes: manifest metadata and source-document metadata.
- Produces: documented invariant that `generated_at` is build-start time and `retrieved_at` is actual source fetch time.

- [ ] **Step 1: Add RED documentation/metadata contract test**

Test a manifest fixture where `generated_at` precedes source `retrieved_at` and assert verification accepts it. Add a separate assertion that documentation contains the phrases `build start`/`inicio de construcción` for `generated_at` and `actual fetch time`/`captura real` for `retrieved_at`.

- [ ] **Step 2: Run targeted test**

Run: `python -m pytest tests/release/test_timestamp_semantics.py -q`

Expected: at least the documentation assertion fails until docs are updated. If manifest verification already accepts the ordering, do not modify code.

- [ ] **Step 3: Update semantics consistently**

Document:

```text
generated_at = build-start timestamp for the candidate/release run
retrieved_at = actual per-source fetch timestamp
published_at = official publication time only when supported by evidence
effective_from/effective_to = legal validity only when supported by evidence
```

Do not add an assertion that `generated_at` must equal or follow `retrieved_at`.

- [ ] **Step 4: Verify**

```bash
python -m pytest tests/release/test_timestamp_semantics.py tests/release -q
python -m pytest -q
python -m build
git diff --check
```

- [ ] **Step 5: Commit**

```bash
git add tests/release/test_timestamp_semantics.py docs/data-model.md README.md README.en.md src/arancel_mx/release/metadata.py
git commit -m "docs: lock release timestamp semantics"
```

Stage `metadata.py` only if a failing test proved a real contradiction.

### Task 2: Add attestation generation for verified build artifacts

**Files:**
- Modify: `.github/workflows/official-data-pipeline.yml`
- Create: `tests/automation/test_artifact_attestation_contract.py`
- Modify: `docs/production-certification.md`

**Interfaces:**
- Consumes: the already verified Actions artifact produced by `build-and-verify`.
- Produces: GitHub artifact attestation bound to the exact repository/workflow/commit/event.

- [ ] **Step 1: Re-verify GitHub's current attestation action and permissions**

Use official GitHub documentation and resolve the current stable tag for `actions/attest-build-provenance` to a full commit SHA. Record both tag and SHA in the PR double-check evidence.

GitHub's current documented minimum permissions are:

```yaml
permissions:
  contents: read
  id-token: write
  attestations: write
```

- [ ] **Step 2: Add RED workflow contract test**

Assert that the attestation step/job:

```text
runs only after verified build output exists
has no contents: write
has attestations: write
has id-token: write
uses a full 40-character SHA
never runs for a failed or no-change build
```

- [ ] **Step 3: Add the minimal attestation boundary**

Attest the release bundle/checksum artifact that consumers can download and verify. Do not attest unrelated test logs. Keep publication logic unchanged.

- [ ] **Step 4: Verify offline workflow contract**

```bash
python -m pytest tests/automation/test_artifact_attestation_contract.py tests/automation -q
python -m pytest -q
python -m build
git diff --check
```

- [ ] **Step 5: Commit**

```bash
git add .github/workflows/official-data-pipeline.yml tests/automation/test_artifact_attestation_contract.py docs/production-certification.md
git commit -m "ci: attest verified data artifacts"
```

### Task 3: Verify attestation on a publish=false run

**Files:**
- No production code changes unless verification exposes a reproducible workflow bug.
- Modify: `docs/production-certification.md` only to record final operator commands.

**Interfaces:**
- Produces: evidence that a verified dry-run artifact can be checked independently with GitHub CLI.

- [ ] **Step 1: Run a new trusted-main `Official data pipeline` with `publish=false`**

Require `build-and-verify == success` and `publish == skipped`.

- [ ] **Step 2: Download the attested artifact locally**

Use the run's exact artifact name from manifest/workflow outputs.

- [ ] **Step 3: Verify provenance with GitHub CLI**

Run the current official form of:

```bash
gh attestation verify <downloaded-artifact> --repo jccontrerasg08-cpu/arancel-mx
```

Expected: verification succeeds and identifies the expected repository/workflow/commit.

- [ ] **Step 4: Verify no production mutation occurred**

Require no new `data-*` release/tag and no production alert Issue for the successful dry-run.

- [ ] **Step 5: Document exact successful command and evidence fields**

Record what users should compare: repository, workflow identity, commit SHA, artifact subject digest. State explicitly that attestation proves build provenance, not legal correctness of tariff content.

### Task 4: Verify the first new immutable automated release

**Files:**
- Modify: `docs/production-certification.md`
- Modify: `README.md`
- Modify: `README.en.md`

**Interfaces:**
- Consumes: first post-hardening automated release whose GitHub API/UI reports immutable.
- Produces: operator-verifiable release-integrity procedure.

- [ ] **Step 1: Wait for or trigger a valid new-date production publication through the existing trusted workflow**

Do not reuse an existing `data-YYYY.MM.DD` tag and do not manually edit an existing release.

- [ ] **Step 2: Confirm immutable state from GitHub**

Require the new release to report immutable in GitHub UI/API before documenting success.

- [ ] **Step 3: Verify release and each local asset**

Use current GitHub CLI commands documented by GitHub:

```bash
gh release verify RELEASE-TAG
gh release verify-asset RELEASE-TAG arancel_mx.duckdb
gh release verify-asset RELEASE-TAG arancel_mx.csv
gh release verify-asset RELEASE-TAG arancel_mx.json
gh release verify-asset RELEASE-TAG manifest.json
gh release verify-asset RELEASE-TAG SHA256SUMS
gh release verify-asset RELEASE-TAG official-sources.tar.gz
```

Expected: every verification succeeds.

- [ ] **Step 4: Verify next unchanged run publishes nothing**

Run or observe the next execution with unchanged source identities and require `status == no_change`, no new release, and no new `data-*` tag.

- [ ] **Step 5: Update public verification docs**

Document release-integrity commands only after they have succeeded against the new immutable release.

- [ ] **Step 6: Final verification**

```bash
python -m pytest -q
python -m build
git diff --check
```

- [ ] **Step 7: Commit documentation evidence**

```bash
git add docs/production-certification.md README.md README.en.md
git commit -m "docs: document verified immutable release integrity"
```
