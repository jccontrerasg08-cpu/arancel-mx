# External consumption contract design

**Status:** Draft design pending user review  
**Repository:** `jccontrerasg08-cpu/arancel-mx`  
**Baseline:** `main` at `f576f4615b6b1cbb785541451d7b07f5d91232e1`  
**Date:** 2026-08-13  
**Motivating consumer:** AduanaMap (downstream application, not this repository)  
**Research input:** [`docs/superpowers/research/2026-08-13-deep-research-report.md`](../research/2026-08-13-deep-research-report.md)

## 1. Goal

Give downstream applications a written, test-backed contract for consuming `arancel-mx` as it exists today: a fail-closed, source-driven Mexican LIGIE/NICO dataset distributed as six GitHub Release assets plus a consumer Python package.

A successful AduanaMap (or any other) ingest journey is:

```text
pin arancel-mx package version
  -> pip install arancel-mx
  -> arancel-mx doctor
  -> download one exact data-YYYY.MM.DD release
  -> verify SHA256SUMS + manifest.json + DuckDB structure
  -> query IGI/IGE, hierarchy, vigencia, and provenance
  -> optionally self-ingest CSV/JSON/DuckDB into the consumer's own store
```

This design does **not** turn `arancel-mx` into AduanaMap, a UK Trade Tariff clone, or a hosted platform.

## 2. Why this is the first sub-project

The research report describes several independent platforms at once: YAML source catalogs, Postgres publication, Fumadocs, Great Expectations, hosted OpenAPI, DevContainers, secret-scan CI, and a full measures graph (IVA, NOM, T-MEC). That is too large for one specification.

This spec therefore:

1. decomposes the report into independent tracks;
2. accepts, adapts, or rejects each recommendation against the shipped repository;
3. fully designs only the first track: the **external consumption contract**.

Later tracks keep their own specs or existing plans. They are listed in §4 so they are not lost, and they are out of implementation scope here.

## 3. Locked assumptions

These assumptions are explicit so they are not re-litigated during implementation:

- **AduanaMap is not this repository.** The GitHub identity remains `jccontrerasg08-cpu/arancel-mx`. No rename, transfer, or `aduanamap-mx/arancel-mx` URL is part of this work.
- **Canonical warehouse remains DuckDB.** Downstream products may load DuckDB/CSV/JSON into Postgres themselves. `arancel-mx` does not publish a Postgres schema or host one.
- **Distribution remains GitHub Releases + PyPI.** There is no hosted REST `/api/v1/tariffs` in this repository for 0.2.x.
- **Official sources remain Diputados, DOF, and SNICE.** SIICEX, VUCEM HTML, INEGI, BCMM, ANAM PROSEC/cupos, and WTO/WITS are not added as publishable authorities.
- **Legal text is not relicensed as CC0.** Software stays Apache-2.0. Official source documents keep their own legal status, as `NOTICE` already states.
- **Fail-closed stays fail-closed.** A failed quality gate blocks publication and opens a GitHub Issue. There is no manual "publish anyway" review queue.
- **Package `0.2.0` is already on PyPI** (uploaded 2026-08-12). Documentation that still calls PyPI a roadmap or unreleased candidate is false and must be corrected as part of this contract.
- **Draft health-audit PR #57 is independent.** Merge it on its own. This spec does not depend on those parser/storage fixes.

## 4. Decomposition of the research report

| Track | Relation to this spec | Disposition |
|---|---|---|
| External consumption contract, PyPI/status honesty, reference golden examples | **This spec** | Design and implement next |
| Public docs information architecture + Docusaurus `website/` | Follow-up | Keep the 2026-08-10 Docusaurus architecture; refresh topic ownership in a later addendum before scaffolding `website/` |
| Health-audit fail-closed fixes | Independent | Review/merge [PR #57](https://github.com/jccontrerasg08-cpu/arancel-mx/pull/57); no new design |
| A9 live attestations, A10 timestamps, A11 `gh release verify` | Independent | Execute existing plans; wait for the next legitimate changed `data-*` publish for live A9 evidence |
| Contributor DevContainer / Dockerfile | Later optional spec | Useful; not required for AduanaMap ingest |
| Great Expectations / GX Data Docs | Rejected for now | Custom fail-closed validators and bundle certification already exist; do not add a second DQ stack |
| Fumadocs / Evidence / Datasette hosted explorer | Rejected | Conflicts with the approved isolated Docusaurus site; Datasette/Evidence remain P2 product ideas, not this repo's docs engine |
| Hosted REST OpenAPI, Postgres canonical store, R2 evidence bucket, Dagster/Airbyte | Rejected for 0.2.x | Contradict shipped architecture and the PyPI consumer non-goals |
| IVA, NOM, TLC/T-MEC preferences, bilingual EN descriptions in the public table | Rejected for 0.2.x | New product scope; would change `PUBLIC_COLUMNS` and legal coverage |
| `config/sources/*.yaml` + `config/datasets/*.yaml` migration | Rejected | `source_registry.json` plus schema v2 `manifest.json` already are the declarative contracts |
| TruffleHog CI job | Later optional | GitHub secret scanning is already an operator control; optional CI scanner is not the consumption contract |
| Cache-Control headers on release assets | Later optional | GitHub Releases do not expose custom Cache-Control today; document immutability of `data-*` tags instead |

## 5. Research-report decision record

Each research recommendation is decided here. "Adapt" means keep the intent and map it onto the shipped system.

### 5.1 P0

| Recommendation | Decision | Mapping |
|---|---|---|
| Clear license, preferably CC0 or MIT | **Adapt** | Keep Apache-2.0 for original code. Clarify in README/`NOTICE` that official Diputados/DOF/SNICE text is not a CC0 grant. Do not relicense. |
| `config/sources/` and `config/datasets/` YAML | **Reject** | Sources live in `src/arancel_mx/sources/source_registry.json`. Dataset contract lives in `PUBLIC_COLUMNS`, `manifest.json` schema v2, and `docs/data-model.md`. |
| CI that validates releases (manifest vs files, row counts) | **Already done** | `official-data-pipeline.yml` + `certify_bundle` + release tests. Document this path for downstream consumers; do not add a parallel `ci/validate-release.yml`. |
| Golden tests for IGI=16%, IVA, treaties | **Adapt** | Add reference examples for **official IGI/IGE text** of known codes from verified fixtures. Do **not** assert `IGI=16%` (that confuses IVA with IGI). Do **not** invent IVA or TLC. |
| Dockerfile / DevContainer | **Defer** | Separate later spec. Not part of the consumption contract. |

### 5.2 P1

| Recommendation | Decision | Mapping |
|---|---|---|
| Fumadocs documentation site | **Reject** | Docusaurus under isolated `website/` is the approved public-docs engine. |
| Great Expectations | **Reject for now** | Keep Python fail-closed gates. Revisit only if a later spec proves GX adds checks the current validators cannot express. |
| Cache-Control for versioned outputs | **Adapt** | Document that a `data-YYYY.MM.DD` GitHub Release is immutable. Do not claim HTTP cache headers the project cannot set. |
| Secret scanning in CI | **Defer** | Operator GitHub Secret scanning stays. A TruffleHog workflow is not this spec. |
| OpenAPI `/api/v1/tariffs` | **Reject for 0.2.x** | The public query surface is CLI + `Dataset`. AduanaMap may wrap that in its own API. |

### 5.3 P2 and AduanaMap artifacts

| Recommendation | Decision | Mapping |
|---|---|---|
| Datasette dashboard | **Defer** | Downstream may point Datasette at the public DuckDB. Not hosted here. |
| Postgres vs DuckDB benchmark | **Reject** | DuckDB is canonical. Downstream may benchmark its own ingest. |
| OpenLineage | **Defer** | Manifest + `source_capture.json` + GitHub run identity already provide release lineage. |
| WTO/WITS comparative tariffs | **Reject** | Would mix non-Mexican authority into the official dataset. |
| AduanaMap reads hosted Postgres / REST | **Adapt** | AduanaMap reads the six-asset release and/or `Dataset`. It may load those bytes into its own Postgres/API. |
| Per-row `source_trace.json` | **Adapt** | Use existing per-row `primary_source_*` / `source_document_ids_json` plus `Dataset.provenance(code)` and manifest `source_documents`. Do not add a seventh release asset. |
| `pip install arancelmx` | **Reject** | The distribution name is `arancel-mx`. |

### 5.4 Factual corrections the contract must not repeat

The research report must not leak into public docs as if it described this repository:

- There is no `setup.py`; packaging is `pyproject.toml`.
- Generated DuckDB/CSV/JSON must not be committed under `data/releases/` (gitignored by policy).
- SIDOF API keys are not part of official capture. DOF evidence is fetched from public ledger-linked URLs.
- VUCEM/SIICEX are not official publishable sources.
- `source_trace.json` is not a release asset; `source_capture.json` lives inside `official-sources.tar.gz`.
- Public descriptions are Spanish official text, not bilingual ES/EN columns.

## 6. Approaches considered

### Approach A — Document and test the shipped contract (recommended)

Write one canonical downstream guide, correct PyPI/status wording, and add tests that lock what AduanaMap may rely on and what it must not assume.

- Pros: matches the running system; no new runtime; unblocks honest `pip install`; YAGNI.
- Cons: does not give AduanaMap a hosted API.

### Approach B — Host a REST API over DuckDB in this repository

Add FastAPI/OpenAPI `/api/v1/tariffs/mx/{code}` as the research report sketches.

- Pros: closer to UK Trade Tariff; convenient for a web app.
- Cons: contradicts the approved 0.2.0 non-goal of no hosted REST API; adds hosting, auth, SLA, and cache semantics this project does not operate.

### Approach C — Rebuild around the report's greenfield layout

Introduce `config/sources/*.yaml`, Postgres as canonical publish, Fumadocs, GX, R2, and a manual review queue.

- Pros: matches the report's vocabulary.
- Cons: discards a working fail-closed DuckDB pipeline, source registry, and certification suite; high risk, no user-facing gain for AduanaMap beyond what Approach A already enables.

**Recommendation: Approach A.** AduanaMap should treat `arancel-mx` as an upstream data package. If AduanaMap needs HTTP, it owns that API.

## 7. Architecture

No new runtime service. The contract is a documentation-and-test layer over existing components:

```text
official Diputados / DOF / SNICE
        -> fail-closed pipeline
        -> six-asset GitHub Release data-YYYY.MM.DD
        -> PyPI package arancel-mx (code only)
                -> CLI / Dataset (verify + query)
                -> AduanaMap (or any app) self-ingests
```

```text
arancel-mx (this repo)          AduanaMap (other repo)
----------------------          ----------------------
source registry                 own UI / map / API
legal reconciliation            own Postgres if desired
DuckDB + six assets             ingest verified bytes
consumer Dataset/CLI            never scrape DOF/SNICE itself
```

AduanaMap must not scrape official sources in parallel and then treat that scrape as equivalent to an `arancel-mx` release. The whole point of this package is verified identity, hashes, and fail-closed publication.

## 8. Public surface AduanaMap may rely on

### 8.1 Python package

- Distribution name: `arancel-mx`
- Import package: `arancel_mx`
- Console: `arancel-mx`
- Documented public types: `Dataset`, `TariffRecord`, `Ficha`, `ProvenanceRecord`, `SearchResult`, `DatasetInfo`, `HsSection`, and the public exception types exported from `arancel_mx`
- Construction: `Dataset.latest()`, `Dataset.version("data-YYYY.MM.DD")`, `Dataset.open(path)` (structural open is not `release_verified`)
- Queries: `lookup`, `search`, `ficha`, `chapters`, `parent`, `children`, `provenance`

Package version and dataset version remain independent. Pinning `arancel-mx==0.2.0` does not pin `data-2026.08.11`.

### 8.2 Dataset release assets

Exactly six files, unchanged:

1. `arancel_mx.duckdb`
2. `arancel_mx.csv`
3. `arancel_mx.json`
4. `manifest.json`
5. `SHA256SUMS`
6. `official-sources.tar.gz`

Downstream verification order:

1. Resolve one exact `data-YYYY.MM.DD` tag (never "whatever is in git").
2. Check `SHA256SUMS` against the downloaded bytes.
3. Check `manifest.json` schema version `2` and artifact hashes.
4. Open DuckDB read-only and use the `arancel_mx` view and/or `Dataset`.

Do not add `source_trace.json`, `manifest.yaml`, or Postgres dumps to this list.

### 8.3 Tabular columns

The public CSV/JSON/`arancel_mx` view column order remains `PUBLIC_COLUMNS`. This spec does **not** add, remove, or rename columns.

Downstream products that need a `source_trace` object must compose it from:

- per-row `primary_source_document_id`, `primary_source_authority`, `primary_source_url`, `source_document_ids_json`, `source_count`
- `Dataset.provenance(code)` / `arancel-mx provenance`
- manifest `source_documents` and `source_identity`

IGI/IGE display must use `igi_text` / `ige_text` as official literals (for example `10` or `Ex.`). Downstream must not rewrite those literals into `"16%"` or treat `igi_value` as IVA.

### 8.4 Out of contract

AduanaMap (and public docs) must not claim that `arancel-mx` currently provides:

- IVA, franja/región, permisos, NOM, TLC/T-MEC preferences, or PROSEC
- English description columns
- a hosted REST API
- a hosted Postgres
- SIICEX-CAAAREM or VUCEM HTML as legal identity
- automatic promotion of incomplete captures through a human review queue

## 9. Status honesty

Public docs currently contradict PyPI. The contract requires these exact status meanings:

| Surface | Required wording intent |
|---|---|
| README ES/EN status table row "Publicación en PyPI" | Published: `arancel-mx==0.2.0` is on PyPI. The 2026-08-11 design's full external OS/Python matrix was **not** a blocking gate for that upload. Do not say "Roadmap". Do not say "production-certified" until a later package version completes those gates. |
| `CHANGELOG.md` `[0.2.0]` | Heading date `2026-08-12` (PyPI upload day), not "Unreleased package candidate". Note that Trusted Publishing uploaded 0.2.0 and that the original design's post-TestPyPI matrix remains incomplete. |
| `docs/consumer-cli.md` | `pip install arancel-mx` is the current public install path, not a future one. |
| `docs/package-release.md` | Describe 0.2.0 as published. Keep the build-once / TestPyPI / Trusted Publishing mechanics. Replace the sentence that forbids claiming publication. State that a later `0.2.1+` would be required to treat the design's full matrix as a release gate, because 0.2.0 filenames are already on PyPI. |

Do not weaken existing tests that require `pip install arancel-mx`, `Dataset.latest()`, or the six-asset list. No current test asserts the old "not yet published" wording; add tests that lock the new honesty wording instead.

## 10. Canonical downstream document

Add `docs/external-consumption.md` as the Spanish source of truth for downstream ingest (AduanaMap included). `README.en.md` must link to that file and include a short English ingest summary (install, verify, query, out of scope) so English-only readers are not blocked. Section-by-section English translations wait for the later Docusaurus i18n addendum. Do not create a second full English markdown guide in this spec.

The document has these sections, in this order:

1. What `arancel-mx` is and is not (data package, not legal advice, not a customs platform).
2. Install and pin (`pip install arancel-mx==0.2.0`, dataset pin `--dataset data-YYYY.MM.DD`).
3. Verify (`doctor`, `data download`, `data verify`, SHA256SUMS, manifest schema v2).
4. Query (CLI + `Dataset` examples using `lookup` / `ficha` / `provenance`).
5. Self-ingest (read DuckDB/CSV/JSON into the consumer's store; do not treat that store as upstream truth).
6. Provenance mapping (`primary_source_*` + `provenance` + `official-sources.tar.gz`).
7. Out of scope measures (IVA, NOM, TLC, bilingual columns, hosted API).
8. License and attribution pointer to `LICENSE` / `NOTICE`.
9. Link to `docs/consumer-cli.md`, `docs/data-model.md`, `docs/release-process.md`, `docs/sources.md`.

`docs/package-release.md` remains the Python-distribution mechanics doc. It must not duplicate the full ingest guide.

Existing links to `docs/consumer-cli.md` stay valid. The new guide points at it rather than replacing it.

## 11. Reference golden examples

The research report's "IGI=16%" examples are rejected. This spec adds **reference examples** that lock official literals already used in project docs/fixtures, so downstream tests have a stable expected shape.

Implementation rules:

- Use offline fixtures or documentation-contract tests. Do not fetch live DOF or the public GitHub Release during unit tests.
- Assert `igi_text` / `ige_text` / `code` / `level`, not rewritten percentages.
- Include at least:
  - Fixture golden: `01012101` remains a current 8-digit fraction in consumer/parser fixtures, with official literals already used there (`igi_text` `10`, `ige_text` `Ex.` where the fixture supplies rates).
  - Documentation golden: `docs/sources.md` and `docs/external-consumption.md` keep the SIICEX counter-example: `11063001` is not in the current official snapshot and must fail closed; `11062002` is the documented sagú fraction with official IGI `10`. That pair is a docs-contract assertion, not a live DuckDB query.
- Do not add treaty/IVA fixtures.
- Do not add a unit test that queries the published `data-*` DuckDB for `11062002` / `11063001`.

If a later official LIGIE change makes the documented sagú example stale, `docs/sources.md`, `docs/external-consumption.md`, and the docs-contract test must be updated together. That is intended.

## 12. License and attribution

No license change.

README (ES and EN) and `docs/external-consumption.md` must state:

- original project code is Apache-2.0;
- Cámara de Diputados, DOF, and SNICE publications retain their own legal status;
- redistribution of captured official bytes in `official-sources.tar.gz` is for verification, not a transfer of those authorities' rights;
- `arancel-mx` is not legal advice.

`NOTICE` already contains this distinction; do not rewrite it unless a factual error is found.

## 13. Error handling

Downstream guidance must describe fail-closed consumer behavior that already exists:

- missing or unverifiable dataset: do not query a partial cache;
- `--offline` does not fall back to network;
- unknown or non-current codes raise `RecordNotFoundError` / CLI failure rather than a guessed row;
- `Dataset.open()` on a local file is structural, not release-verified.

This spec does not change those semantics. It only requires them to be stated in the downstream guide.

## 14. Testing

Add or extend tests so the contract cannot silently drift:

1. `docs/external-consumption.md` exists and contains `pip install arancel-mx`, `data-YYYY.MM.DD`, `SHA256SUMS`, `Dataset.provenance`, and the out-of-scope strings `IVA`, `NOM`, and `T-MEC` in a section that says they are **not** published.
2. README ES/EN status tables no longer call PyPI a roadmap. They mention `0.2.0` as published and do not claim production certification.
3. `CHANGELOG.md` `[0.2.0]` heading is not "Unreleased package candidate" and includes `2026-08-12`.
4. `docs/consumer-cli.md` and `docs/package-release.md` no longer say publication has not happened.
5. Reference golden examples from §11 (fixture `01012101` rates; docs-contract for `11063001` / `11062002`).
6. Existing public-column, six-asset, and README install tests remain green.

No live GitHub write-boundary test is required for this spec. No new workflow file.

## 15. Implementation sequence (after this spec is approved)

This is the intended PR split for the later implementation plan, not work to do before approval:

1. Honesty PR: README ES/EN, `CHANGELOG.md`, `docs/consumer-cli.md`, `docs/package-release.md`, and the tests that encoded "not published".
2. Contract PR: `docs/external-consumption.md` plus contract tests.
3. Reference examples PR: golden tests from §11.

Do not scaffold `website/`, add OpenAPI, add GX, or migrate `source_registry.json` in those PRs.

## 16. Non-goals

This spec does not:

- implement Docusaurus, Fumadocs, Datasette, Evidence, or a wiki;
- add Postgres, R2, Dagster, Airbyte, lakeFS, or OpenLineage;
- add a hosted REST API or OpenAPI document;
- change `PUBLIC_COLUMNS` or manifest schema v2;
- add IVA, NOM, preferences, or English description columns;
- register SIICEX, VUCEM, INEGI, BCMM, ANAM, or WTO as official sources;
- add SIDOF API keys or other capture secrets;
- create `config/sources/` or `config/datasets/`;
- add a seventh release asset;
- merge or depend on PR #57;
- claim A9 live SLSA evidence before the next changed `data-*` publish;
- add a DevContainer or Dockerfile;
- add TruffleHog;
- treat `arancel-mx` as legal advice or as AduanaMap.

## 17. Success criteria

The spec is implemented when:

- a new contributor can follow `docs/external-consumption.md` and ingest a verified `data-*` release without cloning ETL internals;
- public docs match the fact that `arancel-mx==0.2.0` is on PyPI and that design-matrix certification is incomplete;
- AduanaMap can be told, in one document, which fields exist, how to verify them, and which customs measures are absent;
- tests fail if those claims drift.

## 18. Follow-up specs (not this PR)

After this contract lands, the next design-sized tracks in recommended order are:

1. Public documentation IA addendum for Docusaurus (consumer CLI first, not maintainer `build` as the public `cli.md`).
2. Optional contributor DevContainer spec.
3. Optional `0.2.1` PyPI recertification that actually blocks on the 2026-08-11 external matrix.

Those documents are not created by this spec.
