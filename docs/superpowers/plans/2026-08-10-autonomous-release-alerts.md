# Autonomous Release and Alerts Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Turn a validated, reconciled changed source snapshot into an automatically published immutable `data-YYYY.MM.DD` GitHub Release, while ensuring every failure blocks publication and creates or updates one actionable GitHub Issue.

**Architecture:** Keep the production build read-only and move GitHub mutation into separate least-privilege jobs. The build job downloads the previous release manifest, runs the core pipeline, and uploads a verified Actions artifact only when data changed. A publisher job with `contents: write` downloads that exact artifact, creates a draft release, uploads six assets, independently verifies them, and publishes. One notification job with `issues: write` runs unconditionally to upsert failures or close recovered alerts.

**Tech Stack:** GitHub Actions, Python 3.11, requests, GitHub REST API, existing release verification code, pytest.

## Global Constraints

- Production scheduled/manual publication runs trusted code from `main` only.
- No `pull_request_target` execution.
- Repository default token stays read-only.
- Only the publisher receives `contents: write`.
- Only the notification job receives `issues: write`.
- Never overwrite, retarget, or replace an existing `data-YYYY.MM.DD` release or tag.
- Build first, mutate GitHub only after every local verification passes.
- Release publication failure must not leave a published partial release.
- GitHub Issue alerts must be deduplicated by deterministic failure identity.
- No external PAT unless the built-in `GITHUB_TOKEN` is proven insufficient.

---

## Task 1: Add a small testable GitHub REST client for automation scripts

**Files:**
- Create: `scripts/github_api.py`
- Create: `tests/automation/test_github_api.py`
- Create directory: `tests/automation/`

**Interfaces:**

```python
class GitHubApi:
    def __init__(
        self,
        repository: str,
        token: str,
        api_url: str = "https://api.github.com",
        session: Any | None = None,
    ): ...

    def request_json(self, method: str, path: str, **kwargs) -> Any: ...
    def request_bytes(self, method: str, path: str, **kwargs) -> bytes: ...
```

- [ ] Add a failing test proving the client sends `Authorization: Bearer <token>`, `Accept: application/vnd.github+json`, and the current REST API version header.
- [ ] Add tests for JSON success, binary success, 404 mapping, and non-2xx errors that include status and a sanitized GitHub message without echoing the token.
- [ ] Run `python -m pytest tests/automation/test_github_api.py -q` and confirm module-not-found failure.
- [ ] Implement the minimal requests-based client with a default 30-second timeout.
- [ ] Ensure error messages never contain request authorization headers.
- [ ] Run focused tests.
- [ ] Commit: `feat: add testable github automation client`.

---

## Task 2: Download and validate the latest published dataset manifest

**Files:**
- Create: `scripts/fetch_previous_release.py`
- Create: `tests/automation/test_fetch_previous_release.py`

**Interfaces:**

```python
def latest_data_release(releases: Sequence[Mapping[str, object]]) -> Mapping[str, object] | None: ...

def fetch_previous_manifest(
    client: GitHubApi,
    output_path: Path,
) -> dict[str, object] | None: ...
```

Rules:
- consider only non-draft, non-prerelease releases whose tag matches `^data-\d{4}\.\d{2}\.\d{2}$`;
- choose the highest semantic date, not API array order;
- require exactly one `manifest.json` asset;
- validate downloaded JSON through `source_identity_from_manifest()` before accepting it.

- [ ] Add failing tests for no previous release, valid latest release, draft exclusion, malformed tag exclusion, duplicate manifest assets, malformed JSON, and missing `source_identity`.
- [ ] Run focused tests and confirm failure.
- [ ] Implement release enumeration and asset download with GitHub's asset API using binary accept headers.
- [ ] Write the file atomically only after validation passes.
- [ ] CLI behavior: print `{"status":"none"}` when no prior dataset exists, otherwise print the selected tag and path.
- [ ] Run focused tests.
- [ ] Commit: `feat: fetch previous verified dataset manifest`.

---

## Task 3: Define structured production run results and failure diagnostics

**Files:**
- Create: `scripts/run_official_pipeline.py`
- Create: `tests/automation/test_run_official_pipeline.py`
- Modify: `scripts/build_official_dataset.py` only if shared parsing helpers should be imported rather than duplicated

**Output contract:** always attempt to write `out/pipeline-result.json`.

Success with no change:

```json
{
  "status": "no_change",
  "stage": "complete",
  "dataset_version": "2026.08.10",
  "artifact_name": "arancel-mx-<run-id>",
  "message": "registered source identity is unchanged"
}
```

Successful build:

```json
{
  "status": "built",
  "stage": "complete",
  "dataset_version": "2026.08.10",
  "artifact_name": "arancel-mx-<run-id>",
  "release_dir": "out/release"
}
```

Failure:

```json
{
  "status": "failed",
  "stage": "build",
  "dataset_version": "2026.08.10",
  "failure_category": "legal_reconciliation",
  "message": "legal reconciliation failed: missing_dof_evidence:law_reform:2025-12-29"
}
```

- [ ] Add failing tests proving expected domain exceptions become sanitized result JSON while the script exits `2`.
- [ ] Add tests proving no-change exits `0` without a release directory and built exits `0` with `out/release`.
- [ ] Add tests that unexpected exceptions use category `unexpected_error` but never include environment variables or token values.
- [ ] Run focused tests and confirm failure.
- [ ] Implement a narrow exception-to-category mapping for discovery, reconciliation, parser/profile, validation, checksum, and generic errors.
- [ ] Accept all GitHub provenance inputs from environment variables and pass them into `OfficialDatasetConfig`/`ReleaseProvenance`.
- [ ] Write `pipeline-result.json` atomically before returning.
- [ ] Run focused tests.
- [ ] Commit: `feat: add structured production pipeline runner`.

---

## Task 4: Implement deterministic GitHub data-alert identity and issue formatting

**Files:**
- Create: `scripts/data_alert.py`
- Create: `tests/automation/test_data_alert.py`

**Interfaces:**

```python
@dataclass(frozen=True)
class DataAlert:
    stage: str
    failure_category: str
    dataset_version: str
    message: str
    run_id: str
    run_attempt: str
    commit_sha: str
    run_url: str

    @property
    def key(self) -> str: ...
    @property
    def title(self) -> str: ...
    def body(self) -> str: ...
```

Deterministic key input:

```text
stage + NUL + failure_category
```

Issue title:

```text
[DATA ALERT] <stage>: <failure_category>
```

The issue body must contain a hidden marker such as:

```html
<!-- arancel-mx-data-alert-key:<sha256> -->
```

- [ ] Add failing tests proving the same stage/category gets the same key across runs and different categories get different keys.
- [ ] Add tests that body includes run URL, commit SHA, dataset candidate, publication state `BLOCKED`, and sanitized message.
- [ ] Add a length-cap test that truncates excessively long exception messages while preserving the run link.
- [ ] Run focused tests and confirm failure.
- [ ] Implement the dataclass and Markdown formatter.
- [ ] Run focused tests.
- [ ] Commit: `feat: define deterministic data alert format`.

---

## Task 5: Upsert failure issues and close recovered alerts

**Files:**
- Modify: `scripts/data_alert.py`
- Modify: `tests/automation/test_data_alert.py`

**Interfaces:**

```python
def upsert_alert(client: GitHubApi, alert: DataAlert) -> int: ...
def close_recovered_alerts(client: GitHubApi, run_url: str, commit_sha: str) -> tuple[int, ...]: ...
def ensure_alert_labels(client: GitHubApi) -> None: ...
```

Labels:
- `data-alert`
- `automation`
- `release-blocked`

- [ ] Add a failing fake-API test where no matching issue exists and assert one issue is created with all three labels.
- [ ] Add a test where one open issue contains the hidden alert key and assert a comment is added instead of creating another issue.
- [ ] Add a test where two matching open issues exist and assert the script fails rather than guessing which issue is canonical.
- [ ] Add a recovery test that comments `Recovered` with the successful run URL and closes every open issue carrying `data-alert` plus a valid arancel-mx hidden marker.
- [ ] Add a test that unrelated user issues labeled `data-alert` but lacking the hidden marker are never closed.
- [ ] Run focused tests and confirm failures.
- [ ] Implement label creation idempotently; treat already-existing labels as success.
- [ ] Implement issue search using repository issues filtered to open state and marker inspection.
- [ ] Implement recovery close with an explicit comment before state mutation.
- [ ] Add CLI modes `failure` and `recovery` driven by environment variables or a supplied result JSON path.
- [ ] Run focused tests.
- [ ] Commit: `feat: automate data alert lifecycle`.

---

## Task 6: Implement draft release creation, six-asset upload, and independent verification

**Files:**
- Create: `scripts/publish_release.py`
- Create: `tests/automation/test_publish_release.py`
- Modify: `src/arancel_mx/release/package.py`
- Modify: `src/arancel_mx/release/__init__.py`
- Modify: `tests/release/test_package.py`

**Published asset allowlist:**

```python
PUBLIC_RELEASE_ASSETS = (
    "arancel_mx.duckdb",
    "arancel_mx.csv",
    "arancel_mx.json",
    "manifest.json",
    "SHA256SUMS",
    "official-sources.tar.gz",
)
```

**Local verification interface:**

```python
def verify_publication_bundle(release_dir: Path) -> dict[str, object]: ...
```

It must:
- require exactly the six allowed files;
- call `verify_release()`;
- require `SHA256SUMS` to cover `arancel_mx.duckdb`, CSV, JSON, manifest, and source archive;
- verify every covered file locally;
- not attempt a self-referential hash for `SHA256SUMS` itself.

- [ ] Add failing bundle tests for missing asset, extra asset, corrupted source archive, and invalid reconciliation metadata.
- [ ] Implement `verify_publication_bundle()` and run release tests.
- [ ] Add publisher tests with a fake GitHub API proving an existing tag/release causes `release_tag_collision` before any mutation.
- [ ] Add a test for the same-date second change and assert no overwrite/update call is made.
- [ ] Add a success test expecting this order: local verify → create draft release targeting exact commit → upload six assets → verify six uploaded assets → publish draft.
- [ ] Implement release creation through the GitHub Releases REST API with `draft: true`, `prerelease: false`, tag `data-<dataset_version>`, and `target_commitish` equal to the validated commit SHA.
- [ ] Upload each asset with exact media type `application/octet-stream` and simple filename only.
- [ ] Independently verify remote asset size and SHA-256. Prefer GitHub's returned SHA-256 asset digest when present; when it is unavailable, download the uploaded asset bytes and calculate the digest locally before publication.
- [ ] Require the remote set to contain exactly the six names and reject duplicates.
- [ ] Publish by patching only `draft: false` after verification succeeds.
- [ ] On pre-publication failure after draft creation, attempt to delete the draft; if cleanup also fails, include both the original error and draft release ID in the structured failure result.
- [ ] After publication, refetch by tag and assert it is non-draft and contains exactly the six verified assets.
- [ ] Do not edit the release or assets after publication.
- [ ] Run `python -m pytest tests/release/test_package.py tests/automation/test_publish_release.py -q`.
- [ ] Commit: `feat: publish verified six-asset data releases`.

---

## Task 7: Replace the weekly read-only workflow with the autonomous production workflow

**Files:**
- Create: `.github/workflows/official-data-pipeline.yml`
- Delete after migration: `.github/workflows/build-official-dataset.yml`
- Replace: `tests/test_official_dataset_workflow.py` with static contract tests for the new workflow
- Modify: `tests/test_public_distribution.py`

**Workflow skeleton:**

```yaml
name: Official data pipeline

on:
  workflow_dispatch:
  schedule:
    - cron: "17 11 * * *"

permissions:
  contents: read

concurrency:
  group: arancel-mx-official-data-production
  cancel-in-progress: false
```

Jobs:

```text
build-and-verify   contents: read
publish            contents: write
notify             contents: read + issues: write
```

- [ ] Rewrite the static workflow test first and assert it fails while the old weekly workflow exists.
- [ ] Required static assertions:
  - daily `17 11 * * *` schedule;
  - `workflow_dispatch`;
  - production concurrency with `cancel-in-progress: false`;
  - global `contents: read`;
  - build job runs offline tests before source network build;
  - build job has a timeout;
  - all external Actions are pinned to full 40-character commit SHAs;
  - publisher is the only job containing `contents: write`;
  - notifier is the only job containing `issues: write`;
  - no `pull_request` or `pull_request_target` trigger;
  - publication depends on build success and `status == built`;
  - notifier uses `if: always()`.
- [ ] Implement the new workflow with an early guard that scheduled/manual publication only runs when `github.ref == 'refs/heads/main'`.
- [ ] Build job sequence:
  1. checkout trusted main;
  2. setup Python;
  3. install exact production-build dependencies from the lock introduced in the supply-chain plan;
  4. run `python -m pytest -q`;
  5. fetch previous manifest;
  6. resolve UTC version and provenance environment;
  7. run `scripts/run_official_pipeline.py` with `continue-on-error: true` at the step level;
  8. parse `out/pipeline-result.json` into job outputs;
  9. upload `out/release` only when status is `built`;
  10. explicitly fail the job after diagnostics are exposed when the runner step failed.
- [ ] Use artifact name `arancel-mx-${{ github.run_id }}-${{ github.run_attempt }}` and pass that exact name into manifest provenance.
- [ ] Publisher job downloads only that artifact by exact name, reruns `verify_publication_bundle()`, then runs `scripts/publish_release.py`.
- [ ] Publisher captures structured result outputs before explicitly failing so the notifier receives a useful category/message.
- [ ] Notification job runs always after both jobs. If build failed, upsert build alert. If publish failed, upsert publish alert. If build succeeded and publish either succeeded or was skipped for no change, run recovery close.
- [ ] Delete the old `build-official-dataset.yml` only after the new static tests are green.
- [ ] Run `python -m pytest tests/test_official_dataset_workflow.py tests/test_public_distribution.py -q`.
- [ ] Commit: `feat: automate official data release pipeline`.

---

## Task 8: Make workflow failure diagnostics available even when the core command fails

**Files:**
- Modify: `.github/workflows/official-data-pipeline.yml`
- Modify: `scripts/run_official_pipeline.py`
- Modify: `scripts/publish_release.py`
- Modify: `tests/test_official_dataset_workflow.py`
- Modify: `tests/automation/test_run_official_pipeline.py`
- Modify: `tests/automation/test_publish_release.py`

- [ ] Add failing static tests that require step IDs `pipeline` and `publisher`, `continue-on-error: true` on those command steps, a subsequent output-extraction step with `if: always()`, and an explicit final nonzero guard.
- [ ] Add result-json tests proving both scripts write diagnostics before returning nonzero.
- [ ] Implement output extraction without printing secret tokens or full environment dumps.
- [ ] Limit issue-visible error messages to a safe bounded size while preserving the workflow run URL as the path to complete logs.
- [ ] Run focused tests.
- [ ] Commit: `feat: preserve diagnostics for failed automation runs`.

---

## Task 9: Test alert recovery and no-change behavior at workflow-contract level

**Files:**
- Modify: `tests/test_official_dataset_workflow.py`
- Modify: `tests/automation/test_data_alert.py`

- [ ] Add static assertions that `notify` treats `publish` result `skipped` as healthy when `build` output status is `no_change`.
- [ ] Add static assertion that a failed build can never satisfy the publisher `if` condition.
- [ ] Add a unit test that a previously open source-access alert is closed by a successful no-change run.
- [ ] Add a unit test that a release-tag-collision alert remains open until a later successful run.
- [ ] Run focused tests.
- [ ] Commit: `test: cover automation recovery and no-change paths`.

---

## Task 10: Run a safe production dry run before enabling mutation

**Files:**
- Temporarily supported through `workflow_dispatch` input in `.github/workflows/official-data-pipeline.yml`
- Modify: `tests/test_official_dataset_workflow.py`

**Manual input:**

```yaml
workflow_dispatch:
  inputs:
    publish:
      description: "Publish verified changed data"
      required: true
      type: boolean
      default: false
```

Scheduled runs always use production behavior after final cutover; the input only gives maintainers a safe pre-cutover manual dry run.

- [ ] Add a static test that manual `publish=false` can run the entire capture/reconcile/build/verify path but cannot enter the publisher job.
- [ ] Implement the input guard so schedule events are publication-enabled while manual dispatch obeys the boolean.
- [ ] Before enabling the schedule on `main`, manually dispatch `publish=false` from the hardened branch or a trusted temporary main state and verify:
  - tests pass;
  - official sources reconcile;
  - previous release manifest is found;
  - if sources are unchanged, no artifact/release mutation occurs;
  - if changed, the verified Actions artifact is produced but no GitHub Release is created.
- [ ] Inspect `pipeline-result.json`, artifact contents, and manifest provenance.
- [ ] Commit any dry-run-only corrections as `fix: address production pipeline dry run findings`.

---

## Task 11: Enable autonomous schedule and verify the first live cycle

**Prerequisites outside code:**
- GitHub Release immutability enabled in repository Settings.
- `main` protection/ruleset configured according to the repository hardening plan.
- Default workflow permissions remain read-only.

- [ ] Merge hardened implementation only after CI is green.
- [ ] Dispatch once on trusted `main` with `publish=false` and verify expected behavior.
- [ ] Dispatch with `publish=true` only when a changed dataset candidate exists or use the next scheduled run.
- [ ] If no source change exists, verify the run is green and creates no release or issue.
- [ ] On the first legitimate changed snapshot, verify a new `data-YYYY.MM.DD` release is automatically created from the exact `main` commit, has six assets, and matches local/Actions hashes.
- [ ] Verify there are no open automation alerts after the healthy run.
- [ ] Confirm a deliberately simulated failure in a non-production test branch cannot publish because the production workflow is not triggered by PR branches.

## Exit Criteria

This plan is complete only when:

1. A no-change run is green and publishes nothing.
2. A valid changed run publishes exactly one six-asset immutable release.
3. The publisher cannot run after build/reconciliation failure.
4. Same-date tag collisions block instead of overwriting.
5. Remote release assets are independently verified before draft publication.
6. Any failed production stage creates or updates one deterministic GitHub Issue.
7. A later healthy run comments on and closes automation-generated alerts.
8. No production workflow uses a PAT, `write-all`, or `pull_request_target`.
