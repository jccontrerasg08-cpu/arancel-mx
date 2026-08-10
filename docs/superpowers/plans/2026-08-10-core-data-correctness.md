# Core Data Correctness Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make official-source capture, legal reconciliation, timestamps, source-change identity, and release metadata internally correct before any autonomous publisher is allowed to write a GitHub Release.

**Architecture:** Split source acquisition from canonical materialization. A new official-input snapshot boundary captures registered SNICE/Diputados inputs plus the current DOF evidence linked by the trusted Diputados ledger. That snapshot owns source identity and reconciliation. Only a reconciled changed snapshot reaches parsing/materialization. Release provenance is persisted inside `dataset_release` and exported into `manifest.json` without changing the public `arancel_mx` column contract.

**Tech Stack:** Python 3.11, requests, DuckDB, PyMuPDF, pytest, existing offline synthetic XLSX/PDF fixtures.

## Global Constraints

- Preserve the current public `arancel_mx` column order and semantics.
- Fail closed on ambiguous discovery, missing legal evidence, unknown parser layout, checksum mismatch, or inconsistent source identity.
- Do not infer a legal effective date from observation alone.
- `retrieved_at` must come from the actual HTTP fetch; `generated_at` remains build metadata.
- Keep all tests offline by using fake sessions and synthetic fixtures.
- Do not write generated source documents or DuckDB files into Git history.
- Bump the internal/public dataset schema version from `1` to `2` because `dataset_release` gains release-metadata storage, while preserving the existing `arancel_mx` view contract.

---

## Task 1: Introduce explicit release provenance and source identity types

**Files:**
- Create: `src/arancel_mx/release/metadata.py`
- Modify: `src/arancel_mx/release/__init__.py`
- Create: `tests/release/test_metadata.py`

**Interfaces:**

```python
@dataclass(frozen=True)
class ReleaseProvenance:
    git_commit_sha: str
    github_run_id: str
    github_run_attempt: str
    github_workflow_ref: str
    github_artifact_name: str

    @classmethod
    def local(cls) -> "ReleaseProvenance": ...

    def to_dict(self) -> dict[str, str]: ...


@dataclass(frozen=True)
class SourceIdentity:
    dataset_key: str
    document_role: str
    source_url: str
    sha256: str
    registry_version: str

    def to_dict(self) -> dict[str, str]: ...


def source_identity_digest(items: Sequence[SourceIdentity]) -> str: ...

def source_identity_from_manifest(manifest: Mapping[str, object]) -> tuple[SourceIdentity, ...]: ...
def source_identity_changed(current: Sequence[SourceIdentity], previous: Sequence[SourceIdentity]) -> bool: ...
```

- [ ] Add failing tests proving `ReleaseProvenance.local()` uses explicit local values rather than `None`.

```python
def test_local_release_provenance_is_explicit():
    value = ReleaseProvenance.local().to_dict()
    assert value == {
        "git_commit_sha": "local",
        "github_run_id": "local",
        "github_run_attempt": "local",
        "github_workflow_ref": "local",
        "github_artifact_name": "local",
    }
```

- [ ] Run `python -m pytest tests/release/test_metadata.py -q` and confirm the test fails because the module does not exist.
- [ ] Implement the two dataclasses with validation that rejects blank strings and non-64-character SHA-256 source hashes.
- [ ] Add a deterministic digest test using two identities supplied in opposite order and assert equal digest output.
- [ ] Add a change-detection test proving URL/hash/role/registry-version differences are meaningful but list ordering is not.
- [ ] Add a manifest parsing test that rejects missing `source_identity` metadata instead of silently returning an empty state.
- [ ] Export the new public helpers from `src/arancel_mx/release/__init__.py`.
- [ ] Run `python -m pytest tests/release/test_metadata.py -q` and confirm all tests pass.
- [ ] Commit: `feat: add release provenance and source identity types`.

---

## Task 2: Split official source capture from dataset materialization

**Files:**
- Create: `src/arancel_mx/pipeline/official_sources.py`
- Modify: `src/arancel_mx/pipeline/official_dataset.py`
- Modify: `src/arancel_mx/pipeline/__init__.py`
- Modify: `tests/pipeline/test_official_dataset.py`
- Create: `tests/pipeline/test_official_sources.py`

**Interfaces:**

```python
@dataclass(frozen=True)
class CapturedOfficialSource:
    dataset_key: str
    document_role: str
    title: str
    fetched: FetchedDocument
    capture: CaptureManifest
    source_document: dict[str, object]


@dataclass(frozen=True)
class OfficialInputSnapshot:
    ledger: LedgerSnapshot
    sources: tuple[CapturedOfficialSource, ...]
    identities: tuple[SourceIdentity, ...]
    registry_version: str
    registry_sha256: str
    reconciliation: ReconciliationReport


def capture_official_inputs(
    config: OfficialDatasetConfig,
    session: Any | None = None,
) -> OfficialInputSnapshot: ...
```

- [ ] Move `_capture_source`, source-file naming, registry loading, ledger fetching, LIGIE/NICO discovery, and consolidated-LIGIE capture into the new module without changing behavior yet.
- [ ] Add a failing test asserting `capture_official_inputs()` returns the three existing base source roles before DOF evidence is added.
- [ ] Run `python -m pytest tests/pipeline/test_official_sources.py -q` and confirm the failure.
- [ ] Implement the source-capture boundary and make `build_official_dataset()` call it rather than performing HTTP discovery inline.
- [ ] Keep parsing and materialization inside `official_dataset.py`; pass the captured snapshot into those stages.
- [ ] Update the existing fake session so every discovery request is observable in `session.requested`.
- [ ] Run `python -m pytest tests/pipeline/test_official_sources.py tests/pipeline/test_official_dataset.py -q`.
- [ ] Commit: `refactor: isolate official source capture from dataset build`.

---

## Task 3: Enforce timeout semantics on registered discovery requests

**Files:**
- Modify: `src/arancel_mx/pipeline/reconcile.py`
- Modify: `src/arancel_mx/pipeline/official_sources.py`
- Modify: `tests/pipeline/test_reconcile.py`
- Modify: `tests/pipeline/test_official_sources.py`

**Interfaces:**

```python
def discover_registered_sources(
    registry: Mapping[str, RegistryEntry],
    client: Any,
    timeout_s: float = 60.0,
) -> tuple[DiscoveredDocument, ...]: ...
```

- [ ] Add a failing fake-client test that records the `timeout` argument and asserts every canonical-page request receives the configured value.
- [ ] Add a failing test for `timeout_s <= 0`.
- [ ] Run `python -m pytest tests/pipeline/test_reconcile.py -q` and confirm the new tests fail.
- [ ] Change `client.get(entry.canonical_page)` to `client.get(entry.canonical_page, timeout=timeout_s)` and validate a positive timeout before network access.
- [ ] Pass `config.timeout_s` from `capture_official_inputs()`.
- [ ] Run `python -m pytest tests/pipeline/test_reconcile.py tests/pipeline/test_official_sources.py -q`.
- [ ] Commit: `fix: enforce timeouts during source discovery`.

---

## Task 4: Correct `retrieved_at` semantics

**Files:**
- Modify: `src/arancel_mx/pipeline/official_sources.py`
- Modify: `tests/pipeline/test_official_sources.py`
- Modify: `tests/pipeline/test_official_dataset.py`

- [ ] Extend the fake HTTP `Response`/session helper so `fetch_official_document()` can be monkeypatched to return a known retrieval timestamp different from `generated_at`.
- [ ] Add a failing test with:

```python
retrieved = datetime(2026, 8, 10, 7, 59, 31, tzinfo=timezone.utc)
generated = datetime(2026, 8, 10, 8, 0, 0, tzinfo=timezone.utc)
assert source.source_document["retrieved_at"] == retrieved
assert source.source_document["retrieved_at"] != generated
```

- [ ] Run `python -m pytest tests/pipeline/test_official_sources.py -q` and confirm it fails under the current generated-time behavior.
- [ ] Replace all source capture metadata assignments that use `_build_timestamp(config.generated_at)` for retrieval time with `fetched.retrieved_at.astimezone(timezone.utc).replace(microsecond=0)`.
- [ ] Keep `config.generated_at` unchanged for the dataset release row.
- [ ] Run the focused tests and then `python -m pytest tests/sources/test_http.py tests/pipeline/test_official_dataset.py -q`.
- [ ] Commit: `fix: preserve actual source retrieval timestamps`.

---

## Task 5: Capture and validate the latest required DOF evidence from the trusted Diputados ledger

**Files:**
- Create: `src/arancel_mx/sources/legal_evidence.py`
- Modify: `src/arancel_mx/sources/__init__.py`
- Modify: `src/arancel_mx/pipeline/official_sources.py`
- Modify: `tests/fixtures/diputados/ligie_2022.html` only if a minimal existing fixture link cannot exercise the required cases
- Create: `tests/sources/test_legal_evidence.py`
- Modify: `tests/pipeline/test_official_sources.py`

**Interfaces:**

```python
@dataclass(frozen=True)
class RequiredDofEvidence:
    role: str
    published_at: date
    url: str
    media_type: str


def required_dof_evidence(ledger: LedgerSnapshot) -> tuple[RequiredDofEvidence, ...]: ...
```

Required roles are exactly:
- `law_reform` at `ledger.last_law_reform`
- `tariff_decree` at `ledger.latest_tariff_modification`

- [ ] Add a failing unit test where the latest `law_reform` row lacks a `LedgerLink(role="dof", ...)` and assert a `ValueError` containing `missing DOF evidence: law_reform`.
- [ ] Add the equivalent failure test for `tariff_decree`.
- [ ] Add a success test that extracts exactly one evidence item for each required role, deduplicating identical URLs.
- [ ] Run `python -m pytest tests/sources/test_legal_evidence.py -q` and confirm failures.
- [ ] Implement `required_dof_evidence()` so evidence can only originate from the already-parsed trusted Diputados ledger, never from arbitrary guessed URLs.
- [ ] In `capture_official_inputs()`, fetch each required evidence URL with `fetch_official_document()` using an explicit allowlist limited to `dof.gob.mx`, `www.dof.gob.mx`, `diputados.gob.mx`, and `www.diputados.gob.mx`, because Diputados may host a copy of the DOF publication linked from its legal ledger.
- [ ] Allow only the media type declared by the ledger link, plus `application/pdf`, `text/html`, and `application/msword` when the link metadata is incomplete.
- [ ] Capture those bytes under deterministic source keys such as `dof_law_reform` and `dof_tariff_decree`; derive source IDs from role, final URL, and SHA-256.
- [ ] Include the DOF evidence in the source archive and source-document list so a released build preserves the exact bytes used by the gate.
- [ ] Run focused tests.
- [ ] Commit: `feat: capture required DOF legal evidence`.

---

## Task 6: Make legal reconciliation a blocking build gate

**Files:**
- Modify: `src/arancel_mx/pipeline/reconcile.py`
- Modify: `src/arancel_mx/pipeline/official_sources.py`
- Modify: `tests/pipeline/test_reconcile.py`
- Modify: `tests/pipeline/test_official_sources.py`
- Modify: `tests/pipeline/test_official_dataset.py`

- [ ] Add a failing integration test where the captured `law_reform` evidence date differs from `ledger.last_law_reform`; assert no output release directory is created.
- [ ] Add a failing test where required DOF evidence is absent and assert the error includes the specific reconciliation discrepancy.
- [ ] Add a success test where both evidence roles match and `snapshot.reconciliation.publishable is True`.
- [ ] Run the focused tests and verify the new integration tests fail.
- [ ] Convert captured DOF sources into reconciliation records shaped as:

```python
{
    "document_id": source_document_id,
    "role": "law_reform",  # or tariff_decree
    "published_at": published_at,
    "source_url": final_url,
    "sha256": capture.sha256,
}
```

- [ ] Build the SNICE evidence sequence from the current captured structured sources and explicitly mark proposals/indicators as non-legal when they are later included.
- [ ] Call `reconcile_legal_instruments()` inside `capture_official_inputs()` after all required legal evidence bytes are captured.
- [ ] Raise before workbook/PDF parsing when `publishable` is false:

```python
if not report.publishable:
    details = "; ".join(report.discrepancies)
    raise ValueError(f"legal reconciliation failed: {details}")
```

- [ ] Ensure the work/output directory cleanup semantics leave no partially published `output_dir`.
- [ ] Run `python -m pytest tests/pipeline/test_reconcile.py tests/pipeline/test_official_sources.py tests/pipeline/test_official_dataset.py -q`.
- [ ] Commit: `feat: block builds on legal reconciliation errors`.

---

## Task 7: Add pre-build meaningful source-change detection

**Files:**
- Modify: `src/arancel_mx/pipeline/official_sources.py`
- Modify: `src/arancel_mx/pipeline/official_dataset.py`
- Modify: `scripts/build_official_dataset.py`
- Modify: `tests/pipeline/test_official_sources.py`
- Modify: `tests/pipeline/test_official_dataset.py`
- Modify: `tests/test_official_dataset_script.py`

**Interfaces:**

```python
@dataclass(frozen=True)
class OfficialBuildResult:
    status: Literal["no_change", "built"]
    dataset_version: str
    row_count: int
    validation_status: str
    source_count: int
    output_dir: str | None


def build_official_dataset(
    config: OfficialDatasetConfig,
    session: Any | None = None,
    previous_manifest: Mapping[str, object] | None = None,
) -> dict[str, object]: ...
```

- [ ] Add a failing test that supplies a previous manifest with an identical `source_identity` list and asserts `status == "no_change"`, no candidate DuckDB exists, and no release directory exists.
- [ ] Add a test changing one source SHA and assert the full build runs.
- [ ] Add a test changing only identity list ordering and assert `no_change`.
- [ ] Run focused tests and confirm failures.
- [ ] Compare `OfficialInputSnapshot.identities` with `source_identity_from_manifest(previous_manifest)` immediately after capture/reconciliation and before parsing/materialization.
- [ ] Keep reconciliation before `no_change` success so a currently broken/missing legal source can never be hidden by an old identical tariff workbook hash.
- [ ] Add `--previous-manifest PATH` to `scripts/build_official_dataset.py`; load JSON if supplied and pass it to the builder.
- [ ] Emit machine-readable JSON with `status` for both branches.
- [ ] Run focused script and pipeline tests.
- [ ] Commit: `feat: skip unchanged official dataset builds`.

---

## Task 8: Persist manifest v2 provenance in DuckDB and release JSON

**Files:**
- Modify: `src/arancel_mx/storage/duckdb.py`
- Modify: `src/arancel_mx/pipeline/build.py`
- Modify: `src/arancel_mx/pipeline/official_dataset.py`
- Modify: `scripts/build_official_dataset.py`
- Modify: `tests/storage/test_duckdb.py`
- Modify: `tests/pipeline/test_build.py`
- Modify: `tests/pipeline/test_official_dataset.py`
- Modify: `tests/test_official_dataset_script.py`
- Modify: `tests/release/test_package.py`

**Schema change:**

```sql
ALTERED LOGICAL DEFINITION:
CREATE TABLE IF NOT EXISTS dataset_release (
    dataset_version VARCHAR PRIMARY KEY,
    schema_version VARCHAR NOT NULL,
    ligie_version VARCHAR NOT NULL,
    effective_as_of DATE NOT NULL,
    generated_at TIMESTAMP NOT NULL,
    row_count BIGINT NOT NULL DEFAULT 0,
    validation_status VARCHAR NOT NULL,
    validation_results_json VARCHAR,
    source_documents_json VARCHAR,
    release_metadata_json VARCHAR NOT NULL
);
```

**Release metadata JSON contract:**

```json
{
  "registry_version": "2026-08-10",
  "registry_sha256": "<64 hex>",
  "git_commit_sha": "<sha-or-local>",
  "github_run_id": "<id-or-local>",
  "github_run_attempt": "<attempt-or-local>",
  "github_workflow_ref": "<ref-or-local>",
  "github_artifact_name": "<name-or-local>",
  "level_counts": {"hs2": 0, "hs4": 0, "hs6": 0, "fraccion8": 0, "nico10": 0},
  "reconciliation": {"publishable": true, "error_codes": [], "discrepancies": []},
  "source_identity": []
}
```

- [ ] Add failing schema tests asserting `dataset_release.release_metadata_json` exists and is `NOT NULL`.
- [ ] Change `OfficialDatasetConfig.schema_version` default from `"1"` to `"2"`.
- [ ] Add CLI arguments `--git-commit-sha`, `--github-run-id`, `--github-run-attempt`, `--github-workflow-ref`, and `--github-artifact-name`, each defaulting to `local` for local builds.
- [ ] Add a failing materialization test proving `release_metadata_json` is required and valid JSON.
- [ ] Implement the tenth `dataset_release` column and update all `INSERT`, `SELECT`, public DB copy, and test fixture statements that depend on positional columns.
- [ ] Compute `registry_sha256` from the exact bytes of packaged `source_registry.json`, not from a reserialized JSON object.
- [ ] Put `level_counts`, reconciliation result, and source identity into the release metadata before materialization.
- [ ] Extend `_export_arancel_release()` to parse `release_metadata_json` and write these top-level manifest fields:

```python
manifest.update({
    "registry_version": metadata["registry_version"],
    "registry_sha256": metadata["registry_sha256"],
    "git_commit_sha": metadata["git_commit_sha"],
    "github_run_id": metadata["github_run_id"],
    "github_run_attempt": metadata["github_run_attempt"],
    "github_workflow_ref": metadata["github_workflow_ref"],
    "github_artifact_name": metadata["github_artifact_name"],
    "level_counts": metadata["level_counts"],
    "reconciliation": metadata["reconciliation"],
    "source_identity": metadata["source_identity"],
})
```

- [ ] Add `verify_release()` validation that these fields are present, structurally valid, and reconciliation is publishable.
- [ ] Update deterministic-release tests so two builds with equal source bytes and equal explicit retrieval/build metadata remain logically deterministic.
- [ ] Run `python -m pytest tests/storage tests/pipeline/test_build.py tests/pipeline/test_official_dataset.py tests/release/test_package.py -q`.
- [ ] Commit: `feat: add schema v2 release provenance metadata`.

---

## Task 9: Harden the PDF parser against the PyMuPDF deprecation

**Files:**
- Modify: `src/arancel_mx/parsers/documents.py`
- Modify: `tests/parsers/test_documents.py`

- [ ] Add a simple import-contract test that imports the parser under current PyMuPDF without referencing the deprecated `fitz` module name in project source.
- [ ] Run `python -m pytest tests/parsers/test_documents.py -q`.
- [ ] Replace:

```python
import fitz
```

with:

```python
import pymupdf
```

and replace `fitz.open(...)` with `pymupdf.open(...)`.
- [ ] Run parser tests and verify the deprecation warning from project code is gone.
- [ ] Commit: `fix: migrate PDF parser to pymupdf namespace`.

---

## Task 10: Clarify read-only update CLI semantics without breaking 0.x users abruptly

**Files:**
- Modify: `src/arancel_mx/cli.py`
- Modify: `tests/test_cli.py`
- Modify: `README.md`
- Modify: `README.en.md`

**Public behavior:**
- New preferred command: `arancel-mx check-updates`.
- Existing `arancel-mx update` remains a compatibility alias for this 0.x line, prints a deprecation message to stderr, and remains read-only.
- `run_update()` remains a Python application adapter for explicitly accepted state mutation after downstream jobs succeed.

- [ ] Add a failing parser test asserting `check-updates` appears in `--help`.
- [ ] Add a test asserting `update` delegates to the same `check_for_updates()` path but emits a deprecation message containing `use check-updates`.
- [ ] Add a test proving neither CLI command writes the supplied state file.
- [ ] Run `python -m pytest tests/test_cli.py tests/pipeline/test_update.py -q` and confirm the new tests fail.
- [ ] Add the `check-updates` subparser and preserve `update` as the compatibility alias.
- [ ] Update both READMEs to use `check-updates` in examples and explicitly call it read-only.
- [ ] Run focused tests.
- [ ] Commit: `feat: clarify read-only update check CLI`.

---

## Task 11: Run the complete core-data verification gate

**Files:** No new source files; verification only.

- [ ] Run `python -m pytest -q`.
- [ ] Run `python -m build`.
- [ ] Run `git diff --check`.
- [ ] Run a local synthetic official build through `tests/pipeline/test_official_dataset.py` and verify all six release files are produced for a changed reconciled snapshot.
- [ ] Inspect one generated `manifest.json` and confirm schema version `2`, distinct retrieval/build timestamps, registry hash, reconciliation result, source identities, level counts, and explicit local provenance fields.
- [ ] Confirm an identical previous manifest returns `no_change` and creates no release directory.
- [ ] Commit any test-only fixes as `test: complete core data hardening coverage`.

## Exit Criteria

This plan is complete only when:

1. Every network discovery/fetch has a timeout and allowlist boundary.
2. DOF evidence for current law reform and tariff modification is captured and hashed.
3. Reconciliation blocks parsing/publication on mismatch.
4. `retrieved_at` is a real fetch timestamp.
5. Unchanged source identity exits successfully before parsing/materialization.
6. Schema v2 stores complete release provenance while `arancel_mx` public columns remain unchanged.
7. The PDF parser uses the supported `pymupdf` namespace.
8. The preferred CLI says what it actually does.
9. The full offline suite, package build, and whitespace checks pass.
