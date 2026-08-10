# Production certification and Docusaurus documentation design

Date: 2026-08-10

## Objective

Finish `arancel-mx` as a stable, independently consumable, production-ready open-source data package by adding a final certification layer around the already-hardened official-data pipeline, then publish a static documentation site with Docusaurus without coupling Node.js to the tariff ETL/runtime.

The certification phase must prove more than "CI is green". It must prove that:

1. a third party can install the built Python artifacts in a clean environment;
2. the console entrypoint and module entrypoint work outside the repository checkout;
3. the six-file dataset bundle is internally consistent and independently verifiable;
4. DuckDB/CSV/JSON expose equivalent logical records;
5. source archives and manifest provenance reconstruct the exact official bytes used;
6. unchanged source state resolves to `no_change` rather than a redundant release;
7. expected corruption, source drift, network boundary violations, tag collisions, and publication failures fail closed;
8. the real GitHub `contents: write` and `issues: write` boundaries work through temporary isolated mutations and clean up after themselves;
9. the documentation site builds reproducibly in Spanish and English and deploys independently from production data publication;
10. every implementation PR is preceded by an explicit double-check of assumptions, current repository state, official documentation, diff scope, and verification evidence.

This design extends, rather than replaces, `2026-08-10-production-hardening-automation-design.md`.

## Non-goals

- Do not turn Docusaurus into an application backend.
- Do not move official data generation into Node.js.
- Do not publish test releases under `data-YYYY.MM.DD`.
- Do not mutate an existing immutable/public dataset release during certification.
- Do not weaken fail-closed legal reconciliation to make tests pass.
- Do not add external PATs if the built-in `GITHUB_TOKEN` can perform the required operation safely.
- Do not version Docusaurus documentation once per daily dataset release.
- Do not claim a stable Python API beyond interfaces actually implemented and tested.

## Existing baseline to preserve

The current repository already establishes the following production contract:

- Python package `arancel-mx`, Python `>=3.11`;
- console script `arancel-mx = arancel_mx.cli:entrypoint`;
- canonical DuckDB plus CSV, JSON, manifest, checksums, and official source archive;
- six-file public release contract;
- source-first LIGIE/NICO data with legal provenance;
- fail-closed reconciliation against registered official evidence;
- protected `main` with required GitHub Actions `test` status;
- daily `Official data pipeline`;
- build jobs read-only by default;
- publication receives `contents: write` only after a verified build;
- notifier receives `issues: write` only at the notification boundary;
- successful production dry-run #3 on trusted `main` with 214 offline tests and a verified six-file artifact.

Certification must not create a second, competing execution path for the same business rules. It should reuse public verification functions and package entrypoints wherever possible.

## Architecture

The work is split into two sequential subprojects.

### Subproject A: Production Certification Suite

Add a dedicated certification layer that exercises the package and GitHub boundaries without publishing a production dataset.

Logical flow:

```text
protected main
    |
    v
build wheel + sdist
    |
    +--> clean install smoke tests
    +--> CLI/module smoke tests
    +--> Python compatibility matrix
    |
verified dry-run six-file artifact
    |
    +--> manifest/hash/source archive audit
    +--> CSV/JSON/DuckDB equivalence
    +--> read-only DuckDB consumer queries
    +--> deterministic rebuild checks
    +--> no-change replay
    +--> fault injection suite
    |
GitHub certification workflow
    |
    +--> temporary draft release boundary
    |       create -> upload tiny fixtures -> verify -> delete -> verify absence
    |
    +--> temporary issue boundary
            create -> update/comment -> close -> verify closed
```

### Subproject B: Docusaurus documentation site

After certification is stable, add a static Docusaurus site under `website/`.

```text
Python/data runtime                    Documentation runtime
-------------------                    ---------------------
src/                                   website/
scripts/                               docusaurus.config.ts
tests/                                 sidebars.ts
requirements/                          package.json + lock
.github/workflows/official-*           src/ + static/ + i18n/
        |                                       |
        v                                       v
GitHub Releases                         GitHub Pages
```

The documentation workflow never receives `contents: write` for dataset publication and never calls release-publishing scripts.

## Subproject A: certification coverage

### 1. Package installation smoke tests

Build the actual wheel and sdist, then install each into a fresh virtual environment outside the repository checkout.

Required assertions:

- wheel installs without using editable mode;
- sdist installs without using editable mode;
- `python -c "import arancel_mx"` succeeds;
- `python -m arancel_mx --help` succeeds;
- installed `arancel-mx --help` succeeds;
- help exposes the documented public command families;
- package data such as the source registry is present after installation;
- no test-only dependency is accidentally required by the normal installed package.

The smoke test must execute from a temporary directory that is not the repository root so that local source paths cannot mask packaging errors.

### 2. Python version matrix

Keep Python 3.11 as the minimum supported runtime and test at least:

- Python 3.11;
- one current newer CPython version supported by all locked production dependencies at implementation time.

The exact newer version must be verified against current upstream support immediately before the implementation PR. Do not hard-code a future version from memory.

### 3. DuckDB consumer certification

Open the generated `arancel_mx.duckdb` read-only and run consumer-style queries against the public view/table contract.

Required checks:

- database opens successfully;
- documented core tables/views exist;
- `arancel_mx` row count equals manifest row count;
- counts by `level` equal manifest level counts;
- `record_id` uniqueness holds;
- MX8 rows have expected HS6 parents;
- NICO10 rows have expected MX8 parents;
- no descriptive HS level silently inherits tariff rates;
- representative lookups return stable schema/column names;
- source/provenance joins resolve for canonical records.

DuckDB storage compatibility must be tested explicitly rather than inferred from `duckdb>=1.1`. The implementation must record which minimum DuckDB version can open the produced database and either:

1. constrain the package/runtime promise accordingly; or
2. configure a compatible storage version if technically supported and justified.

No compatibility claim is added to documentation without an executed test.

### 4. Cross-format equivalence

Treat DuckDB as the canonical materialization and prove that CSV and JSON represent the same public logical records.

Required checks:

- exact row-count equality;
- exact public column-set equality after format-specific decoding;
- unique `record_id` in all formats;
- record-by-record equality keyed by `record_id` after normalized null/numeric/text representation;
- level counts equal across all formats and manifest;
- deterministic ordering where the public release contract promises ordering.

### 5. Source archive reconstruction

For `official-sources.tar.gz`:

- archive contains only expected source captures and metadata;
- no unsafe absolute or parent-traversal paths;
- each archived official document hash matches `source_capture.json`;
- each captured source identity resolves to the manifest;
- every required manifest source document exists in the archive;
- no extra authoritative source is silently omitted from provenance;
- extraction into an empty temporary directory succeeds without overwriting external paths.

### 6. Hash and manifest verification

Independently recompute:

- `SHA256SUMS` entries;
- manifest artifact hashes;
- official-source hashes;
- registry hash;
- record hashes where applicable.

The verifier must fail closed on:

- a one-byte change to CSV;
- a one-byte change to JSON;
- a modified manifest;
- a modified source archive;
- a missing asset;
- an unexpected seventh asset;
- duplicate or malformed checksum lines.

### 7. Deterministic rebuild tests

Using frozen captured source bytes and fixed logical build metadata, run the build twice in isolated directories.

Required behavior:

- canonical logical records are identical;
- deterministic text artifacts expected to be byte-stable have identical hashes;
- source archive is byte-stable if the implementation contract currently promises deterministic archive metadata;
- DuckDB logical contents are identical even when the physical DuckDB file is not guaranteed to be byte-identical;
- any intentionally non-deterministic field is explicitly documented and excluded from equality only for a justified reason.

### 8. `no_change` replay

A first verified build produces a schema-v2 manifest. A second pipeline evaluation receives the first manifest as its previous published state while source bytes remain unchanged.

Expected result:

```json
{"status":"no_change"}
```

The second run must not generate a publication candidate that can reach the publisher.

This test should be fixture-driven and deterministic in CI. A live repeated `publish=false` workflow may supplement it but must not be the only coverage because official sites can change between calls.

### 9. Fault injection

Add deterministic tests for these boundaries where they are not already covered:

- source timeout;
- redirect to non-allowlisted host;
- oversized response;
- unexpected/mismatched media type;
- malformed/truncated XLS/XLSX/PDF;
- parser structural ambiguity;
- missing required DOF evidence;
- conflicting legal evidence;
- source hash mismatch;
- cross-format mismatch;
- manifest provenance mismatch;
- existing release/tag collision;
- remote upload hash/size mismatch;
- cleanup failure after failed draft publication.

All expected failures must return structured bounded diagnostics without printing secrets.

## Controlled live mutation protocol

The user explicitly approved controlled temporary mutations. They are therefore part of certification, but must be isolated from the production namespace.

### Temporary draft release test

Use a dedicated manual certification workflow or an explicitly gated job. It must never run automatically on pull requests.

Naming:

```text
release name: [CERTIFICATION] arancel-mx <run-id>
tag candidate namespace: certification-<run-id>
```

Never use `data-*`.

Test payloads must be tiny synthetic fixtures, not the real 30+ MB production dataset. The purpose is to prove the GitHub write boundary and remote verification lifecycle, not to duplicate the production artifact.

Lifecycle:

1. confirm no production tag/release uses the certification name;
2. create a draft release only;
3. upload exact small expected assets for the certification fixture;
4. fetch release metadata back from GitHub;
5. download/verify uploaded bytes and hashes;
6. deliberately do not publish the draft;
7. delete the draft in a guaranteed cleanup block;
8. check release absence;
9. check tag/ref absence;
10. fail certification if cleanup cannot be confirmed.

If GitHub creates a tag/ref earlier than expected for a draft in current API behavior, the workflow must explicitly delete that certification ref during cleanup and verify its absence. The implementation must discover and test actual GitHub behavior rather than assuming it.

The certification workflow receives `contents: write` only for this isolated job.

### Temporary GitHub Issue test

Use a unique title prefix that cannot collide with real production alerts:

```text
[CERTIFICATION ALERT] <run-id>
```

Lifecycle:

1. create temporary issue;
2. read it back;
3. update body or add a certification comment;
4. confirm idempotent/deduplication behavior required by the test harness;
5. close the issue with an explicit certification-complete message;
6. read it back and assert `closed`;
7. leave it closed as an auditable test trace, unless repository policy later requires deletion-like cleanup (GitHub Issues are not normally deletable through standard repository APIs).

This test must not reuse `[DATA ALERT]` identities because it must never update or close a real production incident.

The certification issue job receives `issues: write`, `contents: read`, and nothing broader.

### Mutation safety invariants

Before and after a live certification run, assert:

- no new `data-*` tag was created;
- no public production release was changed;
- no draft certification release remains;
- no certification tag/ref remains;
- the certification issue is closed;
- `main` has not been mutated by the workflow;
- the workflow did not receive secrets beyond the built-in token unless separately approved;
- artifacts/logs contain no token or credential material.

## Supply-chain provenance

Add GitHub artifact attestations only where they materially improve the public verification story.

Preferred target is the release bundle or a manifest/checksum artifact that consumers are expected to verify, not every routine CI file.

GitHub currently documents that artifact attestations establish provenance linking an artifact to repository/workflow/commit/event and are verified with `gh attestation verify`. For public repositories they use Sigstore's public-good infrastructure.

If implemented, the attestation job receives only the documented minimum:

```text
contents: read
id-token: write
attestations: write
```

Attestation verification supplements SHA-256 and manifest validation; it does not replace them and must not be presented as proof that the data itself is legally correct.

After the first truly immutable automated release exists, add an operator verification procedure using GitHub's current release integrity commands (`gh release verify` and `gh release verify-asset`) and keep it outside normal `publish=false` dry runs.

## Timestamp semantic audit

The dry-run artifact showed that `generated_at` can precede individual `retrieved_at` values because build metadata is resolved before source retrieval.

The current documentation defines `generated_at` as build/release generation time and `retrieved_at` as actual source fetch time. Certification must make this semantics explicit.

Preferred contract:

- rename or document the current early timestamp semantically as build-start generation metadata if it remains early; or
- set final release `generated_at` only after source capture if the field is intended to represent completed candidate generation.

Do not change timestamp meaning merely for chronological aesthetics. Pick one meaning, test it, and document it consistently in manifest, data model, README, and code.

## Docusaurus documentation design

### Location and isolation

Use:

```text
website/
├── docusaurus.config.ts
├── sidebars.ts
├── package.json
├── package-lock.json
├── src/
├── static/
└── i18n/
```

Keep Python package/build metadata at repository root.

Do not run Node tooling in the official data pipeline.

### Source-of-truth policy

Avoid maintaining the same technical documentation manually in README, `docs/`, and `website/docs/`.

Preferred design:

- root `README.md`/`README.en.md` remain concise repository entrypoints;
- canonical long-form technical Markdown remains under root `docs/` where practical;
- Docusaurus consumes canonical documentation through a supported docs-plugin path/configuration verified against the current official Docusaurus docs;
- Docusaurus-only landing/navigation/UI content stays under `website/`;
- if Docusaurus cannot safely consume the external docs directory in the selected version, use a deterministic copy/generation step with a `--check` mode so drift is CI-detectable. Do not introduce hand-maintained duplicate copies.

The exact method is chosen only after a proof build using the pinned Docusaurus version.

### Internationalization

Default locale: Spanish (`es`).
Secondary locale: English (`en`).

Use Docusaurus native i18n and a locale dropdown. GitHub Pages uses a single deployment, so locales should live under paths in one site rather than separate Pages deployments.

Public user-facing core docs should have ES/EN parity before the site is declared complete. Internal implementation specs under `docs/superpowers/` do not need to be exposed or translated as public product documentation.

### Public information architecture

Initial public navigation:

```text
Inicio / Home
Getting Started
CLI
Python
Dataset
  - latest release
  - CSV
  - JSON
  - DuckDB
  - manifest and checksums
  - official source archive
Modelo de datos / Data model
HS -> MX8 -> NICO
Fuentes oficiales / Official sources
Procedencia y evidencia legal / Provenance and legal evidence
Pipeline autónomo / Autonomous pipeline
Reproducibilidad / Reproducibility
Verificar una release / Verify a release
Contribuir / Contributing
```

Do not expose internal operational secrets, temporary certification internals, or undocumented unstable API promises.

### Docusaurus dependency policy

At implementation time:

1. verify the current stable Docusaurus release from official upstream metadata/docs;
2. pin the selected version in `package.json`/lockfile;
3. commit the lockfile;
4. use `npm ci` in CI;
5. do not use a floating `latest` reference in CI;
6. review Node engine requirements against the selected Docusaurus version;
7. enable Dependabot for the website ecosystem if not already covered.

### Documentation CI

On PRs affecting `website/`, public docs, README links, or docs workflow:

- `npm ci`;
- production Docusaurus build;
- Spanish build;
- English build;
- broken internal links must fail the build;
- no generated `build/` output committed to Git;
- static asset references resolve;
- basic generated HTML smoke checks for title, language alternates, canonical paths, and primary navigation.

Do not add browser-heavy E2E infrastructure unless the static build proves insufficient.

### GitHub Pages deployment

Use a dedicated workflow with a build job and deploy job. The deploy boundary uses GitHub's documented Pages permissions:

```text
contents: read
pages: write
id-token: write
```

Use the `github-pages` environment and current pinned official Pages actions.

The docs workflow must not receive `contents: write`, `issues: write`, or release permissions.

### Dataset/release display

Docusaurus may show the latest dataset version and links, but the site must not become the source of truth for release state.

Preferred implementation:

- generate a small static metadata file at docs build time from GitHub Release/API metadata or a committed/generated safe data snapshot;
- link users to GitHub Releases for immutable assets;
- never rehost generated dataset binaries inside the Pages artifact.

## PR decomposition

Keep implementation auditable and reversible. Preferred PR sequence:

1. **Certification core**: package-install smoke tests, artifact equivalence, archive/hash verification, DuckDB consumer tests, deterministic/no-change fixture tests.
2. **Fault injection and timestamp contract**: fill remaining fail-closed coverage and resolve/document timestamp semantics.
3. **Controlled GitHub mutation certification**: manual-only temporary draft release and temporary issue lifecycle with guaranteed cleanup.
4. **Artifact attestation/release verification**: only after core certification is green and required GitHub feature availability is confirmed.
5. **Docusaurus foundation**: pinned site toolchain, Spanish default, English i18n skeleton, docs source-of-truth integration, local/CI builds.
6. **Docusaurus content and Pages**: public navigation/content parity, verification guide, Pages workflow and environment deployment.

If one PR grows beyond one coherent concern, split it further rather than mixing unrelated cleanup.

## Mandatory pre-PR double-check gate

Before opening **every implementation PR**, perform and record this checklist in the PR body:

1. Re-read the current `README.md`, relevant design/spec, and files being changed.
2. Fetch current `main` and confirm the branch is based on the expected protected head.
3. Verify any unstable external assumption against primary official documentation at that moment (GitHub, Docusaurus, DuckDB, PyPA, etc.).
4. Search the repository for existing equivalent functionality before adding new code.
5. Confirm no requested behavior contradicts the project objective or public contract.
6. Run the smallest focused RED test first for bug/behavior changes.
7. Run the complete relevant suite after implementation.
8. Run package/build checks and `git diff --check` equivalent.
9. Inspect the final diff manually for accidental generated files, secrets, debug probes, network-dependent tests, stale comments, or unrelated refactors.
10. Verify permissions are least-privilege for any workflow change.
11. Verify live-mutation jobs cannot run on untrusted pull-request code.
12. Verify temporary release names/tags cannot collide with `data-*` production namespace.
13. Verify cleanup behavior is tested before a real temporary mutation is attempted.
14. Verify documentation matches actual command/check names and current implementation.
15. Only then open the PR.

For each PR, the assistant should summarize the double-check result before creating it. Any unresolved contradiction blocks PR creation until investigated.

## Testing and rollout gates

### Gate A: local/offline certification

Pass when:

- package artifacts install cleanly;
- CLI/module smoke tests pass outside checkout;
- artifact and source verification pass;
- DuckDB consumer tests pass;
- cross-format equivalence passes;
- deterministic replay passes;
- `no_change` replay passes;
- fault injection remains fail-closed.

### Gate B: live temporary mutation certification

Pass when:

- temporary draft release create/upload/read-back/delete lifecycle succeeds;
- no certification release/tag remains;
- temporary certification issue create/update/close succeeds;
- no production release/tag/issue identity was touched;
- post-run audit confirms no unexpected mutation.

### Gate C: first automated immutable production release

Pass when a scheduled/trusted-main production run:

- creates one verified `data-YYYY.MM.DD` release only after all gates pass;
- publishes exactly six expected assets;
- remote asset hashes match local verified bundle;
- GitHub reports the release as immutable when repository settings support it;
- release integrity can be independently verified using the documented GitHub mechanism;
- a subsequent unchanged run returns `no_change` and publishes nothing.

### Gate D: documentation site

Pass when:

- pinned Docusaurus build succeeds reproducibly with `npm ci`;
- ES and EN builds succeed;
- public docs reflect the tested package/release behavior;
- GitHub Pages deploys from its dedicated least-privilege workflow;
- Pages site does not contain dataset binaries or secrets;
- README links resolve to the public docs site and GitHub Releases appropriately.

## Completion criteria

The repository can be called stable and usable for the current 0.x public contract when all of the following are true:

1. protected-main CI and production dry-run remain green;
2. wheel/sdist installation works in clean external environments;
3. documented CLI entrypoints work from installed artifacts;
4. public dataset formats are logically equivalent and independently verifiable;
5. source archive plus manifest reconstruct source identity and checksums;
6. DuckDB has a tested consumer compatibility statement;
7. deterministic rebuild and `no_change` behavior are proven;
8. expected corruption/network/legal failures fail closed;
9. temporary real GitHub write-boundary certification succeeds and cleans up safely;
10. first autonomous immutable release succeeds and the next unchanged run publishes nothing;
11. Docusaurus documentation builds and deploys in ES/EN with no duplicated manual source of truth;
12. every implementation PR has documented double-check evidence and no known unresolved contradiction.

## Primary references verified during design

- Repository README and current production hardening design in `main`.
- Docusaurus official documentation for i18n and static documentation behavior.
- GitHub official documentation for Pages custom workflows and required `pages: write` / `id-token: write` permissions.
- GitHub official documentation for artifact attestations and `gh attestation verify`.
- GitHub official documentation for immutable release verification with `gh release verify` and `gh release verify-asset`.

These references are implementation constraints, not copied code. Versions/action SHAs must be re-verified immediately before the PR that introduces them.
