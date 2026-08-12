# PyPI Consumer Core Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Implement the stable `Dataset` Python API, typed models, exact data-release resolution, verified cache/download transaction, deterministic query semantics, and strict offline behavior for `arancel-mx 0.2.0`.

**Architecture:** Add a focused `src/arancel_mx/consumer/` package that depends on existing read-only DuckDB/storage/domain contracts but never imports maintainer ETL/release entrypoints. `Dataset` is a thin public facade over `DatasetManager`, with network discovery/download, cache state, integrity validation, and SQL query logic separated into small modules so every boundary can be tested deterministically.

**Tech Stack:** Python 3.11+, frozen dataclasses, `requests`, `duckdb`, `platformdirs`, `filelock`, `pytest`, local HTTP fixtures/mocks.

## Global Constraints

- Public API: `Dataset`, `TariffRecord`, `SearchResult`, `ProvenanceRecord`, `DatasetInfo`, documented exceptions.
- Consumer DuckDB connections are read-only.
- `Dataset.latest(offline=True)` performs no network access and selects the newest locally verified dataset.
- `Dataset.open(path)` performs structural validation but never invents release/SHA provenance for standalone files.
- Valid data tags match `^data-\d{4}\.\d{2}\.\d{2}$` and must be non-draft/non-prerelease.
- Exactly six remote asset names are required: `arancel_mx.duckdb`, `arancel_mx.csv`, `arancel_mx.json`, `manifest.json`, `SHA256SUMS`, `official-sources.tar.gz`.
- Normal cache stores DuckDB + manifest + SHA256SUMS + `verified.json`; full six-asset download is reserved for bundle verification.
- `verified.json` is written last after every other check succeeds.
- API digest present and malformed/mismatched -> `DatasetIntegrityError`; API digest absent -> explicit unavailable state, not success.
- CLI/env precedence is implemented here as reusable config: flag/explicit arg > environment > default.
- TDD on every task.

---

### Task 1: Public exception hierarchy, immutable models, and runtime package version

**Files:**
- Create: `src/arancel_mx/consumer/__init__.py`
- Create: `src/arancel_mx/consumer/errors.py`
- Create: `src/arancel_mx/consumer/models.py`
- Modify: `src/arancel_mx/__init__.py`
- Test: `tests/consumer/test_public_api.py`

**Interfaces:**
- Produces public exceptions: `ArancelMXError`, `DatasetError`, `DatasetUnavailableError`, `DatasetDownloadError`, `DatasetIntegrityError`, `DatasetSchemaError`, `DatasetVersionNotFoundError`, `QueryError`, `InvalidCodeError`, `RecordNotFoundError`.
- Produces immutable models: `TariffRecord`, `SearchResult`, `ProvenanceRecord`, `DatasetInfo`.
- Produces `arancel_mx.__version__` from `importlib.metadata.version("arancel-mx")`.
- `Dataset` itself is exported in Task 8; until then the root module only exports version/models/exceptions that already exist.

- [ ] **Step 1: Create the failing public-contract tests**

Create `tests/consumer/test_public_api.py` with these exact tests:

```python
from dataclasses import FrozenInstanceError
from importlib.metadata import version

import pytest

import arancel_mx
from arancel_mx.consumer.errors import (
    ArancelMXError,
    DatasetDownloadError,
    DatasetError,
    DatasetIntegrityError,
    DatasetSchemaError,
    DatasetUnavailableError,
    DatasetVersionNotFoundError,
    InvalidCodeError,
    QueryError,
    RecordNotFoundError,
)
from arancel_mx.consumer.models import DatasetInfo, ProvenanceRecord, SearchResult, TariffRecord


def test_runtime_version_comes_from_distribution_metadata() -> None:
    assert arancel_mx.__version__ == version("arancel-mx")


def test_exception_hierarchy_is_stable() -> None:
    assert issubclass(DatasetError, ArancelMXError)
    assert issubclass(DatasetUnavailableError, DatasetError)
    assert issubclass(DatasetDownloadError, DatasetError)
    assert issubclass(DatasetIntegrityError, DatasetError)
    assert issubclass(DatasetSchemaError, DatasetError)
    assert issubclass(DatasetVersionNotFoundError, DatasetError)
    assert issubclass(QueryError, ArancelMXError)
    assert issubclass(InvalidCodeError, QueryError)
    assert issubclass(RecordNotFoundError, QueryError)


def test_tariff_record_is_frozen() -> None:
    record = TariffRecord(
        code="01012101",
        level="fraccion8",
        description="Reproductores de raza pura.",
        unit_name="Cbza",
        igi_text="10",
        igi_kind="ad_valorem",
        igi_value=10.0,
        ige_text="Ex.",
        ige_kind="exento",
        ige_value=0.0,
        parent_code="010121",
        dataset_version="2026.08.11",
        schema_version="2",
        effective_from=None,
        effective_to=None,
        is_current=True,
    )
    with pytest.raises(FrozenInstanceError):
        record.code = "x"  # type: ignore[misc]


def test_dataset_info_distinguishes_structural_and_release_integrity() -> None:
    info = DatasetInfo(
        dataset_version="2026.08.11",
        schema_version="2",
        path="/tmp/arancel_mx.duckdb",
        source="local",
        structural_valid=True,
        release_verified=False,
        github_digest_state="unavailable",
    )
    assert info.structural_valid is True
    assert info.release_verified is False
    assert info.github_digest_state == "unavailable"
```

Also instantiate `SearchResult` and `ProvenanceRecord` once so constructor field names become contractual.

- [ ] **Step 2: Run the focused test and observe failure**

Run:

```bash
python -m pytest tests/consumer/test_public_api.py -q
```

Expected: collection/import failure because `arancel_mx.consumer.errors` and models do not yet exist, and the current root version is still literal `0.1.0`.

- [ ] **Step 3: Implement the exact public model shapes**

`src/arancel_mx/consumer/errors.py`:

```python
class ArancelMXError(Exception):
    """Base class for documented consumer failures."""


class DatasetError(ArancelMXError):
    pass


class DatasetUnavailableError(DatasetError):
    pass


class DatasetDownloadError(DatasetError):
    pass


class DatasetIntegrityError(DatasetError):
    pass


class DatasetSchemaError(DatasetError):
    pass


class DatasetVersionNotFoundError(DatasetError):
    pass


class QueryError(ArancelMXError):
    pass


class InvalidCodeError(QueryError):
    pass


class RecordNotFoundError(QueryError):
    pass
```

`src/arancel_mx/consumer/models.py` defines `@dataclass(frozen=True, slots=True)` models with these fields:

```python
@dataclass(frozen=True, slots=True)
class TariffRecord:
    code: str
    level: str
    description: str
    unit_name: str | None
    igi_text: str | None
    igi_kind: str | None
    igi_value: float | None
    ige_text: str | None
    ige_kind: str | None
    ige_value: float | None
    parent_code: str | None
    dataset_version: str
    schema_version: str
    effective_from: date | None
    effective_to: date | None
    is_current: bool


@dataclass(frozen=True, slots=True)
class SearchResult:
    record: TariffRecord
    score: int
    match_kind: Literal["exact_code", "code_prefix", "description"]


@dataclass(frozen=True, slots=True)
class ProvenanceRecord:
    source_document_id: str
    role: str
    is_primary: bool
    authority: str
    publication_venue: str
    title: str
    source_url: str
    sha256: str
    published_at: date | None
    effective_from: date | None
    effective_to: date | None


@dataclass(frozen=True, slots=True)
class DatasetInfo:
    dataset_version: str | None
    schema_version: str | None
    path: str
    source: Literal["managed-cache", "local"]
    structural_valid: bool
    release_verified: bool
    github_digest_state: Literal["verified", "unavailable", "not_applicable"]
```

`src/arancel_mx/__init__.py` derives version with:

```python
from importlib.metadata import version as _distribution_version

__version__ = _distribution_version("arancel-mx")
```

Export the models/exceptions from the root package only if they are part of the documented public boundary; do not export internal release/cache types.

- [ ] **Step 4: Re-run focused tests**

Run:

```bash
python -m pytest tests/consumer/test_public_api.py -q
```

Expected: all tests pass.

- [ ] **Step 5: Run import-boundary regressions**

Run:

```bash
python -m pytest tests/test_import_boundaries.py tests/test_public_distribution.py -q
```

Expected: pass; no maintainer import cycle is introduced.

- [ ] **Step 6: Commit**

```bash
git add src/arancel_mx/__init__.py src/arancel_mx/consumer tests/consumer/test_public_api.py
git commit -m "feat: define public consumer API types"
```

---

### Task 2: Consumer configuration and precedence

**Files:**
- Create: `src/arancel_mx/consumer/config.py`
- Test: `tests/consumer/test_config.py`
- Modify: `pyproject.toml`
- Modify: `requirements/production-build.txt`

**Interfaces:**
- Produces `ConsumerConfig` and `resolve_config()`.
- Runtime dependencies added: `platformdirs>=4.3`, `filelock>=3.16`.
- `ConsumerConfig.cache_dir: Path`, `dataset: str | None`, `offline: bool`, `timeout: float`.

- [ ] **Step 1: Write failing precedence/path tests**

Create tests for:

```text
test_default_cache_uses_platformdirs
test_explicit_cache_dir_overrides_environment
test_environment_cache_dir_overrides_default
test_explicit_dataset_overrides_environment
test_offline_accepts_true_environment_values
test_offline_accepts_false_environment_values
test_invalid_offline_environment_raises_value_error
test_timeout_must_be_positive
test_explicit_timeout_overrides_environment
test_unicode_custom_cache_path_is_preserved
```

Core test pattern:

```python
def test_explicit_values_override_environment(monkeypatch, tmp_path):
    monkeypatch.setenv("ARANCEL_MX_CACHE_DIR", str(tmp_path / "env"))
    monkeypatch.setenv("ARANCEL_MX_DATASET", "data-2026.08.10")
    monkeypatch.setenv("ARANCEL_MX_OFFLINE", "1")
    monkeypatch.setenv("ARANCEL_MX_TIMEOUT", "99")
    config = resolve_config(
        cache_dir=tmp_path / "explicit",
        dataset="data-2026.08.11",
        offline=False,
        timeout=7.5,
    )
    assert config.cache_dir == tmp_path / "explicit"
    assert config.dataset == "data-2026.08.11"
    assert config.offline is False
    assert config.timeout == 7.5
```

- [ ] **Step 2: Verify tests fail before implementation**

Run:

```bash
python -m pytest tests/consumer/test_config.py -q
```

Expected: import failure for missing `consumer.config`.

- [ ] **Step 3: Implement `ConsumerConfig` and explicit sentinel precedence**

Use an internal sentinel so `offline=False` can override an environment value of true instead of being confused with an omitted argument.

```python
@dataclass(frozen=True, slots=True)
class ConsumerConfig:
    cache_dir: Path
    dataset: str | None
    offline: bool
    timeout: float
```

Default cache root:

```python
Path(platformdirs.user_cache_dir(appname="arancel-mx", appauthor=False))
```

Boolean environment accepted values:

```text
true: 1,true,yes,on
false: 0,false,no,off
```

Any other non-empty value raises `ValueError("ARANCEL_MX_OFFLINE must be a boolean value")`.

Timeout is parsed as float and must be `> 0`.

- [ ] **Step 4: Add dependencies atomically**

In `pyproject.toml` runtime dependencies add:

```toml
"filelock>=3.16",
"platformdirs>=4.3",
```

Regenerate/update the pinned production-build constraint entries according to the repository's existing constraint policy rather than installing an unconstrained transitive set in CI.

- [ ] **Step 5: Run focused and dependency-policy tests**

```bash
python -m pytest tests/consumer/test_config.py tests/test_dependency_policy.py -q
```

Expected: pass.

- [ ] **Step 6: Commit**

```bash
git add pyproject.toml requirements/production-build.txt src/arancel_mx/consumer/config.py tests/consumer/test_config.py
git commit -m "feat: add consumer configuration precedence"
```

---

### Task 3: Exact GitHub data-release discovery

**Files:**
- Create: `src/arancel_mx/consumer/release_api.py`
- Test: `tests/consumer/test_release_api.py`

**Interfaces:**
- Produces internal immutable `ReleaseAsset` and `DataRelease`.
- Produces `GitHubReleaseClient` with:

```python
class GitHubReleaseClient:
    def __init__(self, session: requests.Session, *, timeout: float) -> None: ...
    def latest(self) -> DataRelease: ...
    def version(self, tag: str) -> DataRelease: ...
    def list(self) -> tuple[DataRelease, ...]: ...
```

- `DataRelease.tag`, `release_id`, `assets_by_name` are exact and immutable for one operation.

- [ ] **Step 1: Write failing release-acceptance/rejection tests**

Use fake `requests.Session` responses; do not hit GitHub live. Required tests:

```text
test_latest_accepts_non_draft_non_prerelease_data_tag
test_latest_rejects_non_data_tag
test_latest_rejects_draft
test_latest_rejects_prerelease
test_release_requires_exact_six_asset_names
test_release_rejects_duplicate_asset_name
test_release_rejects_extra_asset_name
test_release_records_valid_sha256_api_digest
test_release_allows_missing_api_digest_as_none
test_release_rejects_malformed_present_api_digest
test_version_rejects_invalid_requested_tag_before_network
test_version_maps_github_404_to_dataset_version_not_found
test_list_filters_invalid_releases_and_sorts_newest_first
test_resolved_asset_urls_are_exact_release_urls_not_releases_latest_urls
```

Define the expected assets constant in the module:

```python
EXPECTED_ASSETS = frozenset({
    "arancel_mx.duckdb",
    "arancel_mx.csv",
    "arancel_mx.json",
    "manifest.json",
    "SHA256SUMS",
    "official-sources.tar.gz",
})
```

- [ ] **Step 2: Run failing tests**

```bash
python -m pytest tests/consumer/test_release_api.py -q
```

Expected: module/import failures.

- [ ] **Step 3: Implement exact parsing and error mapping**

`latest()` calls the GitHub public latest-release endpoint but validates it instead of trusting the word "latest" blindly. `version(tag)` calls the exact `/releases/tags/{tag}` endpoint. `list()` paginates public releases until no page remains or a deterministic configurable page ceiling is reached; 0.2.0 uses a fixed ceiling of 10 pages x 100 results to prevent unbounded discovery.

Any `requests.RequestException` at this boundary becomes `DatasetDownloadError` with exception chaining.

The API digest parser accepts only:

```python
re.fullmatch(r"sha256:([0-9a-fA-F]{64})", digest)
```

Missing `digest` -> `None`. Present malformed digest -> `DatasetIntegrityError`.

- [ ] **Step 4: Re-run focused tests**

```bash
python -m pytest tests/consumer/test_release_api.py -q
```

Expected: pass.

- [ ] **Step 5: Commit**

```bash
git add src/arancel_mx/consumer/release_api.py tests/consumer/test_release_api.py
git commit -m "feat: resolve exact public data releases"
```

---

### Task 4: Streamed HTTP download and retry mapping

**Files:**
- Create: `src/arancel_mx/consumer/http.py`
- Test: `tests/consumer/test_http.py`

**Interfaces:**
- Produces:

```python
def build_session() -> requests.Session: ...

def stream_download(
    session: requests.Session,
    url: str,
    destination: Path,
    *,
    timeout: float,
) -> int: ...
```

- Returns written byte count.
- Writes only to caller-supplied temporary path.

- [ ] **Step 1: Write failing transport tests using a local HTTP fixture/server**

Required tests:

```text
test_stream_download_writes_body_incrementally
test_stream_download_returns_byte_count
test_stream_download_maps_404_to_dataset_download_error
test_stream_download_maps_dns_connection_failure
test_stream_download_maps_timeout
test_retry_policy_retries_429
test_retry_policy_retries_500_502_503_504
test_retry_policy_does_not_retry_404
test_interrupted_response_leaves_only_temporary_file_for_caller_cleanup
```

Retry policy is exactly 3 total GET attempts with backoff factor `0.25` and status allowlist `{429, 500, 502, 503, 504}`. Allowed methods are GET only.

- [ ] **Step 2: Observe failures**

```bash
python -m pytest tests/consumer/test_http.py -q
```

Expected: missing module/functions.

- [ ] **Step 3: Implement session adapter and streamed write**

Use `requests.adapters.HTTPAdapter` plus `urllib3.util.retry.Retry` already provided transitively by `requests`; do not add a second HTTP client library.

Write chunks of 1 MiB, skip empty keepalive chunks, call `response.raise_for_status()`, and chain errors into `DatasetDownloadError`.

- [ ] **Step 4: Pass focused tests**

```bash
python -m pytest tests/consumer/test_http.py -q
```

- [ ] **Step 5: Commit**

```bash
git add src/arancel_mx/consumer/http.py tests/consumer/test_http.py
git commit -m "feat: add bounded consumer downloads"
```

---

### Task 5: Cross-platform cache layout, lock, atomic promotion and verified state

**Files:**
- Create: `src/arancel_mx/consumer/cache.py`
- Test: `tests/consumer/test_cache.py`

**Interfaces:**
- Produces `CachePaths`, `VerifiedMetadata`, `DatasetCache`.

```python
@dataclass(frozen=True, slots=True)
class CachePaths:
    root: Path
    release_dir: Path
    duckdb: Path
    manifest: Path
    sha256sums: Path
    verified: Path
    lock: Path


class DatasetCache:
    def paths(self, tag: str) -> CachePaths: ...
    def list_verified(self) -> tuple[str, ...]: ...
    def latest_verified(self) -> str: ...
    def load_verified(self, tag: str) -> VerifiedMetadata: ...
    def promote(self, tag: str, staging_dir: Path, metadata: VerifiedMetadata) -> CachePaths: ...
    def cleanup_stale_parts(self, tag: str) -> None: ...
    def locked(self): ...
```

- [ ] **Step 1: Write failing cache invariants**

Required tests:

```text
test_paths_isolate_each_data_version
test_list_verified_ignores_directory_without_verified_json
test_latest_verified_uses_date_tag_order_not_directory_mtime
test_promote_uses_os_replace_for_each_final_asset
test_verified_json_is_written_last
test_failed_promotion_never_creates_verified_json
test_existing_verified_version_is_not_silently_overwritten
test_stale_part_cleanup_does_not_delete_verified_version
test_cache_lock_serializes_two_processes
test_cache_supports_spaces_in_path
test_cache_supports_unicode_enye_path
test_read_only_cache_failure_is_mapped_to_dataset_unavailable_error
```

The concurrency test launches two subprocesses that both acquire the same `FileLock`; assert the critical-section timestamps do not overlap.

- [ ] **Step 2: Run and observe failure**

```bash
python -m pytest tests/consumer/test_cache.py -q
```

- [ ] **Step 3: Implement metadata and promotion order**

`VerifiedMetadata` serialized JSON keys are deterministic and sorted:

```text
release_id
dataset_tag
dataset_version
schema_version
duckdb_sha256
manifest_sha256
sha256sums_sha256
github_digest_state
verified_at
```

Promotion order:

```text
manifest.json
SHA256SUMS
arancel_mx.duckdb
verified.json LAST
```

All staged and final files live under the same cache root so `os.replace()` remains atomic on one filesystem.

- [ ] **Step 4: Pass cache tests**

```bash
python -m pytest tests/consumer/test_cache.py -q
```

- [ ] **Step 5: Commit**

```bash
git add src/arancel_mx/consumer/cache.py tests/consumer/test_cache.py
git commit -m "feat: add atomic verified dataset cache"
```

---

### Task 6: Checksum, manifest and DuckDB integrity gate

**Files:**
- Create: `src/arancel_mx/consumer/integrity.py`
- Test: `tests/consumer/test_integrity.py`
- Create: `tests/consumer/conftest.py`

**Interfaces:**
- Produces:

```python
def sha256_file(path: Path) -> str: ...
def parse_sha256sums(text: str) -> dict[str, str]: ...
def load_manifest(path: Path) -> dict[str, object]: ...
def verify_api_digest(path: Path, expected: str | None) -> Literal["verified", "unavailable"]: ...
def validate_duckdb(
    path: Path,
    *,
    manifest: Mapping[str, object] | None,
    expected_tag: str | None,
    release_verified: bool,
    github_digest_state: Literal["verified", "unavailable", "not_applicable"],
) -> DatasetInfo: ...
```

- [ ] **Step 1: Build deterministic DuckDB fixture support**

`tests/consumer/conftest.py` creates a minimal real DuckDB using the existing schema contract and inserts:

```text
hs2 01
hs4 0101
hs6 010121
fraccion8 01012101
nico10 0101210100
```

Insert one `dataset_release` row with `dataset_version="2026.08.11"`, `schema_version="2"`, validation status `passed`, and create the same public `arancel_mx` view shape used by release packaging. Insert one `source_document` and `record_provenance` row for provenance tests.

- [ ] **Step 2: Write failing integrity tests**

Required tests:

```text
test_parse_sha256sums_accepts_exact_two_column_contract
test_parse_sha256sums_rejects_invalid_hash
test_parse_sha256sums_rejects_duplicate_filename
test_manifest_requires_dataset_version_schema_version_and_validation_status
test_manifest_version_must_match_resolved_tag
test_api_digest_present_and_matching_is_verified
test_api_digest_missing_is_unavailable
test_api_digest_present_and_mismatched_raises_integrity_error
test_duckdb_opens_read_only
test_duckdb_requires_arancel_mx_view
test_duckdb_requires_dataset_release_row
test_duckdb_rejects_unsupported_schema
test_duckdb_release_version_must_match_manifest
test_corrupt_duckdb_maps_to_dataset_integrity_error
test_local_open_without_manifest_reports_release_verified_false
test_managed_cache_validation_reports_release_verified_true
```

Supported dataset schemas for package 0.2.0 are explicit:

```python
SUPPORTED_SCHEMA_VERSIONS = frozenset({"2"})
```

If the actual current release manifest proves a different schema during execution preflight, stop and update the design/plan before code rather than widening this set silently.

- [ ] **Step 3: Run tests and observe failure**

```bash
python -m pytest tests/consumer/test_integrity.py -q
```

- [ ] **Step 4: Implement layered verification**

Order inside managed validation:

```text
parse manifest
parse SHA256SUMS
hash manifest and SHA256SUMS for API digest if available
hash DuckDB for API digest if available
hash DuckDB against SHA256SUMS
open DuckDB read-only
require arancel_mx view + dataset_release
require supported schema
require dataset_version/schema alignment
return DatasetInfo
```

Raw `json.JSONDecodeError`, `OSError`, and `duckdb.Error` are chained into the documented dataset errors. Unsupported schema uses `DatasetSchemaError`; checksum/version corruption uses `DatasetIntegrityError`.

- [ ] **Step 5: Pass focused and existing certification tests**

```bash
python -m pytest tests/consumer/test_integrity.py tests/certification/test_consumer.py -q
```

- [ ] **Step 6: Commit**

```bash
git add src/arancel_mx/consumer/integrity.py tests/consumer/conftest.py tests/consumer/test_integrity.py
git commit -m "feat: validate consumer dataset integrity"
```

---

### Task 7: Deterministic code normalization, lookup, search, hierarchy and provenance

**Files:**
- Create: `src/arancel_mx/consumer/query.py`
- Test: `tests/consumer/test_query.py`

**Interfaces:**

```python
def normalize_code(value: str) -> str: ...

def lookup(connection, code: str) -> TariffRecord: ...
def search(connection, text: str, *, limit: int) -> tuple[SearchResult, ...]: ...
def parent(connection, code: str) -> TariffRecord | None: ...
def children(connection, code: str) -> tuple[TariffRecord, ...]: ...
def provenance(connection, code: str) -> tuple[ProvenanceRecord, ...]: ...
```

- [ ] **Step 1: Write exact normalization/query tests**

Required normalization tests:

```text
test_normalize_accepts_2_4_6_8_10_digits
test_normalize_removes_unambiguous_spaces_dots_and_hyphens
test_normalize_rejects_letters
test_normalize_rejects_lengths_other_than_2_4_6_8_10
test_normalize_rejects_empty_value
```

Required query tests:

```text
test_lookup_returns_exact_current_record
test_lookup_absent_valid_code_raises_record_not_found
test_lookup_invalid_code_raises_invalid_code
test_search_exact_code_ranks_first
test_search_code_prefix_ranks_before_description_only
test_search_is_case_insensitive
test_search_is_accent_insensitive
test_search_token_ranking_is_deterministic
test_search_limit_must_be_positive
test_search_same_inputs_same_order
test_parent_hs2_returns_none
test_parent_hs4_returns_hs2
test_parent_hs6_returns_hs4
test_parent_fraction_returns_hs6
test_parent_nico_returns_fraction
test_children_returns_only_direct_children_sorted_by_code
test_provenance_returns_primary_first_then_deterministic_source_order
```

Search scoring for 0.2.0 is fixed and documented in the code to guarantee deterministic behavior:

```text
1000 exact normalized code
700 code prefix
300 + 25 per matched normalized description token
+ 5 if all query tokens are present
```

Tie-breakers: score descending, code ascending, description ascending.

Accent normalization uses Unicode NFKD and removes combining marks; it does not add fuzzy edit-distance matching.

- [ ] **Step 2: Observe failures**

```bash
python -m pytest tests/consumer/test_query.py -q
```

- [ ] **Step 3: Implement parameterized read-only SQL**

Never concatenate user text directly into SQL. Use positional parameters for exact/prefix searches and normalized description comparison. Convert DB rows in one `_row_to_tariff_record()` helper so every query returns the same public shape.

Parent mapping is exact:

```python
PARENT_LEVEL = {
    "hs2": None,
    "hs4": ("hs2", "hs2"),
    "hs6": ("hs4", "hs4"),
    "fraccion8": ("hs6", "hs6"),
    "nico10": ("fraccion8", "fraccion8"),
}
```

- [ ] **Step 4: Pass focused tests**

```bash
python -m pytest tests/consumer/test_query.py -q
```

- [ ] **Step 5: Commit**

```bash
git add src/arancel_mx/consumer/query.py tests/consumer/test_query.py
git commit -m "feat: add deterministic consumer queries"
```

---

### Task 8: Dataset manager transaction and public `Dataset` facade

**Files:**
- Create: `src/arancel_mx/consumer/manager.py`
- Create: `src/arancel_mx/consumer/dataset.py`
- Modify: `src/arancel_mx/consumer/__init__.py`
- Modify: `src/arancel_mx/__init__.py`
- Test: `tests/consumer/test_manager.py`
- Test: `tests/consumer/test_dataset.py`

**Interfaces:**

`DatasetManager`:

```python
class DatasetManager:
    def __init__(self, config: ConsumerConfig, *, session: requests.Session | None = None) -> None: ...
    def ensure(self, tag: str | None = None) -> Path: ...
    def update(self) -> tuple[Literal["downloaded", "no_change"], Path]: ...
    def list_local(self) -> tuple[str, ...]: ...
    def list_remote(self) -> tuple[str, ...]: ...
    def selected_path(self, tag: str | None = None) -> Path: ...
    def verify(self, tag: str | None = None, *, online: bool = False, bundle: bool = False) -> DatasetInfo: ...
```

`Dataset`:

```python
class Dataset:
    @classmethod
    def latest(cls, *, offline: bool | None = None, cache_dir: str | Path | None = None, timeout: float | None = None) -> "Dataset": ...

    @classmethod
    def version(cls, tag: str, *, offline: bool | None = None, cache_dir: str | Path | None = None, timeout: float | None = None) -> "Dataset": ...

    @classmethod
    def open(cls, path: str | Path) -> "Dataset": ...

    @property
    def info(self) -> DatasetInfo: ...

    def lookup(self, code: str) -> TariffRecord: ...
    def search(self, text: str, *, limit: int = 20) -> tuple[SearchResult, ...]: ...
    def parent(self, code: str) -> TariffRecord | None: ...
    def children(self, code: str) -> tuple[TariffRecord, ...]: ...
    def provenance(self, code: str) -> tuple[ProvenanceRecord, ...]: ...
    def connect(self): ...
```

- [ ] **Step 1: Write failing manager transaction tests**

Required manager tests:

```text
test_ensure_latest_resolves_once_and_pins_exact_release
test_ensure_downloads_manifest_then_sha256sums_then_duckdb
test_ensure_checks_github_digest_and_checksum_before_promotion
test_ensure_reuses_existing_verified_cache_without_redownload
test_ensure_failed_checksum_never_promotes
test_ensure_invalid_manifest_never_promotes
test_ensure_corrupt_duckdb_never_promotes
test_ensure_latest_change_during_operation_cannot_mix_release_assets
test_update_downloads_newer_release_without_deleting_old
test_update_returns_no_change_when_local_latest_matches_remote
test_verify_default_is_local_only
test_verify_online_compares_exact_remote_release_metadata
test_verify_bundle_fetches_all_six_assets_into_temporary_certification_area
```

For the latest-change race test, fake the release API so the first call returns `data-2026.08.11` and a hypothetical second call would return another tag; assert manager calls release resolution only once and every download URL comes from the first `DataRelease` object.

- [ ] **Step 2: Write failing Dataset facade tests**

Required Dataset tests:

```text
test_root_package_exports_dataset
test_dataset_open_validates_local_file_read_only
test_dataset_open_local_info_does_not_claim_release_verification
test_dataset_version_uses_exact_tag
test_dataset_latest_delegates_to_manager
test_dataset_lookup_returns_tariff_record
test_dataset_search_returns_tuple_of_search_results
test_dataset_parent_children_and_provenance_delegate_to_query_layer
test_dataset_connect_context_manager_closes_connection
```

- [ ] **Step 3: Run and observe failure**

```bash
python -m pytest tests/consumer/test_manager.py tests/consumer/test_dataset.py -q
```

- [ ] **Step 4: Implement manager transaction exactly**

Staging path must be a unique directory inside the release cache root, for example:

```text
<cache>/.staging/data-2026.08.11-<uuid>/
```

Transaction under cache lock:

```text
if already verified -> validate local verified metadata -> reuse
else resolve exact release once
-> download manifest.part
-> download SHA256SUMS.part
-> validate both metadata artifacts and available API digests
-> download arancel_mx.duckdb.part
-> verify API digest if available
-> verify SHA256SUMS checksum
-> validate DuckDB schema/release metadata
-> promote manifest/SHA256SUMS/DuckDB atomically
-> write verified.json last
-> clean staging directory
```

`bundle=True` additionally retrieves CSV/JSON/official sources and validates all six release digests/checksums without replacing the normal three-file managed cache contract.

- [ ] **Step 5: Implement Dataset as a small wrapper**

`Dataset.open()` uses `validate_duckdb(... release_verified=False, github_digest_state="not_applicable")`. Managed instances receive validated cache metadata and use `source="managed-cache"`.

Every `Dataset.connect()` call delegates to existing `arancel_mx.storage.duckdb.connect(path, read_only=True)`.

- [ ] **Step 6: Pass focused tests**

```bash
python -m pytest tests/consumer/test_manager.py tests/consumer/test_dataset.py -q
```

- [ ] **Step 7: Pass all consumer tests created so far**

```bash
python -m pytest tests/consumer -q
```

- [ ] **Step 8: Commit**

```bash
git add src/arancel_mx/__init__.py src/arancel_mx/consumer tests/consumer/test_manager.py tests/consumer/test_dataset.py
git commit -m "feat: expose verified Dataset consumer API"
```

---

### Task 9: Strict offline behavior, destructive failures, and cache-upgrade reuse

**Files:**
- Test: `tests/consumer/test_offline.py`
- Test: `tests/consumer/test_faults.py`
- Test: `tests/consumer/test_upgrade_cache.py`
- Modify only if tests expose missing behavior: `src/arancel_mx/consumer/manager.py`, `cache.py`, `integrity.py`, `dataset.py`

**Interfaces:**
- No new public API.
- Locks down negative behavior before CLI work begins.

- [ ] **Step 1: Write offline tests**

```text
test_latest_offline_never_constructs_or_calls_network_client
test_latest_offline_selects_newest_verified_local_tag
test_latest_offline_without_cache_raises_dataset_unavailable_with_download_guidance
test_version_offline_requires_requested_verified_tag
test_lookup_search_parent_children_provenance_work_with_socket_network_blocked
test_local_verify_works_with_socket_network_blocked
```

Use a monkeypatch that raises immediately if `requests.Session.request` or `socket.create_connection` is invoked.

- [ ] **Step 2: Write destructive/failure-state tests**

```text
test_wrong_sha256_leaves_no_verified_json
test_truncated_download_leaves_no_verified_json
test_invalid_sha256sums_leaves_no_verified_json
test_invalid_json_manifest_leaves_no_verified_json
test_manifest_missing_required_field_leaves_no_verified_json
test_unsupported_schema_leaves_no_verified_json
test_manifest_version_mismatch_leaves_no_verified_json
test_corrupt_duckdb_leaves_no_verified_json
test_remote_missing_asset_leaves_no_verified_json
test_duplicate_remote_asset_leaves_no_verified_json
test_partial_part_from_killed_process_is_cleanable
test_concurrent_downloads_end_with_one_valid_verified_cache
test_verified_cache_survives_network_failure
test_old_supported_data_release_can_be_opened_by_new_package
```

Every failure test must assert the documented exception class and `not paths.verified.exists()`.

- [ ] **Step 3: Write cache-upgrade survival test**

Simulate package reinstall boundary without deleting the cache by constructing a verified cache, destroying all manager/Dataset instances, then creating new instances against the same `ARANCEL_MX_CACHE_DIR`. Assert local metadata and queries still work without network.

```python
def test_verified_cache_survives_new_consumer_process(tmp_path, verified_cache):
    # fixture creates durable verified cache under tmp_path
    config = resolve_config(cache_dir=tmp_path, offline=True)
    dataset = Dataset.latest(offline=True, cache_dir=config.cache_dir)
    assert dataset.lookup("01012101").code == "01012101"
```

The later package-release matrix repeats this with an actual previous-PyPI-package upgrade starting at 0.2.1.

- [ ] **Step 4: Run negative suite and observe any failures**

```bash
python -m pytest tests/consumer/test_offline.py tests/consumer/test_faults.py tests/consumer/test_upgrade_cache.py -q
```

Expected before fixes: any gaps fail with the specific unwanted behavior; do not loosen assertions.

- [ ] **Step 5: Implement only the minimal fixes exposed by failing tests**

Do not add network fallback in offline mode. Do not promote partial cache. Do not delete previously verified versions during update.

- [ ] **Step 6: Re-run negative suite and full consumer suite**

```bash
python -m pytest tests/consumer/test_offline.py tests/consumer/test_faults.py tests/consumer/test_upgrade_cache.py -q
python -m pytest tests/consumer -q
```

Expected: pass.

- [ ] **Step 7: Run full repository regression before handoff to CLI plan**

```bash
python -m pytest -q
python -m build
```

Expected: zero test failures and successful wheel/sdist build.

- [ ] **Step 8: Commit**

```bash
git add src/arancel_mx/consumer tests/consumer
git commit -m "test: lock down consumer failure and offline semantics"
```

---

## Plan A completion gate

Do not start Plan B until all commands below are freshly green on the implementation branch:

```bash
python -m pytest tests/consumer -q
python -m pytest tests/test_cli.py tests/test_public_distribution.py tests/test_import_boundaries.py tests/certification/test_consumer.py -q
python -m pytest -q
python -m build
```

At this gate, the Python API and cache/download behavior exist, but no claim is made about TestPyPI, PyPI, external OS/Python certification, or production readiness.
