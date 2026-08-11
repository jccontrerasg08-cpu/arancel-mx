# PyPI Consumer Distribution and External Certification Design

**Status:** Approved design, written specification pending final user review  
**Repository:** `jccontrerasg08-cpu/arancel-mx`  
**Baseline:** `main` at `23a2dd937d6699e2663245eca0270a11ea34a0aa`  
**Target package release:** `arancel-mx 0.2.0`  
**Primary goal:** make `pip install arancel-mx` a reliable, consumer-first installation path whose production PyPI publication is blocked until an exact built distribution has passed TestPyPI and external certification.

## 1. Goal

`arancel-mx` must become usable by a person who has never cloned the repository and does not know the internal ETL/release implementation.

A successful external-user journey is:

```text
clean machine
  -> install arancel-mx from PyPI
  -> run arancel-mx doctor
  -> discover/download a verified data-* release
  -> query tariff data through CLI or Python
  -> reuse the verified cache offline
  -> upgrade arancel-mx without losing the cache
```

The production package must not be uploaded to PyPI merely because repository CI is green. The publication path is fail-closed and must prove the exact distributions through TestPyPI before production approval.

## 2. Core architectural decision

Code and tariff data retain independent lifecycles.

### Python package lifecycle

```text
arancel-mx 0.2.0
arancel-mx 0.2.1
arancel-mx 0.3.0
...
```

Distribution channel:

```text
TestPyPI -> external certification -> manual approval -> PyPI
```

### Dataset lifecycle

```text
data-2026.08.10
data-2026.08.11
data-YYYY.MM.DD
...
```

Distribution channel:

```text
GitHub Releases
```

The large public dataset is not embedded in the Python wheel. The wheel contains code and small package resources only. `Dataset` downloads a verified public DuckDB release on demand.

Package tags use a namespace that cannot collide with data tags:

```text
pkg-v0.2.0rc1
pkg-v0.2.0rc2
pkg-v0.2.0
```

No GitHub Release is created for `pkg-v*` tags. This preserves the existing GitHub `releases/latest` contract for public `data-*` assets.

## 3. Non-goals for 0.2.0

The first PyPI consumer release does not:

- embed the 30+ MB DuckDB dataset in the wheel;
- replace GitHub Releases as the authoritative dataset distribution channel;
- create GitHub Releases for Python package versions;
- provide a web service or hosted REST API;
- add fuzzy/semantic/LLM search as part of the stable public API;
- attempt to classify goods legally on behalf of a user;
- replace the existing maintainer build, reconciliation, or release commands;
- claim support for interpreters, operating systems, or architectures that have not passed the release matrix;
- use GitHub Packages as the Python package index;
- use persistent PyPI/TestPyPI API tokens when Trusted Publishing is available.

A future GHCR container can be additive, but it is outside the 0.2.0 PyPI gate.

## 4. Current baseline

At the approved baseline:

- package metadata declares `name = "arancel-mx"`, version `0.1.0`, Python `>=3.11`, Apache-2.0, runtime dependencies, and the `arancel-mx` console entrypoint;
- `src/arancel_mx/__init__.py` exposes only `__version__` as public API;
- the CLI exposes maintainer-oriented `build`, `check-updates`, `update`, `reconcile`, and `release` commands;
- CI builds wheel and sdist and smoke-tests both in a clean virtual environment outside the checkout;
- that clean-install test removes `PYTHONPATH`/`PYTHONHOME`, checks `import arancel_mx`, module/console help, and packaged source registry data;
- the public DuckDB contains the validated public `arancel_mx` view and public provenance/audit tables;
- the data pipeline already publishes immutable `data-*` releases with the exact six-asset contract and provenance controls.

The 0.2.0 work extends these foundations rather than replacing them.

## 5. Public Python API contract

The initial stable consumer boundary is deliberately small.

```python
from arancel_mx import Dataset

latest = Dataset.latest()
record = latest.lookup("01012101")
results = latest.search("refrigeradores")
parent = latest.parent("01012101")
children = latest.children("0101")
provenance = latest.provenance("01012101")
```

Version-pinned data:

```python
db = Dataset.version("data-2026.08.11")
```

Explicit local data:

```python
db = Dataset.open("/path/to/arancel_mx.duckdb")
```

Offline operation:

```python
db = Dataset.latest(offline=True)
```

Advanced access is available without making DuckDB internals the primary API:

```python
with db.connect() as connection:
    connection.sql("SELECT * FROM arancel_mx LIMIT 5")
```

### 5.1 Public return models

Consumer methods return typed immutable models rather than undocumented raw tuples.

Minimum public models:

- `TariffRecord`
- `SearchResult`
- `ProvenanceRecord`
- `DatasetInfo`

The stable record surface includes, where applicable:

```text
code
level
description
unit_name
igi_text
igi_kind
igi_value
ige_text
ige_kind
ige_value
parent_code
dataset_version
schema_version
effective_from
effective_to
is_current
```

Fields not applicable at a hierarchy level are `None`; HS descriptive levels do not inherit tariff rates.

### 5.2 Public API stability

`Dataset`, public models, documented exception classes, and documented method signatures form the 0.2.x compatibility surface.

Internal SQL, table joins, HTTP implementation, retry implementation, cache layout metadata, and helper modules remain private and may change without becoming public API.

## 6. Package version source of truth

`pyproject.toml` remains the single package-version source.

`src/arancel_mx/__init__.py` must derive `__version__` from installed distribution metadata using `importlib.metadata.version("arancel-mx")` rather than duplicating a literal version.

The release workflow rejects any `pkg-vX.Y.Z` tag whose normalized version differs from `project.version` in `pyproject.toml`.

The package follows PEP 440/SemVer-compatible versioning during 0.x:

- `0.2.0rcN`: release candidates, TestPyPI only;
- `0.2.0`: first approved public consumer release;
- `0.2.x`: compatible bug/security fixes;
- `0.3.0`: intentionally expanded 0.x consumer surface;
- `1.0.0`: only after the public API/deprecation policy is mature.

## 7. CLI contract

Consumer commands become first-class while existing engineering commands remain available.

### 7.1 Consumer commands

```text
arancel-mx doctor

arancel-mx data status
arancel-mx data download
arancel-mx data update
arancel-mx data list
arancel-mx data path
arancel-mx data verify

arancel-mx lookup CODE
arancel-mx search TEXT
arancel-mx parent CODE
arancel-mx children CODE
arancel-mx provenance CODE
```

Common consumer options:

```text
--dataset data-YYYY.MM.DD
--offline
--format table|json|csv
--limit N
```

JSON and CSV output must be deterministic and machine-readable. Human table output is convenience output, not the machine contract.

### 7.2 Maintainer commands

The existing commands remain:

```text
build
check-updates
update   # deprecated read-only alias
reconcile
release
```

Documentation separates these under a maintainer/engineering section so a new user is not required to understand the official build pipeline to query data.

## 8. Dataset discovery

`Dataset.latest()` must resolve an exact `data-*` tag before downloading assets.

The resolver:

1. queries the public GitHub release API;
2. accepts only non-draft, non-prerelease releases whose tag matches `^data-\d{4}\.\d{2}\.\d{2}$`;
3. resolves one exact tag;
4. validates the expected six release asset names;
5. pins all subsequent asset URLs to the exact tag/release identity;
6. never mixes `latest` URLs during a multi-file transaction.

The six expected public assets remain exactly:

```text
arancel_mx.duckdb
arancel_mx.csv
arancel_mx.json
manifest.json
SHA256SUMS
official-sources.tar.gz
```

A package release, unrelated GitHub release, draft, prerelease, malformed data tag, missing asset, or duplicated asset must not be accepted as a dataset.

## 9. Cache and filesystem behavior

Use `platformdirs` for cross-platform locations rather than hand-built home-directory assumptions.

Conceptual user cache:

```text
<platform cache>/arancel-mx/
  releases.json
  data-2026.08.11/
    arancel_mx.duckdb
    manifest.json
    SHA256SUMS
    verified.json
```

Normal consumer download stores only the assets required to validate and use the DuckDB. `data verify --bundle` may fetch/verify the full six-asset release when a user wants full release certification.

Properties:

- each `data-*` version is isolated;
- a verified version is never silently overwritten;
- temporary files use `.part`/temporary names;
- promotion into the verified cache uses atomic `os.replace` semantics on the same filesystem;
- concurrent download/update operations use a cross-platform file lock;
- failed downloads never become valid cache entries;
- stale temporary files can be safely cleaned without deleting verified versions;
- Unicode paths, spaces, custom cache roots, and read-only failure paths are tested.

Supported environment variables:

```text
ARANCEL_MX_CACHE_DIR
ARANCEL_MX_DATASET
ARANCEL_MX_OFFLINE
ARANCEL_MX_TIMEOUT
```

CLI flags override environment variables; environment variables override defaults.

## 10. Download and integrity transaction

Normal transaction:

```text
resolve exact data tag
  -> validate remote asset set
  -> download manifest.json to temporary path
  -> download SHA256SUMS to temporary path
  -> validate manifest/schema/version relationship
  -> download arancel_mx.duckdb as temporary file
  -> verify expected SHA256
  -> open DuckDB read-only
  -> verify required public tables/view
  -> verify dataset_release metadata agrees with the resolved version/schema
  -> atomic promotion
  -> write verified.json last
```

HTTP downloads are streamed, bounded by configurable timeouts, and use limited retries for retryable GET failures such as transient 429/5xx responses. Permanent integrity errors are not retried as though they were network errors.

No failed checksum, truncated body, invalid manifest, unsupported schema, invalid DuckDB, or mismatched dataset version may enter verified cache state.

## 11. Offline semantics

`Dataset.latest(offline=True)` means the newest locally verified dataset, not "try the network and fall back silently."

Offline mode performs no network access.

If no verified local dataset exists, it raises `DatasetUnavailableError` with actionable CLI guidance.

Once a dataset is downloaded and verified, the following must work with network access disabled:

```text
lookup
search
parent
children
provenance
data status
data path
data verify
```

## 12. Query semantics for 0.2.0

Supported code levels remain:

```text
hs2
hs4
hs6
fraccion8
nico10
```

### 12.1 `lookup`

- exact normalized code match;
- accepts display punctuation/spacing only when normalization is unambiguous;
- invalid-length/non-numeric identifiers raise `InvalidCodeError`;
- valid but absent codes raise `RecordNotFoundError`.

### 12.2 `search`

0.2.0 search supports:

- exact code;
- code prefix;
- case-insensitive description text;
- accent-insensitive description matching;
- token-based deterministic ranking;
- explicit result limit.

Fuzzy/semantic search is deferred so `Dataset.search()` can later improve ranking without changing its high-level contract.

### 12.3 Hierarchy

`parent()` and `children()` operate only through validated canonical relationships and return documented level-aware records.

### 12.4 Provenance

`provenance()` exposes the public source/provenance records already present in the distributable database without presenting them as legal advice or legal signatures.

## 13. Public exception hierarchy

The package does not leak raw `requests`, filesystem, JSON, or DuckDB implementation exceptions as the primary consumer contract.

```text
ArancelMXError

DatasetError
  DatasetUnavailableError
  DatasetDownloadError
  DatasetIntegrityError
  DatasetSchemaError
  DatasetVersionNotFoundError

QueryError
  InvalidCodeError
  RecordNotFoundError
```

Exception chaining retains the underlying cause for debugging while CLI output presents concise actionable messages.

## 14. `doctor`

`arancel-mx doctor` is the support and self-diagnosis entrypoint.

Human output checks:

```text
package version
Python version
OS / architecture
installation metadata
console entrypoint
packaged source registry
cache path and writability
network reachability when not offline
latest valid data release resolution
manifest/schema compatibility
checksum state
DuckDB open/read-only state
query smoke test
offline-cache readiness
```

`arancel-mx doctor --json` returns structured diagnostic output suitable for bug reports/CI.

Diagnostics must not print tokens, authorization headers, cookies, unrelated environment variables, or private file contents.

`doctor` distinguishes:

```text
HEALTHY
DEGRADED  # optional network unavailable but verified offline data is usable
UNHEALTHY
```

## 15. Packaging metadata and public distribution quality

Before the first PyPI release, `pyproject.toml` is expanded with complete public metadata:

- maintainer identity represented by the public repository account;
- keywords;
- Python 3.11, 3.12, 3.13, and 3.14 classifiers only after matrix certification;
- OS-independent classifier;
- Apache Software License classifier/modern SPDX metadata as supported by current packaging standards;
- project URLs for repository, issues, documentation, changelog, and data releases;
- development status appropriate for 0.x.

Add:

```text
CHANGELOG.md
src/arancel_mx/py.typed
```

The PEP 561 marker is shipped only when the public consumer modules/models are actually type-checked and annotated sufficiently to make the claim useful.

README rendering must be validated before publication. Build validation includes at least:

```text
python -m build
twine check dist/*
check-wheel-contents dist/*.whl
```

The sdist must independently contain all source/package metadata needed to rebuild the wheel in an isolated clean environment.

## 16. Dependency compatibility

The release gate tests both:

1. the normal latest resolver allowed by package dependency ranges; and
2. supported dependency floors that are explicitly promised, especially `duckdb==1.1.0` for public DuckDB compatibility.

`pip check` is mandatory after installation.

The release matrix determines what Python versions may be advertised. If Python 3.14 or another claimed version cannot install all required dependencies and pass consumer tests, the package must either fix the incompatibility or narrow `requires-python`/classifiers before publication.

No support claim is documentary only.

## 17. Pull-request CI versus release certification

Normal PR CI must remain reasonably fast while still catching packaging regressions.

### 17.1 Required PR/main checks

Existing unit/integration/build checks remain, plus:

- public consumer API tests;
- cache/download tests with local HTTP fixtures/mocks at the network boundary;
- destructive integrity/error tests;
- wheel and sdist clean-install certification;
- metadata/render/package-content checks;
- Linux minimum/latest Python edge coverage;
- at least one Windows consumer smoke and one macOS consumer smoke;
- existing DuckDB 1.1.0 compatibility probe;
- whitespace/security/public-distribution tests.

### 17.2 Release-only full matrix

The expensive matrix runs only for `pkg-v*` candidates/finals and exercises the artifact after TestPyPI publication.

Blocking matrix:

```text
                     CPython
                 3.11 3.12 3.13 3.14
Ubuntu x64        yes  yes  yes  yes
Windows x64       yes  yes  yes  yes
macOS ARM64       yes  yes  yes  yes
macOS Intel       yes  yes  yes  yes
```

Initial GitHub-hosted macOS labels are `macos-15` for ARM64 and `macos-15-intel` for Intel, subject to re-verification immediately before implementation because hosted-runner labels are time-sensitive.

Windows ARM64 and additional Linux ARM64 jobs may run as non-blocking canaries where runner availability/cost permits. Preview runner failures do not redefine the blocking support claim.

## 18. Installation-mode certification

Release certification validates both distributions and common user installation tools.

Required modes:

```text
pip wheel install
pip source install (--no-binary=arancel-mx)
pip binary-only install (--only-binary=:all:)
pipx CLI install
uv pip install
uv tool install
```

The package is pure Python, but dependency/platform resolution is still tested on every blocking OS/Python combination.

No consumer certification job may rely on an editable checkout.

## 19. TestPyPI artifact acquisition

External certification must prove the package came from TestPyPI without allowing local checkout files to mask problems.

Primary secure flow per distribution type:

```text
clean runner
  -> no source checkout in consumer job
  -> pip download --no-deps --index-url https://test.pypi.org/simple arancel-mx==VERSION
  -> verify downloaded wheel/sdist SHA256 against the build artifact digest
  -> install that exact downloaded distribution in a fresh environment
  -> resolve normal runtime dependencies from PyPI
  -> execute consumer certification
```

A dedicated resolver smoke may additionally exercise the PyPA-documented TestPyPI + PyPI dependency-index pattern for the candidate version, but the digest-verified download is the authoritative proof that the `arancel-mx` distribution itself came from TestPyPI.

This avoids treating `--extra-index-url` as the only provenance control.

## 20. Build-once publication invariant

A final package version is built once.

```text
exact pkg-vX.Y.Z commit
  -> build wheel + sdist once
  -> generate SHA256 record
  -> upload one immutable GitHub Actions artifact
  -> publish those exact bytes to TestPyPI
  -> download back from TestPyPI and verify SHA256
  -> certify external consumers
  -> manual production approval
  -> retrieve the original Actions artifact
  -> verify SHA256 again
  -> publish those exact bytes to PyPI
```

No second production rebuild occurs between TestPyPI certification and PyPI upload.

If source changes are required after a failed candidate, a new version/candidate is required. Existing uploaded versions are not overwritten.

## 21. Release-candidate lifecycle

Iterative candidates use PEP 440 prereleases:

```text
0.2.0rc1
0.2.0rc2
...
```

Each candidate may be published to TestPyPI and run through the matrix. Release-candidate tags never publish to production PyPI.

When a candidate is accepted, the source version becomes `0.2.0`, and the final `pkg-v0.2.0` build itself is uploaded to TestPyPI and must pass the same certification. The production PyPI upload uses that same final build artifact.

Passing `rcN` alone is not sufficient evidence for uploading separately built final bytes.

## 22. GitHub Actions workflow architecture

Two workflow responsibilities remain separated.

### 22.1 `.github/workflows/python-package-preflight.yml`

Purpose: PR/main packaging quality without registry mutation.

Permissions:

```yaml
permissions:
  contents: read
```

No `id-token: write`, no PyPI/TestPyPI publication, no package tag creation.

### 22.2 `.github/workflows/publish-python-package.yml`

Trigger:

```text
push of pkg-v* tags only
```

No production `workflow_dispatch` trigger is required for 0.2.0. Reducing arbitrary trigger paths narrows the Trusted Publisher boundary.

Conceptual jobs:

```text
validate-tag-and-version
  -> build-once
  -> inspect-distributions
  -> publish-testpypi
  -> verify-testpypi-roundtrip
  -> external-certification-matrix
  -> production-approval
  -> publish-pypi
  -> post-publish-certification
```

Release candidates stop before `publish-pypi`.

Workflow default permissions remain `contents: read` or empty/minimal. Only the TestPyPI/PyPI publishing jobs receive `id-token: write`.

Every third-party GitHub Action is pinned by full commit SHA, consistent with the repository supply-chain policy. The exact current upstream SHA for `pypa/gh-action-pypi-publish` and supporting Actions is re-verified immediately before implementation rather than freezing a stale design-time tag.

## 23. Trusted Publishing and GitHub environments

Use two separately configured PyPI Trusted Publishers:

```text
TestPyPI project: arancel-mx
GitHub owner: jccontrerasg08-cpu
Repository: arancel-mx
Workflow: publish-python-package.yml
Environment: testpypi
```

```text
PyPI project: arancel-mx
GitHub owner: jccontrerasg08-cpu
Repository: arancel-mx
Workflow: publish-python-package.yml
Environment: pypi
```

GitHub environments:

### `testpypi`

- no permanent package credential;
- OIDC Trusted Publishing only;
- no required manual approval unless a future threat model requires it.

### `pypi`

- OIDC Trusted Publishing only;
- required human reviewer/approval;
- production deployment must be restricted to the release workflow/tag path as strongly as GitHub environment rules allow;
- no job can reach the production upload before every external certification dependency is successful.

No repository secret named `PYPI_TOKEN`, `TEST_PYPI_TOKEN`, `.pypirc` password, username/password, or long-lived package credential is introduced.

PyPI Trusted Publishing documentation notes that the workflow itself becomes part of the trust boundary. Changes to `publish-python-package.yml`, package versioning/release validation, or related publication scripts therefore require the same high-scrutiny review as credential-bearing infrastructure.

## 24. Package-name preflight

Immediately before configuring pending publishers and before first live publication:

- verify the normalized `arancel-mx` project name on PyPI;
- verify the normalized project name on TestPyPI;
- verify the repository metadata uses the same normalized distribution name;
- stop if the PyPI name is owned by an unrelated project.

A web search returning no project is not treated as a name reservation. PyPI pending Trusted Publishers do not reserve a project name until first use.

If the name is unexpectedly unavailable, implementation stops for an explicit naming decision. It must not automatically publish under a lookalike/typosquatting name.

## 25. PyPI attestations and provenance

Use the current PyPA Trusted Publishing action behavior that emits PEP 740-compatible attestations where supported.

Package integrity evidence therefore includes:

```text
source tag/commit identity
build artifact SHA256
GitHub Actions artifact identity
TestPyPI roundtrip SHA256
PyPI distribution SHA256
PyPI Trusted Publisher / PEP 740 publication attestations
```

This package provenance is separate from the GitHub artifact attestations already used for public tariff dataset release assets.

No claim is made that package attestations are legal signatures over Mexican source documents.

## 26. Destructive/error certification

Release readiness includes tests for expected failures, not only happy paths.

Required scenarios:

- no network;
- DNS/connection failure;
- HTTP timeout;
- HTTP 404;
- retryable 429/5xx;
- interrupted/truncated download;
- wrong SHA256;
- invalid `SHA256SUMS` format;
- invalid JSON manifest;
- manifest missing required fields;
- unsupported schema version;
- manifest/version mismatch;
- corrupt DuckDB;
- DuckDB missing required public relation/view;
- remote release missing one of the six assets;
- duplicate asset names in release metadata;
- non-`data-*` release encountered;
- latest release changes during an operation;
- partial `.part` file from a killed process;
- cache directory not writable;
- cache path containing spaces;
- Unicode/`ñ` cache path;
- concurrent download by two processes;
- no verified cache in offline mode;
- verified cache with network unavailable;
- old supported dataset with new package;
- package upgrade with pre-existing verified cache.

Tests must assert both failure type and absence of false verified-cache state.

## 27. External consumer functional certification

Each blocking matrix cell executes a real consumer workflow against the exact TestPyPI candidate.

Minimum sequence:

```text
verify package version
arancel-mx --help
python -m arancel_mx --help
arancel-mx doctor --json
arancel-mx data download
arancel-mx data status
arancel-mx data verify
arancel-mx lookup known-code --format json
arancel-mx search known-term --format json
arancel-mx parent known-code --format json
arancel-mx children known-parent --format json
arancel-mx provenance known-code --format json
Python Dataset.latest() smoke
Python lookup/search/hierarchy/provenance smoke
network-disabled offline smoke using downloaded cache
pip check
```

Known-code/known-term assertions must come from a pinned, validated data release contract or from release metadata discovered by the test. They may not depend on an unverified arbitrary web response.

## 28. Post-PyPI certification

Production publication is followed by a second clean external matrix that installs by exact version from `https://pypi.org`.

This proves public resolver visibility rather than only upload API success.

At minimum it repeats the blocking OS/Python matrix for import, CLI, full dataset/query smoke, and offline operation.

A post-publish failure cannot make already-published bytes disappear. Response policy:

1. fail the workflow;
2. create/update a deterministic `[PACKAGE ALERT]` GitHub Issue for the affected package version;
3. investigate immediately;
4. yank the broken PyPI version if consumer impact warrants it;
5. publish a corrected patch version;
6. never overwrite/reuse the broken version number.

Deleting/replacing published artifacts is not the rollback model.

## 29. Backward/upgrade compatibility

Before 0.2.0 production publication:

- new package must open/query the current public dataset;
- new package must open/query at least the immediately previous supported `data-*` schema-compatible release;
- cache created by the same 0.2.0 candidate must survive reinstall.

Starting with 0.2.1, release certification adds:

```text
install previous PyPI package
create/download verified cache
upgrade to candidate package
reuse cache
run doctor/query/offline suite
```

Schema compatibility policy is explicit. A future dataset schema that is unsupported raises `DatasetSchemaError` rather than producing partial/wrong results.

## 30. Security and privacy properties

Consumer operation:

- requires no GitHub token for public releases;
- sends no user tariff queries to a remote analytics service;
- queries DuckDB locally after download;
- stores no credentials in the cache;
- logs no sensitive headers/cookies;
- does not execute data downloaded from GitHub as Python code;
- opens distributed DuckDB read-only for consumer queries by default.

Publication:

- uses Trusted Publishing OIDC;
- scopes `id-token: write` to publisher jobs only;
- uses protected `main`/tag lifecycle;
- pins third-party actions by full SHA;
- never gives pull-request code production publishing credentials;
- does not use `pull_request_target` for package build/publication.

## 31. Documentation deliverables

0.2.0 must include consumer-first documentation in Spanish and English covering:

```text
pip install arancel-mx
pipx/uv alternatives
first data download
doctor
lookup/search examples
Python Dataset examples
offline usage
pinning a data release
cache location/configuration
integrity verification
package-version vs dataset-version distinction
supported Python/OS matrix
upgrade behavior
troubleshooting
legal/data disclaimer
```

Maintainer documentation separately covers:

```text
package release candidates
TestPyPI
Trusted Publisher setup
GitHub environments
final pkg-v tag
manual PyPI approval
post-publication verification
yanking/patch response
```

README/PyPI documentation must never imply that `pip install arancel-mx` includes the full tariff database inside the wheel.

## 32. Test strategy and TDD boundaries

Implementation follows TDD.

Before adding consumer behavior, tests define:

- public model/API signatures;
- exact code normalization/error behavior;
- resolver acceptance/rejection rules;
- cache atomicity and verification state;
- network retry/error mapping;
- schema and DuckDB validation;
- offline no-network behavior;
- CLI commands/options/output contracts;
- doctor states;
- version/tag synchronization;
- package metadata/content expectations;
- workflow permission/trigger/order contracts.

Network behavior is unit/integration tested against controlled fixtures/local servers. Live TestPyPI/PyPI and public GitHub release tests are separate certification gates rather than replacements for deterministic tests.

## 33. Release workflow failure semantics

Fail closed at every boundary.

Examples:

```text
build/metadata failure -> no TestPyPI upload
TestPyPI upload failure -> no certification
roundtrip digest mismatch -> no certification
one matrix cell failure -> no production environment request
production approval denied -> no PyPI upload
PyPI upload failure -> post-publish suite not considered complete
post-PyPI consumer failure -> package alert / corrective response
```

A skipped required matrix cell is not equivalent to success unless the design explicitly marks that cell as non-blocking canary.

## 34. Manual setup prerequisites

Some first-publication actions require account/UI configuration and cannot be inferred from repository code.

Before the first live TestPyPI candidate:

1. user has separate PyPI and TestPyPI accounts;
2. strong account security/2FA is enabled as required/recommended by the registries;
3. exact `arancel-mx` project-name preflight passes;
4. GitHub environments `testpypi` and `pypi` exist;
5. `pypi` has required manual approval/reviewer rules;
6. pending Trusted Publishers are registered on TestPyPI and PyPI for the exact owner/repository/workflow/environment tuple;
7. no old permanent PyPI/TestPyPI token remains in repository secrets.

These prerequisites are documented and verified before executing the live certification stage.

## 35. Alternatives considered

### A. Publish the existing engineering toolkit immediately as 0.1.0

Rejected. Installation works, but the public API is not yet consumer-first and would make the first PyPI impression weaker than the repository/data foundation warrants.

### B. Embed every data release in the wheel

Rejected. It couples fast-moving official datasets to code releases, inflates Python distribution size, and prevents independent data updates.

### C. Use GitHub Packages as the Python index

Rejected. The public Python distribution target is PyPI/TestPyPI. GitHub remains source/CI/data-release/provenance infrastructure; GHCR may later distribute an optional OCI image.

### D. Build once for TestPyPI and rebuild after tests for PyPI

Rejected. That tests different bytes from production. Final bytes are built once and reused.

### E. Only test local `dist/*.whl`

Rejected. Local smoke tests stay useful, but final certification must retrieve the exact candidate from TestPyPI by name/version and verify its digest.

### F. Require only Linux/Python 3.11

Rejected. The package explicitly targets ordinary external users across Windows, macOS, and Linux and must prove claimed Python-version support.

### G. Make PyPI publication fully automatic after TestPyPI

Rejected for the first production release. The `pypi` environment requires deliberate human approval after all automated gates succeed.

## 36. Acceptance criteria for `arancel-mx 0.2.0`

0.2.0 is ready for production PyPI approval only when all are true:

1. `Dataset` consumer API and typed public models are implemented and documented.
2. Consumer CLI commands (`doctor`, `data`, `lookup`, `search`, `parent`, `children`, `provenance`) pass deterministic tests.
3. Existing maintainer commands remain compatible unless separately documented.
4. Package version has one source of truth and tag/version mismatch fails closed.
5. Consumer cache uses platform-native paths, atomic promotion, locking, and explicit verified state.
6. Exact `data-*` release resolution and six-asset contract validation are implemented.
7. SHA256, manifest, schema, DuckDB, and release-version verification fail closed.
8. Offline operation performs no network requests and works from verified cache.
9. Public exception hierarchy prevents raw implementation exceptions from being the normal API contract.
10. `doctor` provides human and JSON diagnostics without leaking secrets.
11. Wheel and sdist pass clean-install, metadata, README, package-data, and content checks.
12. Runtime dependencies pass `pip check` and promised DuckDB floor compatibility remains executed.
13. PR/main package preflight is green.
14. Final `pkg-v0.2.0` bytes are built once.
15. Those exact wheel/sdist bytes are uploaded to TestPyPI.
16. TestPyPI roundtrip downloads match expected SHA256.
17. Every blocking Windows/Linux/macOS Intel/macOS ARM × Python 3.11-3.14 matrix cell passes.
18. Required pip/pipx/uv and wheel/sdist installation modes pass.
19. Full online data download/query and network-disabled offline smoke pass for external consumers.
20. Destructive/error cases prove failed artifacts never become verified cache.
21. Package/project metadata is complete and accurate.
22. `publish-python-package.yml` is tag-only, least-privileged, and pins third-party actions by full SHA.
23. TestPyPI and PyPI Trusted Publishing use OIDC with no permanent upload token.
24. `pypi` environment requires human approval.
25. Release candidates cannot publish to production PyPI.
26. No GitHub package release is created that could displace the `data-*` latest-release behavior.
27. Production upload re-verifies original build artifact hashes immediately before publish.
28. PyPI publication emits/verifies the supported provenance/attestation evidence provided by the current trusted publishing action.
29. Post-PyPI external installation matrix passes by exact version from PyPI.
30. README/docs/changelog/troubleshooting accurately describe package vs dataset versioning and consumer workflows.

## 37. Pre-implementation verification checklist

Immediately before implementation planning/execution, re-check:

- current `main` SHA and branch freshness;
- current latest `data-*` release and six exact assets;
- current `pyproject.toml` package metadata/version;
- current PyPA TestPyPI/PyPI Trusted Publishing guidance;
- current `pypa/gh-action-pypi-publish` stable release/full commit SHA;
- current GitHub hosted runner labels, especially macOS Intel/ARM;
- Python 3.11-3.14 support for all runtime dependencies;
- current package name availability/ownership on PyPI and TestPyPI before first live publication;
- GitHub environment and ruleset settings that cannot be proven from code;
- no existing PyPI/TestPyPI token secrets;
- no unrelated data schema/legal-source changes mixed into package-consumer work.

## 38. Official implementation references

The implementation plan must prefer current primary documentation and re-verify time-sensitive details before coding:

- Python Packaging User Guide, GitHub Actions publishing:  
  https://packaging.python.org/en/latest/guides/publishing-package-distribution-releases-using-github-actions-ci-cd-workflows/
- PyPI Trusted Publishing:  
  https://docs.pypi.org/trusted-publishers/
- PyPI Trusted Publisher security model:  
  https://docs.pypi.org/trusted-publishers/security-model/
- PyPI project creation through OIDC:  
  https://docs.pypi.org/trusted-publishers/creating-a-project-through-oidc/
- PyPI attestations:  
  https://docs.pypi.org/attestations/
- Python Packaging User Guide, TestPyPI:  
  https://packaging.python.org/en/latest/guides/using-testpypi/
- GitHub hosted runners:  
  https://docs.github.com/en/actions/reference/runners/github-hosted-runners
- GitHub runner images/labels:  
  https://github.com/actions/runner-images

## 39. Completion definition

The project is not declared "PyPI-ready" when code is merely merged.

The states are:

```text
design approved
  -> implementation complete
  -> deterministic CI verified
  -> TestPyPI configured
  -> release candidate externally certified
  -> final 0.2.0 TestPyPI externally certified
  -> manual production approval
  -> PyPI published
  -> post-PyPI externally certified
  -> 0.2.0 production-certified
```

Documentation must use the correct state and must not claim live PyPI/TestPyPI certification before the corresponding real external run succeeds.
