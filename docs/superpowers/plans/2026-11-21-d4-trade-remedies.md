# D4 Trade Remedies Foundation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a source-traceable, read-only trade-remedy foundation that models measures separately from general IGI/IGE and can retrieve possible official measures by exact 8-digit fraction and origin.

**Architecture:** Add four normalized DuckDB tables for legal measures, procedures, tariff scopes, and terms; materialize them into a separate public view; parse one strict fixture of the 2026 ceramic review; and expose a legacy-safe consumer query. The current official build remains remedy-empty until a later source-promotion slice captures and verifies SIDOF bytes/hashes.

**Tech Stack:** Python 3.11+, DuckDB, dataclasses, pytest, Ruff, mypy, existing release/export pipeline.

**Spec:** `docs/superpowers/specs/2026-11-21-d4-trade-remedies-design.md`

## Global Constraints

- Keep trade remedies separate from `igi_text`, `igi_value`, `ige_text`, and `ige_value`.
- Keep `data-2026.11.21` immutable and readable by newer package code.
- Codes remain strings; `fraction8` is exactly eight ASCII digits and `nico10`, when present, is exactly ten ASCII digits beginning with `fraction8`.
- Never fabricate a NICO or turn “or any other tariff fraction” into synthetic scope rows.
- Separate legal status from procedural status.
- Preserve distinct price-undertaking bases such as FOB China and CIF Mexico.
- Query results are retrieval-only possible measures, never shipment-level applicability or a total-tax calculation.
- Add no runtime dependency.
- No live scraper, public HTTP endpoint, UI, or certified data release in this foundation PR.
- The official build supplies no remedy rows until a separate source-promotion step is reviewed.

## Review Focus

- A current measure under a sunset review must remain `legal_status="active"` while the current procedure is `procedure_status="under_review"`; Task 2 pins this.
- A 10-digit NICO passed to the v1 consumer query must be rejected rather than silently truncated to eight digits; Task 4 pins this.
- The undertaking's 6.72 USD/m² FOB and 8.40 USD/m² CIF thresholds must remain distinct and must not be modeled as duties; Task 3 pins this.
- Legacy releases without `arancel_mx_trade_remedies` must return an empty tuple, not fail schema validation; Task 4 pins this.
- Exporting a DB with remedy rows must preserve the separate tables/view and source-document SHA without changing the tariff row; Task 5 pins this.

---

### Task 1: Install the Trade-Remedy Storage Contract

**Files:**
- Modify: `src/arancel_mx/storage/duckdb.py`
- Create: `tests/storage/test_trade_remedy_schema.py`

**Interfaces:**
- Produces tables `trade_remedy_measure`, `trade_remedy_procedure`, `trade_remedy_scope`, and `trade_remedy_term` through `init_tariff_db(path)`.

- [ ] **Step 1: Write schema tests before production edits**

Create tests that initialize a database and assert `DESCRIBE` exposes these exact core columns:

- measure: `remedy_id, measure_type, product_name, country_of_origin, legal_status, effective_from, effective_to, source_document_id`
- procedure: `procedure_id, remedy_id, procedure_type, procedure_status, published_at, effective_from, effective_to, is_current, source_document_id`
- scope: `scope_id, remedy_id, fraction8, nico10, scope_basis, source_document_id`
- term: `term_id, remedy_id, exporter_or_producer, party_scope, amount_kind, amount, currency, unit, pricing_basis, notes, source_document_id`

Also assert schema CHECK constraints reject an unknown `amount_kind` and an unknown `procedure_status`.

- [ ] **Step 2: Verify RED**

Run:

`python -m pytest -q tests/storage/test_trade_remedy_schema.py`

Expected: FAIL because the four tables do not exist.

- [ ] **Step 3: Add the four tables and useful indexes to `ARANCEL_SCHEMA`**

Supported first-slice values:

- `measure_type`: `antidumping_duty`, `countervailing_duty`, `price_undertaking`
- `legal_status`: `active`, `expired`, `revoked`
- `procedure_type`: `investigation`, `sunset_review`
- `procedure_status`: `final`, `under_review`
- `scope_basis`: `explicit`
- `party_scope`: `named_party`, `other_producer_exporters`, `undertaking_participants`
- `amount_kind`: `specific`, `ad_valorem`, `undertaking`, `other`

Add indexes on remedy foreign-key-like IDs and `trade_remedy_scope(fraction8)`.

- [ ] **Step 4: Verify GREEN**

Run:

`python -m pytest -q tests/storage/test_trade_remedy_schema.py`

Expected: PASS.

- [ ] **Step 5: Commit**

Commit message: `feat: add trade remedy storage schema`

---

### Task 2: Materialize Remedies and Build the Public View

**Files:**
- Modify: `src/arancel_mx/pipeline/build.py`
- Modify: `tests/pipeline/test_build.py`

**Interfaces:**
- Extend:
  `materialize_arancel(conn, source_documents, classifications, rates, release, national_notes=(), nom_requirements=(), trade_remedies=()) -> dict[str, object]`
- Each remedy input is a mapping with measure fields plus `procedures`, `scopes`, and `terms`.
- Produces `arancel_mx_trade_remedies`.

- [ ] **Step 1: Write failing materialization tests**

Add `_trade_remedy_row()` fixture data with:

- `remedy_id="ceramic-cn-antidumping"`
- `measure_type="antidumping_duty"`
- `product_name="Recubrimientos cerámicos para muros y pisos"`
- `country_of_origin="China"`
- `legal_status="active"`
- one current `sunset_review` procedure with `procedure_status="under_review"`, `published_at=date(2026,10,23)`, `effective_from=date(2026,10,24)`
- explicit scopes `69072102`, `69072202`, `69072302`
- named Bode term 8.3 USD/m²
- residual term 12.42 USD/m².

Assert the public view preserves active + under-review simultaneously and leaves a separately materialized `69072102` tariff row's `igi_value` at 35.

Add negative tests for:
- malformed `fraction8`
- `nico10` not sharing the fraction prefix
- named-party term without a party
- specific amount without amount/unit
- more than one current procedure
- unknown source document ID.

- [ ] **Step 2: Verify RED**

Run:

`python -m pytest -q tests/pipeline/test_build.py -k trade_remedy`

Expected: FAIL because `trade_remedies` is not accepted and the view does not exist.

- [ ] **Step 3: Add deterministic validation/insertion helpers**

In `build.py` add focused private helpers:

- `_insert_trade_remedies(conn, rows) -> None`
- deterministic IDs use `canonical_json` + SHA-256 when explicit IDs are absent.
- validate source IDs through `_validate_inputs` by including every remedy, procedure, scope and term `source_document_id`.
- validate exact code shape and amount semantics before inserts.

Do not mutate tariff-rate rows.

- [ ] **Step 4: Add the four tables to `PUBLIC_INTERNAL_TABLES` and create `arancel_mx_trade_remedies` in `_build_view`**

The view joins:
measure → current procedure → scope → term.

Expose at least:

`remedy_id, measure_type, product_name, country_of_origin, legal_status, effective_from, effective_to, procedure_id, procedure_type, procedure_status, procedure_published_at, procedure_effective_from, fraction8, nico10, exporter_or_producer, party_scope, amount_kind, amount, currency, unit, pricing_basis, notes, source_document_id`.

Use the term/measure source identity consistently and keep the procedure source available as `procedure_source_document_id`.

- [ ] **Step 5: Add database validation**

Add checks that reject:
- duplicate remedy IDs through input validation before insert;
- current procedure cardinality > 1 per remedy;
- orphan procedure/scope/term remedy IDs;
- malformed code values that bypassed input validation.

- [ ] **Step 6: Verify GREEN**

Run:

`python -m pytest -q tests/pipeline/test_build.py -k "trade_remedy or materialize"`

Then:

`python -m ruff check src/arancel_mx/pipeline/build.py tests/pipeline/test_build.py`

Expected: PASS.

- [ ] **Step 7: Commit**

Commit message: `feat: materialize trade remedies separately`

---

### Task 3: Add a Fail-Closed Parser Fixture for the 2026 Ceramic Review

**Files:**
- Create: `src/arancel_mx/parsers/trade_remedies.py`
- Create: `tests/parsers/test_trade_remedies.py`
- Create: `tests/fixtures/trade_remedies/ceramic_2026_excerpt.txt`

**Interfaces:**
- Produce:
  `parse_ceramic_2026_review(text: str, *, source_document_id: str) -> tuple[dict[str, object], ...]`
- Output is accepted directly by Task 2's `trade_remedies` argument.

- [ ] **Step 1: Add the checked fixture excerpt**

Include only the minimum official-source excerpts required to prove:
- Bode 8.3 USD/m²;
- residual other-producer/exporter 12.42 USD/m²;
- price undertaking 6.72 USD/m² FOB China and 8.40 USD/m² CIF Mexico;
- fractions 6907.21.02, 6907.22.02, 6907.23.02;
- the 2026 review continues the duties and undertaking;
- publication 2026-10-23 and next-day effectiveness.

Record the official URL in a fixture comment/header, not a mirror.

- [ ] **Step 2: Write RED parser tests**

Assert the parser returns two remedy mappings:

1. antidumping duty with the named and residual terms;
2. price undertaking with two `undertaking` terms whose `pricing_basis` values distinguish FOB China from CIF Mexico.

Both remedies:
- origin China;
- same three explicit fraction scopes;
- legal status active;
- one current sunset-review procedure under review effective 2026-10-24;
- source ID exactly the supplied argument.

Add one test that deletes the “continuarán vigentes” sentence and expects `ValueError`, proving fail-closed current-status parsing.

- [ ] **Step 3: Verify RED**

Run:

`python -m pytest -q tests/parsers/test_trade_remedies.py`

Expected: FAIL because the parser module/function does not exist.

- [ ] **Step 4: Implement the narrow parser**

Use explicit regular expressions/constants for this supported source shape. Do not implement a generic legal-text parser.

Normalize tariff codes by removing dots only after an exact known-pattern match. Convert amounts with `Decimal`. Do not infer unlisted NICO rows.

- [ ] **Step 5: Verify GREEN**

Run:

`python -m pytest -q tests/parsers/test_trade_remedies.py tests/pipeline/test_build.py -k "trade_remedy or ceramic"`

Then:

`python -m ruff check src/arancel_mx/parsers/trade_remedies.py tests/parsers/test_trade_remedies.py`

Expected: PASS.

- [ ] **Step 6: Commit**

Commit message: `feat: parse verified ceramic remedy fixture`

---

### Task 4: Expose a Legacy-Safe Consumer Query

**Files:**
- Modify: `src/arancel_mx/consumer/models.py`
- Modify: `src/arancel_mx/consumer/query.py`
- Modify: `src/arancel_mx/consumer/dataset.py`
- Modify: `src/arancel_mx/__init__.py`
- Create: `tests/consumer/test_trade_remedies_public.py`
- Modify: `tests/consumer/test_dataset.py`

**Interfaces:**
- Add immutable `TradeRemedyHit`.
- Add:
  `query.trade_remedies(connection, fraction8: str, *, country_of_origin: str | None = None) -> tuple[TradeRemedyHit, ...]`
- Add:
  `Dataset.trade_remedies(fraction8: str, *, country_of_origin: str | None = None) -> tuple[TradeRemedyHit, ...]`

- [ ] **Step 1: Write consumer RED tests**

Create a small local DuckDB fixture with the new view and assert:
- `trade_remedies(..., "69072102", country_of_origin="china")` returns hits with codes preserved as strings;
- Bode specific duty remains separate from the undertaking thresholds;
- every hit carries the constant retrieval-only disclaimer;
- `country_of_origin="Vietnam"` returns `()`;
- `"6907210201"` raises `QueryError` rather than truncating;
- a legacy database without the view returns `()`.

Add dataset facade/root-export tests for `TradeRemedyHit`.

- [ ] **Step 2: Verify RED**

Run:

`python -m pytest -q tests/consumer/test_trade_remedies_public.py tests/consumer/test_dataset.py`

Expected: FAIL because the model/query/facade do not exist.

- [ ] **Step 3: Add `TradeRemedyHit`**

Fields match the public view, including:
- separate legal and procedure status;
- `procedure_published_at` and `procedure_effective_from`;
- `pricing_basis`;
- `procedure_source_document_id`;
- `disclaimer`.

Amount type is `float | None` at the consumer boundary, consistent with `TariffRecord`.

- [ ] **Step 4: Implement the query and Dataset facade**

Validation:
- exact eight ASCII digits only;
- non-empty optional origin after stripping;
- case-insensitive exact origin match.

Feature-detect the view in `information_schema.tables`; missing view returns `()`.

Do not join against `arancel_mx` to decide applicability.

- [ ] **Step 5: Verify GREEN**

Run:

`python -m pytest -q tests/consumer/test_trade_remedies_public.py tests/consumer/test_dataset.py`

Then:

`python -m mypy src/arancel_mx/consumer src/arancel_mx/__init__.py`

Expected: PASS.

- [ ] **Step 6: Commit**

Commit message: `feat: expose trade remedy retrieval query`

---

### Task 5: Preserve Remedies Through Public Export Without Breaking Legacy Releases

**Files:**
- Modify: `tests/pipeline/test_build.py`
- Modify: `tests/release/test_package.py` only if release verification needs an explicit additive assertion.

**Interfaces:**
- Uses Task 2's `PUBLIC_INTERNAL_TABLES` and `_build_view`.
- Existing `export_arancel_release(database_path, output_dir)` remains unchanged publicly.

- [ ] **Step 1: Write export regression**

Materialize one tariff row with IGI 35 plus remedy rows, export the release, open the exported `arancel_mx.duckdb`, and assert:
- tariff IGI remains 35;
- `arancel_mx_trade_remedies` exists and returns the remedy;
- `source_document.sha256` for the remedy source is preserved;
- no remedy value appears in `canonical_record.igi_value`.

- [ ] **Step 2: Verify RED or characterize existing behavior**

Run:

`python -m pytest -q tests/pipeline/test_build.py -k trade_remedy_export`

Expected before Task 2 may be RED; after Task 2 it may already PASS because `PUBLIC_INTERNAL_TABLES` drives copy. If it passes, keep the regression because it proves the export contract rather than changing production code.

- [ ] **Step 3: Add only the minimal export fix if the regression fails**

Do not change public release asset count or rewrite manifest semantics in this foundation PR.

- [ ] **Step 4: Run focused compatibility checks**

Run:

`python -m pytest -q tests/pipeline/test_build.py tests/release/test_package.py`

Expected: PASS.

- [ ] **Step 5: Commit**

Commit message: `test: preserve trade remedies in public export`

---

### Task 6: Document the Boundary and Run Full Repository Gates

**Files:**
- Modify: `docs/depth-program.md`
- Modify: `docs/data-model.md`
- Modify: `README.md`
- Modify: `CHANGELOG.md`
- No production API/UI changes.

**Interfaces:**
- Documents the public consumer method and the D4 boundary.
- Leaves #301 open for source promotion and certified data publication.

- [ ] **Step 1: Update documentation**

Document:
- D4 foundation implemented in code, but no certified release contains trade-remedy rows yet;
- the current query returns possible official measures only;
- IGI/IGE remain general tariff fields;
- exporter/product/origin facts control actual remedy applicability;
- source promotion with captured SIDOF bytes/hashes is the next gate.

- [ ] **Step 2: Run all focused D4 tests**

Run:

`python -m pytest -q tests/storage/test_trade_remedy_schema.py tests/parsers/test_trade_remedies.py tests/consumer/test_trade_remedies_public.py tests/pipeline/test_build.py tests/consumer/test_dataset.py tests/release/test_package.py`

Expected: PASS.

- [ ] **Step 3: Run package gates**

Run:

`python -m ruff check src tests scripts`

`python -m mypy src/arancel_mx`

`ARANCEL_MX_SKIP_URL_CHECKS=1 python -m pytest -q --cov=arancel_mx --cov-report=term-missing`

`python -m build`

`git diff --check --exit-code`

Expected: all PASS and coverage >= 87%.

- [ ] **Step 4: Review the complete branch diff**

Confirm:
- only D4 foundation/docs/tests/spec/plan changed;
- no `igi_*` or `ige_*` semantics changed;
- no runtime dependency changed;
- no generated static frontend asset changed;
- no source registry or release tag was silently modified.

- [ ] **Step 5: Commit docs**

Commit message: `docs: document trade remedy retrieval boundary`

- [ ] **Step 6: Open/update one PR**

Title: `feat: add D4 trade remedies foundation`

PR body must state:
- issue #301 remains open;
- no live source promotion or new data release yet;
- verified source fixture is SIDOF 5802001;
- current certified releases stay legacy-safe and remedy-empty.

