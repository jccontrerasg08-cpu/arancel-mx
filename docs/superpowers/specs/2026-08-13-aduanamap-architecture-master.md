# AduanaMap Architecture Master Spec

**Status:** Index of approved and draft blocks; not an implementation plan  
**Date:** 2026-08-13  
**Repositories:**

- Data product: `jccontrerasg08-cpu/arancel-mx` (this repo)
- Application: AduanaMap (separate product; not this GitHub repository)

This document is the index for AduanaMap architecture that depends on `arancel-mx`. Individual blocks are full specs. Do not treat this index as a license to implement a classifier, hosted API, or legal-note parsers inside `arancel-mx`.

## 1. Product boundary

```text
arancel-mx
= DATA PRODUCT
  official sources, fail-closed publication, DuckDB/CSV/JSON,
  provenance, consumer Dataset/CLI

AduanaMap
= APPLICATION USING THAT DATA
  product profiling, classification engine, UX, optional document
  extraction, optional regulatory overlay, optional map/wiki
```

`arancel-mx` remains canonical for **which codes exist**, parent chains, IGI/IGE literals, dataset versions, and source hashes. AduanaMap may **propose** a classification. It may not mint a code that fails structured validation against a pinned `data-*` release.

AI output is never the canonical tariff record.

## 2. Cross-cutting rules (all blocks)

1. Mexican identity is **8 + 2**, not a single “fracción de 10 dígitos”. Wire names: `hs6`, `fraccion8` / `fraction8`, `nico2`, `classification10` (= `nico10` in `arancel-mx`).
2. Fail closed. Missing facts → questions. Missing legal instruments → `UNRESOLVED` / `missing_legal_instruments`, not invented notes.
3. Every decision carries `source_trace` and dataset versions.
4. Classification is not RRNA/NOM/permits. Regulatory applicability is a later stage.
5. NICO is not “the national notes”. Legal basis includes Complementary Rule 10ª of the LIGIE, the official NICO agreement, annotations, methodology, applicable classification rules, and relevant national notes.
6. Do not copy Camtom’s “6 GIR + 1 Mexican complementary rule” simplification. Keep GIR, complementary rules, and national notes as distinct instruments.

## 3. Block index

| Block | Spec | Status | Owner repo |
|---|---|---|---|
| 1. External consumption contract | [`2026-08-13-external-consumption-contract-design.md`](./2026-08-13-external-consumption-contract-design.md) | **Approved** | `arancel-mx` docs + tests |
| 2. Intelligent Classification Engine / TariffPro Benchmark | [`2026-08-13-intelligent-classification-engine-design.md`](./2026-08-13-intelligent-classification-engine-design.md) | Draft pending review | AduanaMap |
| 3. Legal-instrument corpus | *not written* | Blocked on a future `arancel-mx` spec | `arancel-mx` capture/publish of notes and rules |
| 4. Document / image extraction | *not written* | After Block 2 v0 | AduanaMap; OCR stays out of `arancel-mx` |
| 5. Regulatory applicability (RRNA, NOM, permits) | *not written* | After confirmed classification | AduanaMap; not mixed into Block 2 decision |
| 6. Public docs IA / Docusaurus | existing 2026-08-10 design, stale topic map | Follow-up | `arancel-mx` |

## 4. Build order

```text
Block 1  arancel-mx consumption honesty + downstream guide
    │
    ▼
Block 2 v0  AduanaMap classifier using today's Dataset
            (profile, questions, hierarchy, code/parent/as_of checks)
    │
    ▼
Block 3     arancel-mx publishes notes/rules as data
    │
    ▼
Block 2 v1  classifier LEGAL VALIDATION against published instruments
    │
    ├── Block 4  multimodal extraction → same ProductClassificationProfile
    └── Block 5  RRNA/NOM only after classification status is confirmed
```

Block 2 v0 is useful without notes: it can refuse to guess, ask questions, and reject codes that do not exist. It cannot honestly cite section notes or Complementary Rule 10ª until Block 3 exists.

## 5. What this index does not authorize

- Hosted REST inside `arancel-mx`
- Postgres as the `arancel-mx` canonical store
- Fumadocs instead of the approved Docusaurus architecture
- Treating SIICEX/VUCEM as official legal identity
- Relicensing official texts as CC0
- Implementing the classifier in this repository
