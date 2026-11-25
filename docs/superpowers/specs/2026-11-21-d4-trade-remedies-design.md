# D4 Trade Remedies Foundation Design

**Date:** 2026-11-21  
**Issue:** #301  
**Branch:** `feat/d4-trade-remedies`

## Intent

Add the first source-traceable model for Mexican trade remedies without changing the meaning of the general LIGIE tariff fields.

The motivating verified case is the ceramic wall/floor covering measure on China-origin goods. The 2026 sunset-review initiation names fractions `6907.21.02`, `6907.22.02`, and `6907.23.02`, records their 35% general IGI separately, restates company-specific definitive compensatory duties and a price undertaking, and says those measures continue in force while the review is pending.

The public contract must therefore be able to answer:

> Which official trade-remedy measures mention this exact tariff fraction and origin?

It must not answer:

> Does this shipment owe this duty?

That second question depends on product coverage, origin, producer/exporter identity, exclusions, undertakings, effective dates, and other facts outside a tariff-code lookup.

## Source authority

For this domain:

1. DOF/SIDOF final and procedural resolutions are the primary legal evidence.
2. Secretaría de Economía / UPCI notices may be used for discovery and reconciliation.
3. LIGIE/NICO sources provide classification context only; they do not create a trade remedy.
4. A remedy source never overwrites `igi_text`, `igi_value`, `ige_text`, or `ige_value`.

Initial verified sources:

- SIDOF 5684694, final 2023 sunset review. It restates the definitive 2016 exporter-specific duties, the residual 12.42 USD/m² duty for other producer-exporters, and the price undertaking.
- SIDOF 5802001, 2026 second sunset-review initiation. It identifies current TIGIE/NICO scope, states the 35% general IGI separately, and keeps the definitive duties and undertaking in force during the review.

## Critical semantic decision

Do **not** use one overloaded `status` field.

A measure may simultaneously be legally active and procedurally under review. The model therefore separates:

- `legal_status`: whether the measure is in force, such as `active`, `expired`, or `revoked`.
- `procedure_status`: the procedural state of the supporting/current instrument, such as `final` or `under_review`.

For the 2026 ceramic case, the correct state is:

- `legal_status = "active"`
- `procedure_status = "under_review"`

This is required by the 2026 resolution, which keeps the measures in force while the examination proceeds.

## Approaches considered

### A. Normalized measure + scope + term tables

Store one legal measure, one-to-many tariff scopes, and one-to-many monetary/undertaking terms.

**Pros:** avoids duplicating legal facts, models multiple tariff fractions and multiple exporters correctly, keeps procedural history and its source separate, keeps price undertakings distinct from duties, and leaves room for NICO and future temporal operations.

**Cons:** slightly more joins and more validation.

**Decision:** chosen. It is the smallest design that preserves the source semantics.

### B. One flattened row per fraction/exporter

**Pros:** simple query.

**Cons:** duplicates measure dates/source/status across many rows, makes later procedural updates error-prone, and encourages treating a row as a shipment-level determination.

**Decision:** rejected.

### C. One generic regulatory-measure framework for D1-D6

**Pros:** potentially reusable across preferences, PROSEC, quotas, remedies and RRNA.

**Cons:** those domains have materially different legal semantics. Designing their common abstraction now would be speculative and could weaken D4 accuracy.

**Decision:** rejected for this slice.

## Data model

Add four internal DuckDB tables.

### `trade_remedy_measure`

One row per modeled legal measure.

Fields:

- `remedy_id VARCHAR PRIMARY KEY`
- `measure_type VARCHAR NOT NULL`
  - first supported value: `antidumping_duty`
  - `price_undertaking` is represented as a separate measure when the legal source treats it as a distinct mechanism
- `product_name VARCHAR NOT NULL`
- `country_of_origin VARCHAR NOT NULL`
- `legal_status VARCHAR NOT NULL`
- `effective_from DATE`
- `effective_to DATE`
- `source_document_id VARCHAR NOT NULL`

The measure's `source_document_id` is evidence for the modeled current legal measure/terms. It does not imply that this document originally created the measure.

The first slice supports explicit enumerated values only and fails closed on unknown values.

### `trade_remedy_procedure`

One row per procedural event/status attached to a remedy. This keeps the source and effective date of a sunset review separate from the legal measure it reviews.

Fields:

- `procedure_id VARCHAR PRIMARY KEY`
- `remedy_id VARCHAR NOT NULL`
- `procedure_type VARCHAR NOT NULL`
  - first supported value: `sunset_review`
- `procedure_status VARCHAR NOT NULL`
  - `final`
  - `under_review`
- `published_at DATE`
- `effective_from DATE`
- `effective_to DATE`
- `is_current BOOLEAN NOT NULL`
- `source_document_id VARCHAR NOT NULL`

Validation requires at most one current procedure row per remedy. The 2026 ceramic initiation is `sunset_review` + `under_review`, published 2026-10-23 and effective 2026-10-24.

### `trade_remedy_scope`

One row per tariff scope named by the source.

Fields:

- `scope_id VARCHAR PRIMARY KEY`
- `remedy_id VARCHAR NOT NULL`
- `fraction8 VARCHAR NOT NULL`
- `nico10 VARCHAR`
- `scope_basis VARCHAR NOT NULL`
  - first supported value: `explicit`
- `source_document_id VARCHAR NOT NULL`

Rules:

- `fraction8` is exactly eight ASCII digits.
- `nico10`, when present, is exactly ten ASCII digits and begins with `fraction8`.
- no synthetic NICO is created.
- a source phrase such as “or any other tariff fraction” is not converted into fabricated codes; it belongs in notes/source context, not scope rows.

### `trade_remedy_term`

One row per exporter/producer-specific term or residual term.

Fields:

- `term_id VARCHAR PRIMARY KEY`
- `remedy_id VARCHAR NOT NULL`
- `exporter_or_producer VARCHAR`
- `party_scope VARCHAR NOT NULL`
  - `named_party`
  - `other_producer_exporters`
  - `undertaking_participants`
- `amount_kind VARCHAR NOT NULL`
  - `specific`
  - `ad_valorem`
  - `undertaking`
  - `other`
- `amount DECIMAL(18,6)`
- `currency VARCHAR`
- `unit VARCHAR`
- `pricing_basis VARCHAR`
- `notes VARCHAR`
- `source_document_id VARCHAR NOT NULL`

Validation:

- `specific` and `ad_valorem` require numeric amount.
- `specific` additionally requires unit and normally currency.
- `undertaking` may have an amount only when the source explicitly states a threshold; it is never converted into a duty.
- `pricing_basis` preserves source distinctions such as FOB at the Chinese port of shipment versus CIF at the Mexican port of destination.
- a named-party term requires `exporter_or_producer`.
- a residual `other_producer_exporters` term must not name a party.

## Public view and consumer model

Build a public read-only view `arancel_mx_trade_remedies` joining measure, scope and term records without modifying `arancel_mx`.

Expose an immutable flattened consumer object named `TradeRemedyHit`. A hit is deliberately a retrieval result, not a legal applicability determination.

Proposed fields:

- `remedy_id`
- `measure_type`
- `product_name`
- `country_of_origin`
- `fraction8`
- `nico10`
- `legal_status`
- `procedure_status`
- `procedure_published_at`
- `procedure_effective_from`
- `effective_from`
- `effective_to`
- `exporter_or_producer`
- `party_scope`
- `amount_kind`
- `amount`
- `currency`
- `unit`
- `pricing_basis`
- `notes`
- `source_document_id`
- `disclaimer`

The disclaimer is constant and states that a match means an official instrument mentions the code/origin; actual applicability depends on the instrument and shipment facts.

## Query contract

Add:

`trade_remedies(connection, fraction8: str, *, country_of_origin: str | None = None) -> tuple[TradeRemedyHit, ...]`

Rules:

- accept only an exact eight-digit tariff fraction in v1.
- do not silently truncate a 10-digit NICO.
- optional origin filter is exact after whitespace normalization/case-insensitive comparison.
- if the public remedy view does not exist, return an empty tuple so newer package code can open immutable legacy releases such as `data-2026.11.21`.
- sort deterministically by remedy, party scope, party name, amount kind and term id.
- never calculate total import taxes or decide whether a measure applies.

A later additive API/static-data surface may expose this contract. It is not required for the first foundation slice.

## Materialization

Extend `materialize_arancel(...)` with optional `trade_remedies=()`.

The input is a sequence of normalized remedy objects containing:

- measure-level fields,
- `procedures` list,
- `scopes` list,
- `terms` list,
- `source_document_id`.

Materialization:

1. validates all referenced source document IDs before the transaction;
2. generates deterministic IDs from canonical JSON when IDs are not supplied;
3. inserts exactly one measure and its explicit procedures/scopes/terms;
4. rejects duplicates and malformed codes/amount semantics;
5. builds `arancel_mx_trade_remedies`;
6. includes remedy tables in `PUBLIC_INTERNAL_TABLES` so a future certified release can carry them;
7. does not add remedy data to a release unless remedy rows are supplied by the official build input.

The current production official build will continue to supply no remedy rows until a separate source-promotion step is implemented and verified. This prevents an unreviewed web scrape from silently entering a certified release.

## Source parser boundary

The first slice will add a strict source-specific parser for a **checked fixture** of the supported ceramic resolution facts, not a generic legal-text parser.

It must:

- accept text/evidence already captured for a known SIDOF source;
- extract only patterns covered by fixture tests;
- fail closed when required source phrases or amounts are missing;
- preserve exact party names, numeric values, currency/unit and source identity;
- emit the normalized remedy input consumed by materialization;
- never infer measures from tariff codes alone.

The first fixture will cover:

- one named-party specific duty;
- the residual “other producer-exporters” specific duty;
- both explicit price-undertaking thresholds (6.72 USD/m² FOB China and 8.40 USD/m² CIF Mexico), preserving their pricing basis;
- the three explicitly named 8-digit fractions;
- China origin;
- active + under-review procedural state from the 2026 resolution.

The parser can be expanded with additional official resolutions only through new fixtures.

## Compatibility

- No existing public tariff field changes.
- No existing `Dataset.lookup`, search, suggest, NICO, National Notes or NOM behavior changes.
- Legacy DuckDB releases remain readable.
- New remedy fields/tables are additive.
- Codes remain strings.
- No new runtime dependency.
- No release tag is rewritten.
- `data-2026.11.21` remains immutable.

## Validation and tests

Required tests:

1. schema installs all four remedy tables;
2. materialization stores a named-party duty, residual duty and price undertaking separately;
3. deterministic IDs are stable across repeated builds;
4. invalid fraction/NICO shape fails;
5. unknown source IDs fail before transaction;
6. amount-kind invariants fail closed;
7. public view exposes remedy data without changing the 35% IGI tariff row;
8. consumer query by fraction+China returns possible measures;
9. same fraction with non-China origin returns no hits;
10. missing remedy view on a legacy DB returns an empty tuple;
11. active legal status can coexist with a separate current under-review procedure row and its 2026-10-24 effective date;
12. source document provenance/hash is preserved;
13. build/export copying includes remedy tables when present;
14. general tariff tests remain unchanged and green.

## Documentation

Update the D4 roadmap status and consumer/data-model docs to say:

- trade remedies are a separate official-measure domain;
- code/origin lookup is retrieval only;
- exporter/product facts still determine actual applicability;
- remedy amount is never added to IGI/IGE automatically.

## Non-goals

- shipment-level duty liability;
- origin determination;
- exporter identity inference;
- automatic legal advice;
- a generic parser for arbitrary DOF prose;
- full historical population of every remedy;
- preferential tariff logic;
- web UI or public HTTP endpoint in this first slice;
- a new certified data release before source promotion and release verification are separately completed.

## Rollout

1. Merge the additive foundation with fixture-backed behavior.
2. Keep issue #301 open.
3. Follow with a source-promotion slice that captures verified SIDOF bytes/hashes and feeds normalized remedy rows into the official build.
4. Only then publish a new immutable data release and verify the manifest/source archive.
5. Add static/API/UI surfaces additively after the data contract is stable.
