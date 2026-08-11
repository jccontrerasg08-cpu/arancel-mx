# A9 Build Provenance Attestations Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add GitHub/Sigstore SLSA provenance attestations for exactly the six public `arancel-mx` release assets and verify those attestations against the exact repository and signer workflow before a production release may be published.

**Architecture:** Keep attestation creation entirely inside the existing trusted `publish` job of `.github/workflows/official-data-pipeline.yml`. The job downloads the already-verified Actions artifact, independently verifies the six-file bundle, creates one multi-subject provenance attestation with `actions/attest`, verifies each local subject with `gh attestation verify`, and only then enters the existing immutable release publisher. Static policy tests in `tests/test_official_dataset_workflow.py` enforce subject identity, full-SHA pinning, least privilege, ordering, and dry-run isolation; `docs/release-process.md` explains consumer verification without changing the six-asset release contract.

**Tech Stack:** GitHub Actions, `actions/attest` v4.2.1 pinned to `508db95dd578ae2727ebd6217d5ba78e4fbda05d`, GitHub OIDC, GitHub artifact attestations/Sigstore, GitHub CLI `gh attestation verify`, pytest, existing `arancel_mx.release.verify_publication_bundle`.

## Global Constraints

- Baseline implementation starts from protected `main` at or after `244145e63fc1e177e946ecb954877e5c3179fdfe`.
- Re-verify the current official `actions/attest` tag and full SHA immediately before opening the implementation PR. If `v4.2.1` no longer resolves to `508db95dd578ae2727ebd6217d5ba78e4fbda05d`, stop and update this plan/spec explicitly before implementation.
- Public release contract remains exactly: `arancel_mx.duckdb`, `arancel_mx.csv`, `arancel_mx.json`, `manifest.json`, `SHA256SUMS`, `official-sources.tar.gz`.
- No Actions artifact ZIP is an attestation subject and no seventh GitHub Release asset is added.
- Workflow-level permissions remain `contents: read`.
- `build-and-verify` remains `contents: read` only.
- `notify` retains only its existing `contents: read` + `issues: write` boundary.
- Only `publish` receives `contents: write`, `attestations: write`, and `id-token: write`.
- Do not add a PAT, external signing key, KMS secret, `artifact-metadata: write`, SBOM attestation, custom predicate, or external signing service.
- The attestation action must use the default SLSA build provenance mode. Do not set `predicate-type`, `predicate`, `predicate-path`, or `sbom-path`.
- The attestation must identify exactly six explicit newline-delimited `out/release/<asset>` paths. Do not use a glob.
- `gh attestation verify` must enforce both `--repo jccontrerasg08-cpu/arancel-mx` and `--signer-workflow jccontrerasg08-cpu/arancel-mx/.github/workflows/official-data-pipeline.yml`.
- Attestation creation and verification must occur after `Independently verify publication bundle` and before `Publish immutable verified release`.
- Attestation and verification steps must not use `continue-on-error`; any failure blocks publication.
- Existing `publish` job condition remains unchanged so `workflow_dispatch` with `publish=false` skips the entire signing/publication boundary.
- Do not alter source capture, source registry, legal reconciliation, parsing, materialization, schema, row counts, tariff values, release naming, data-alert identities, or `scripts/publish_release.py` in A9.
- The existing real release `data-2026.08.11` was published before A9 and is not retroactive A9 evidence. Live certification requires the next legitimate changed release after the A9 implementation is merged.
- Every PR follows the repository double-check contract: current main, approved spec, official upstream facts, RED/GREEN evidence, full tests, build, DuckDB 1.1.0 probe, wheel/sdist smoke, whitespace, diff, secrets/generated-file scan, permissions and review-thread check.

---

## Planned file changes

```text
.github/workflows/official-data-pipeline.yml
    Add publish-job signing permissions, one pinned multi-subject attestation step,
    and fail-closed verification of all six subjects before publisher execution.

tests/test_official_dataset_workflow.py
    Extend the existing official-pipeline policy tests. This remains the single
    workflow contract test file for official-data-pipeline.yml.

tests/test_autonomous_documentation.py
    Extend existing documentation contract assertions for attestation verification.

docs/release-process.md
    Document the three provenance/integrity layers and exact consumer verification command.
```

No new Python production module is required. A9 is a workflow supply-chain boundary, not a second release implementation.

### Task 1: Add RED workflow policy tests for the A9 trust boundary

**Files:**
- Modify: `tests/test_official_dataset_workflow.py`

**Interfaces:**
- Consumes: current `_workflow()` and `_job_block()` helpers already used by official pipeline tests.
- Produces: executable contract that requires exactly one pinned attestation action, least-privilege signing permissions, exact subjects, exact verifier identity, correct step ordering, and unchanged `publish=false` semantics.

- [ ] **Step 1: Add constants for the action and exact subject contract**

Add after the existing regex constants:

```python
ATTEST_ACTION = "actions/attest@508db95dd578ae2727ebd6217d5ba78e4fbda05d"
PUBLIC_ATTESTATION_PATHS = (
    "out/release/arancel_mx.duckdb",
    "out/release/arancel_mx.csv",
    "out/release/arancel_mx.json",
    "out/release/manifest.json",
    "out/release/SHA256SUMS",
    "out/release/official-sources.tar.gz",
)
PUBLIC_ATTESTATION_NAMES = tuple(path.rsplit("/", 1)[-1] for path in PUBLIC_ATTESTATION_PATHS)
```

- [ ] **Step 2: Add a RED least-privilege and action-pin test**

Append:

```python
def test_publisher_is_only_attestation_signer_and_uses_pinned_first_party_action():
    workflow = _workflow()
    build = _job_block(workflow, "build-and-verify", "publish")
    publish = _job_block(workflow, "publish", "notify")
    notify = _job_block(workflow, "notify")

    assert workflow.count("attestations: write") == 1
    assert workflow.count("id-token: write") == 1
    assert "attestations: write" in publish
    assert "id-token: write" in publish
    assert "contents: write" in publish
    assert "attestations: write" not in build
    assert "id-token: write" not in build
    assert "attestations: write" not in notify
    assert "id-token: write" not in notify
    assert "artifact-metadata: write" not in workflow

    assert publish.count(ATTEST_ACTION) == 1
    assert "actions/attest@v4" not in workflow
```

This deliberately fails on current `main` because the signing permissions and action do not yet exist.

- [ ] **Step 3: Add a RED exact-subject test without accepting globs**

Append:

```python
def test_attestation_subjects_are_exactly_the_six_public_release_files():
    workflow = _workflow()
    publish = _job_block(workflow, "publish", "notify")

    match = re.search(
        r"subject-path:\s*\|\n(?P<body>(?:\s+out/release/[^\n]+\n){6})",
        publish,
    )
    assert match is not None
    subjects = tuple(line.strip() for line in match.group("body").splitlines())
    assert subjects == PUBLIC_ATTESTATION_PATHS
    assert "out/release/*" not in publish
    assert "out/release/**" not in publish
```

- [ ] **Step 4: Add a RED verifier identity and ordering test**

Append:

```python
def test_attestation_is_verified_before_existing_release_publisher():
    workflow = _workflow()
    publish = _job_block(workflow, "publish", "notify")

    assert "Generate build provenance attestation" in publish
    assert "Verify build provenance attestation" in publish
    assert "gh attestation verify" in publish
    assert "--repo jccontrerasg08-cpu/arancel-mx" in publish
    assert (
        "--signer-workflow "
        "jccontrerasg08-cpu/arancel-mx/.github/workflows/official-data-pipeline.yml"
    ) in publish
    assert "GH_TOKEN: ${{ github.token }}" in publish

    array_match = re.search(
        r"assets=\(\n(?P<body>(?:\s+\"[^\"]+\"\n){6})\s+\)",
        publish,
    )
    assert array_match is not None
    verified_names = tuple(
        line.strip().strip('"') for line in array_match.group("body").splitlines()
    )
    assert verified_names == PUBLIC_ATTESTATION_NAMES

    assert publish.index("Independently verify publication bundle") < publish.index(
        "Generate build provenance attestation"
    ) < publish.index("Verify build provenance attestation") < publish.index(
        "Publish immutable verified release"
    )
```

- [ ] **Step 5: Extend the existing manual-dry-run test**

Add to `test_manual_publish_false_is_a_non_mutating_dry_run()`:

```python
    assert "github.event_name == 'schedule' || inputs.publish == true" in publish
    assert "Generate build provenance attestation" not in _job_block(
        workflow, "build-and-verify", "publish"
    )
```

Do not weaken the existing `publish` job condition or notification assertions.

- [ ] **Step 6: Create an isolated implementation branch from current main**

Use a branch name that cannot collide with production release refs:

```text
feat/a9-build-provenance-attestations
```

Commit only the test changes first:

```bash
git add tests/test_official_dataset_workflow.py
git commit -m "test: require release provenance attestations"
```

- [ ] **Step 7: Perform the required double check before opening the draft implementation PR**

Record:

```text
current protected main SHA
feature branch base SHA and 0-behind status
A9 spec path and approved status
actions/attest current official tag -> full SHA mapping
exact four-line permission diff at global/build/publish/notify boundaries
exact six subject paths
no workflow/code/docs changes yet beyond the RED tests
no generated datasets/build outputs/secrets
```

If `main` changed after branch creation, update/recreate the branch before the PR rather than silently implementing on a stale base.

- [ ] **Step 8: Open the implementation PR as draft and observe RED in GitHub Actions**

The expected failure is only the newly-added A9 workflow-contract assertions. Existing repository tests, build, compatibility and packaging behavior must remain unaffected.

Do not edit the workflow until the Actions log confirms the intended RED boundary.

### Task 2: Implement the minimal fail-closed publish-job attestation flow

**Files:**
- Modify: `.github/workflows/official-data-pipeline.yml`
- Test: `tests/test_official_dataset_workflow.py`

**Interfaces:**
- Consumes: `out/release/` downloaded by the existing `actions/download-artifact` step and already accepted by `verify_publication_bundle`.
- Produces: one GitHub SLSA provenance attestation whose statement contains all six public subjects, followed by successful local subject verification before the existing publisher may run.

- [ ] **Step 1: Re-verify the action pin immediately before the workflow edit**

Query the official `actions/attest` repository. Require:

```text
v4.2.1 -> 508db95dd578ae2727ebd6217d5ba78e4fbda05d
```

If this mapping differs, stop implementation and update the approved spec/plan instead of guessing a replacement SHA.

- [ ] **Step 2: Extend only the `publish` job permissions**

Replace:

```yaml
    permissions:
      contents: write
```

with:

```yaml
    permissions:
      contents: write
      attestations: write
      id-token: write
```

Do not change workflow-level, build, or notify permissions.

- [ ] **Step 3: Add the pinned multi-subject attestation after bundle verification**

Insert immediately after `Independently verify publication bundle`:

```yaml
      - name: Generate build provenance attestation
        uses: actions/attest@508db95dd578ae2727ebd6217d5ba78e4fbda05d # v4.2.1
        with:
          subject-path: |
            out/release/arancel_mx.duckdb
            out/release/arancel_mx.csv
            out/release/arancel_mx.json
            out/release/manifest.json
            out/release/SHA256SUMS
            out/release/official-sources.tar.gz
```

Do not add `continue-on-error`, wildcard subjects, custom predicate inputs, storage-record inputs, or output files under `out/release`.

- [ ] **Step 4: Add fail-closed consumer-style verification immediately after signing**

Insert:

```yaml
      - name: Verify build provenance attestation
        env:
          GH_TOKEN: ${{ github.token }}
        run: |
          set -euo pipefail
          assets=(
            "arancel_mx.duckdb"
            "arancel_mx.csv"
            "arancel_mx.json"
            "manifest.json"
            "SHA256SUMS"
            "official-sources.tar.gz"
          )
          for asset in "${assets[@]}"; do
            gh attestation verify "out/release/${asset}" \
              --repo jccontrerasg08-cpu/arancel-mx \
              --signer-workflow jccontrerasg08-cpu/arancel-mx/.github/workflows/official-data-pipeline.yml
          done
```

Do not pass `--predicate-type`; the CLI default enforces `https://slsa.dev/provenance/v1`.

Do not add retry logic unless a real live run later demonstrates GitHub attestation API propagation causes a reproducible transient failure. YAGNI applies until evidence exists.

- [ ] **Step 5: Run the targeted workflow contract test and require GREEN**

Run:

```bash
python -m pytest tests/test_official_dataset_workflow.py -q
```

Expected: PASS. If regex assertions fail because actual YAML formatting differs, inspect the workflow and adjust the test only if the semantic contract is still exact; never relax the subject set, identity, permissions, or ordering to make the test pass.

- [ ] **Step 6: Commit the minimal workflow implementation**

```bash
git add .github/workflows/official-data-pipeline.yml tests/test_official_dataset_workflow.py
git commit -m "ci: attest verified release assets"
```

### Task 3: Document the consumer verification and trust-layer semantics

**Files:**
- Modify: `tests/test_autonomous_documentation.py`
- Modify: `docs/release-process.md`

**Interfaces:**
- Consumes: implemented A9 workflow contract.
- Produces: public operator/consumer instructions that distinguish checksum validation, manifest provenance, and cryptographically signed workflow provenance.

- [ ] **Step 1: Add RED documentation assertions first**

Extend `test_release_process_documents_exact_publication_and_recovery_contract()` by adding these exact normalized requirements to `required`:

```python
        "artifact attestation",
        "actions/attest",
        "gh attestation verify",
        "--repo jccontrerasg08-cpu/arancel-mx",
        "--signer-workflow jccontrerasg08-cpu/arancel-mx/.github/workflows/official-data-pipeline.yml",
        "sha256sums",
        "manifest.json",
        "not a legal signature",
```

- [ ] **Step 2: Run the documentation contract and confirm RED**

Run:

```bash
python -m pytest tests/test_autonomous_documentation.py::test_release_process_documents_exact_publication_and_recovery_contract -q
```

Expected: FAIL only for missing A9 documentation phrases.

- [ ] **Step 3: Add an A9 section to `docs/release-process.md`**

Add a section after the six-asset verification/publication description with the following semantics, in the document's existing language/style:

```markdown
### Artifact attestation

For a changed, validated build that is actually entering the publication job, GitHub Actions creates one SLSA provenance artifact attestation over the same six public files. The signing step uses the first-party `actions/attest` action with GitHub OIDC and runs only after `verify_publication_bundle()` has accepted the downloaded build artifact.

Before the release publisher runs, every subject is verified against both this repository and the exact signer workflow:

```bash
gh attestation verify arancel_mx.duckdb \
  --repo jccontrerasg08-cpu/arancel-mx \
  --signer-workflow jccontrerasg08-cpu/arancel-mx/.github/workflows/official-data-pipeline.yml
```

Apply the same command to `arancel_mx.csv`, `arancel_mx.json`, `manifest.json`, `SHA256SUMS`, and `official-sources.tar.gz`.

These layers answer different questions:

- `SHA256SUMS` checks local digest consistency for the release files it covers.
- `manifest.json` records dataset, source, registry, validation and workflow provenance inside the release contract.
- GitHub artifact attestation binds subject digests to the GitHub Actions workflow identity through signed provenance.

The artifact attestation is not a legal signature on the Mexican source documents and does not replace DOF/Diputados legal evidence or the repository's blocking legal reconciliation.
```

If the surrounding document is primarily Spanish, translate the prose but preserve the exact command, identifiers, and required phrases already protected by `tests/test_autonomous_documentation.py` where appropriate. The normalized test requires the literal English phrase `not a legal signature`; include it parenthetically if needed rather than changing the policy test after RED.

- [ ] **Step 4: State certification status precisely**

Until a post-A9 real publication has been independently verified, document A9 as:

```text
implemented / CI-verified; live attestation verification pending the next legitimate changed release
```

Do not claim `data-2026.08.11` proves A9; it was published before A9 existed.

- [ ] **Step 5: Run documentation and workflow tests together**

```bash
python -m pytest tests/test_official_dataset_workflow.py tests/test_autonomous_documentation.py -q
```

Expected: PASS.

- [ ] **Step 6: Commit docs + policy test**

```bash
git add tests/test_autonomous_documentation.py docs/release-process.md
git commit -m "docs: explain release attestation verification"
```

### Task 4: Final implementation PR verification and merge gate

**Files:**
- No new files beyond Tasks 1-3.

**Interfaces:**
- Produces: reviewable A9 implementation PR whose head is safe to merge under the existing `test` required check.

- [ ] **Step 1: Run the full targeted and repository test gates**

Run:

```bash
python -m pytest tests/test_official_dataset_workflow.py tests/test_autonomous_documentation.py -q
python -m pytest -q
python -m build
git diff --check
```

In GitHub CI also require the existing job `test` to prove:

```text
full pytest suite success
python -m build success
DuckDB 1.1.0 compatibility success
clean-install wheel success
clean-install sdist success
whitespace success
```

- [ ] **Step 2: Perform the final double check against current `main`**

Before marking the PR ready, verify and record:

```text
branch is 0 commits behind current main
final head SHA
exact changed-file set is limited to:
  .github/workflows/official-data-pipeline.yml
  tests/test_official_dataset_workflow.py
  tests/test_autonomous_documentation.py
  docs/release-process.md
workflow-level permissions still contents: read
build-and-verify still contents: read only
notify still contents: read + issues: write only
publish is the only job with contents: write / attestations: write / id-token: write
artifact-metadata: write absent
no PAT/secrets.* added
exact one actions/attest invocation with current verified full SHA
subject set exactly six and no glob
verifier set exactly six
repo identity exact
signer workflow exact
attestation steps precede publisher
publish condition unchanged
scripts/publish_release.py unchanged
source registry/parsers/legal/schema/data files unchanged
no generated out/, dist/, .duckdb or source captures committed
all review threads resolved
```

- [ ] **Step 3: Update the draft PR body with RED/GREEN evidence**

Include:

```text
base main SHA
RED CI run ID and exact failing A9 assertions
GREEN CI run ID
final head SHA
actions/attest tag -> SHA mapping
permission diff
subject list
ordering evidence
full CI gate evidence
live gate explicitly pending
```

- [ ] **Step 4: Mark ready and squash merge using exact head SHA protection**

Do not bypass the `test` ruleset. If `main` changes after the final green run, re-evaluate whether the branch is still mergeable/0-behind and rerun the gate if needed.

- [ ] **Step 5: Require post-merge CI on the exact squash SHA**

A9 is not implementation-complete until the `main` push CI on the merge SHA is `success` with all existing packaging and DuckDB compatibility steps green.

### Task 5: Post-merge safety dry-run and live attestation certification

**Files:**
- No code changes unless a real run exposes a reproducible implementation defect; any such defect requires its own TDD hotfix PR and double check.

**Interfaces:**
- Produces two separate evidence levels: non-mutating safety verification immediately after merge, then live cryptographic verification on the next legitimate changed production release.

- [ ] **Step 1: Run one post-merge `Official data pipeline` with `publish=false`**

From trusted `main`, manually dispatch:

```text
Actions -> Official data pipeline -> Run workflow
branch: main
Publish verified changed data: false
```

Require:

```text
build-and-verify: success or valid no_change
publish: skipped
notify: success dry-run
no release created
no tag created
no production issue mutation
no new artifact attestation created by this dry-run
main unchanged
```

This proves A9 did not break the already-certified non-mutating path. It does **not** count as live signing evidence.

- [ ] **Step 2: Wait for the next legitimate changed production release after the A9 merge**

Do not create a fake `data-YYYY.MM.DD` release and do not mutate `data-2026.08.11`. A scheduled or explicitly authorized production run must naturally reach `status=built` and `publish` after detecting a legitimate source-identity change or other valid publication condition.

- [ ] **Step 3: Verify the live publish job ordering/evidence**

For that run require these steps to be `success` in this order:

```text
Download exact verified build artifact
Independently verify publication bundle
Generate build provenance attestation
Verify build provenance attestation
Publish immutable verified release
```

Also require overall `publish` and `notify` success and no `[DATA ALERT]` left open for the run.

- [ ] **Step 4: Independently verify all six released files as a consumer**

Download the six files from the newly-created release to a clean directory. For each exact file run:

```bash
gh attestation verify FILE \
  --repo jccontrerasg08-cpu/arancel-mx \
  --signer-workflow jccontrerasg08-cpu/arancel-mx/.github/workflows/official-data-pipeline.yml
```

Require success for all six. Also run existing `SHA256SUMS` verification and `certify_bundle()` on the downloaded release files so attestation evidence is combined with the repository's independent release-contract checks.

- [ ] **Step 5: Archive the live evidence without mutating the release**

Record in the implementation PR or a follow-up documentation-only evidence commit:

```text
release tag
release ID
immutable flag
workflow run ID
head SHA
attestation action full SHA
six asset names/digests
consumer gh verification success for each subject
SHA256SUMS verification result
bundle certification result
```

Only after this evidence exists may documentation change from:

```text
implemented / CI-verified
```

to:

```text
live-certified
```

A9 is complete at that point. A10 timestamp semantics and A11 release-integrity/immutability verification remain separate gates even if the same live release later provides useful evidence for them.
