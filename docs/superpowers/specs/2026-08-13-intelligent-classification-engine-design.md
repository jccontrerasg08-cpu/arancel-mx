# Intelligent Classification Engine / TariffPro Benchmark

**Status:** Draft design pending user review  
**Date:** 2026-08-13  
**Block:** 2 of the [AduanaMap Architecture Master Spec](./2026-08-13-aduanamap-architecture-master.md)  
**Owner:** AduanaMap (application). Not implemented in `arancel-mx`.  
**Upstream data:** [External consumption contract](./2026-08-13-external-consumption-contract-design.md)  
**Benchmark:** Camtom TariffPro overview and classification guide (user-reviewed 2026-08-13). Camtom pages were not fetchable from this environment; this spec uses the user’s notes plus official LIGIE/NICO structure already modeled in `arancel-mx`.

## 1. Goal

AduanaMap classifies Mexican goods with a pipeline where **the model proposes and the structured dataset validates**.

A successful turn is:

```text
input (text now; image/PDF/invoice later)
  -> ProductClassificationProfile
  -> sufficiency gate (or QUESTIONS_REQUIRED)
  -> hierarchical search HS2 → HS4 → HS6 → fraction8 → nico2
  -> legal validation against published instruments when present
  -> candidate validation against a pinned arancel-mx data-* release
  -> result with selected / excluded / unresolved, questions,
     calibrated confidence, evidence, source_trace
```

The engine may continue across turns by updating a **structured session**, not by hoping the LLM remembers the chat.

## 2. Non-goals

This spec does not:

- implement the engine inside `arancel-mx`;
- add OCR, vision, or PDF parsing to `arancel-mx`;
- publish IVA, NOM, RRNA, permits, padrones, or trade remedies as part of the classification decision;
- treat `HsSection` titles in `arancel_mx.consumer.hs_sections` as captured legal notes (they are structural chapter-range labels);
- invent section/chapter/subheading notes, GIR text, or complementary-rule text when `arancel-mx` has not published those instruments;
- model a 10-digit string as `fraction`;
- use `confidence = llm.ask("How confident are you? 0-100")`;
- copy Camtom’s “NICO = national notes” or “6 GIR + 1 Mexican rule” wording into the Wiki or the reasoner;
- make AI output canonical over `Dataset.lookup` / parent-chain checks.

## 3. TariffPro benchmark — adopt vs refuse

| TariffPro pattern | Decision | AduanaMap form |
|---|---|---|
| Three-stage flow: product coherence → hierarchical walk → summary/confidence | **Adopt, expand** | Six stages in §6, with explicit sufficiency and candidate validation |
| Extract material, function, presentation, use before coding | **Adopt** | `ProductClassificationProfile` |
| Return questions when certainty is low | **Adopt** | `NEEDS_MORE_INFORMATION` + structured `questions[]` |
| Show considered and discarded 4-digit codes | **Adopt, deepen** | Exclusions at every level with `reason_code`, note/rule ids, evidence |
| Multi-turn follow-up questions | **Adopt, change storage** | `classification_session` object, not chat-only memory |
| Text / image / PDF / invoice / Excel / JSON inputs | **Adopt as funnel** | All inputs collapse to the same profile; extraction is Block 4 |
| Up to three attempts with validation feedback | **Adopt** | Max three propose→validate loops per turn; feedback is structured errors, not free text |
| Two cost/latency tiers | **Adopt** | `fast` and `thorough` in §14 |
| Confidence 0–100 bands (high/medium/low/very low) | **Adopt UX, refuse definition** | Bands from calibrated score; factors are observable |
| “Fracción de 10 dígitos” as the internal key | **Refuse** | 8+2 fields; `classification10` is a derived identifier |
| “NICO determined by national legal notes” | **Refuse** | Complementary Rule 10ª + agreement + notes + methodology |
| “6 GIR + 1 Mexican complementary rule” | **Refuse** | Distinct GIR, complementary rules, national notes |
| RRNA bundled with classification | **Refuse** | Block 5 after classification status is confirmed |
| Self-reported model confidence | **Refuse** | Derived + empirically calibrated |

## 4. Approaches

### Approach A — AduanaMap engine, `arancel-mx` validator (recommended)

The classifier, session store, evals, and UX live in AduanaMap. Every candidate is checked with a pinned `arancel-mx` dataset (`code` exists, parent chain, `ligie_version`, `as_of` / current flags, provenance ids). Legal notes are consumed only after Block 3 publishes them.

- Pros: keeps the approved data/application split; validator is reproducible; evals can replay against frozen `data-*` tags.
- Cons: full legal-note reasoning waits on Block 3.

### Approach B — Put the classifier in `arancel-mx`

Add an optional `arancel-mx classify` extra with LLM calls.

- Pros: one repo.
- Cons: turns the data product into an AI service; contradicts Block 1 and the PyPI consumer non-goals.

### Approach C — LLM classifies, dataset is a post-hoc lookup

The model returns a 10-digit string; AduanaMap only fetches the ficha if the code exists.

- Pros: fastest to demo.
- Cons: inverts “AI proposes, structured base validates”; encourages invented fractions; no exclusion audit trail.

**Recommendation: Approach A**, shipped in two versions:

- **v0** — profile, questions, hierarchy over descriptions, candidate validation against today’s `PUBLIC_COLUMNS`.
- **v1** — same engine, LEGAL VALIDATION enabled once Block 3 data exists.

## 5. Data the validator can use today

From a pinned `data-*` release / `Dataset`:

| Need | Today |
|---|---|
| `hs2` `hs4` `hs6` `fraccion8` `nico2` `nico10` parent chain | Yes |
| Official description / name | Yes (`description`, `name`) |
| IGI/IGE literals | Yes (`igi_text`, `ige_text`, kinds/values) |
| Current flag, effective intervals, `ligie_version`, `dataset_version` | Yes (official builds often use `validity_basis=observed_snapshot` and may leave legal effective dates unset) |
| Per-row provenance | Yes (`primary_source_*`, `Dataset.provenance`) |
| Structural HS section roman/name | Yes, but **not** legal notes (`source=hs_section_grouping`) |
| Section / chapter / subheading notes | **No** — PDF parse stops at `Notas` |
| GIR / complementary rules text | **No tables** |
| National notes body | Schema + empty view `arancel_mx_national_notes`; official pipeline does not populate |
| NICO annotations | **No model** |
| IVA / NOM / RRNA / TLC | Out of `arancel-mx` contract |

v0 must not emit `supporting_note` / `supporting_rule` ids unless those objects were loaded from a published instrument table. If the user asks “why this chapter note?”, v0 answers `missing_legal_instruments`.

## 6. Pipeline

```text
INPUT
  │
  ▼
PRODUCT FACT EXTRACTION
qué es / material / función / composición / presentación /
proceso / dimensiones / uso / estado / marca-modelo
  │
  ▼
INPUT SUFFICIENCY
  ├── insuficiente ──► QUESTIONS_REQUIRED (end turn; persist session)
  │
  ▼
CLASSIFICATION SEARCH          (max 3 propose→validate loops)
  │
  ├── Section (structural grouping only, until Block 3 notes exist)
  ├── Chapter HS2
  ├── Heading HS4
  ├── Subheading HS6
  ├── MX Fraction8
  └── NICO2 → classification10
  │
  ▼
LEGAL VALIDATION
  ├── heading/subheading texts (description today; dedicated legal text later)
  ├── section notes
  ├── chapter notes
  ├── subheading notes
  ├── reglas generales (GIR)
  ├── reglas complementarias MX
  ├── notas nacionales / anotaciones NICO
  └── vigencia
  │
  ├── instrument missing ──► mark UNRESOLVED / missing_legal_instruments
  │
  ▼
CANDIDATE VALIDATION           (always; arancel-mx)
  ├── code exists in pinned dataset?
  ├── edition / ligie_version match?
  ├── effective on as_of? (or is_current if as_of omitted)
  ├── parent chain valid?
  └── exclusion conflict?
  │
  ▼
RESULT
  ├── recommended candidate | QUESTIONS_REQUIRED | UNRESOLVED | NO_CONFIRMABLE
  ├── alternatives
  ├── excluded candidates
  ├── questions
  ├── evidence
  ├── calibrated confidence
  └── source_trace
```

**Critical rule:** a candidate that fails CANDIDATE VALIDATION is never the recommended code, regardless of model score.

### 6.1 Propose→validate loops

Each turn may run at most **three** search loops. After a failed validation, the next proposal receives structured feedback, for example:

```text
rejected_code = 7304
reason_code = parent_chain_invalid | code_not_in_dataset | exclusion_conflict
validator_message = "7304 is not current in data-2026.08.11"
```

The model does not get a fourth loop. If still invalid: `UNRESOLVED` or `QUESTIONS_REQUIRED`, never a guessed code.

## 7. ProductClassificationProfile

All input types (text, later image/PDF/invoice/JSON) normalize to one profile before search.

```json
{
  "identity": {
    "common_name": null,
    "technical_name": null
  },
  "composition": [],
  "function": null,
  "intended_use": null,
  "presentation": null,
  "manufacturing_process": null,
  "technical_characteristics": {},
  "dimensions": {},
  "state": null,
  "brand": null,
  "model": null,
  "completeness": {
    "required_fact_ids": [],
    "known_fact_ids": [],
    "unknown_fact_ids": []
  }
}
```

Facts are typed key/value objects with `value`, `confidence_in_extraction` (separate from classification confidence), and `evidence_span` or extractor id. Extraction confidence must not be copied into `classification_confidence.score`.

Unknown facts stay `null` / empty. The engine must not fill them with model guesses marked as known.

## 8. Required questions

If sufficiency fails, the HTTP/API status of the classification object is `NEEDS_MORE_INFORMATION`. The engine does **not** pick a heading to look decisive.

Example shape:

```json
{
  "status": "NEEDS_MORE_INFORMATION",
  "questions": [
    {
      "id": "manufacturing_method",
      "question": "¿Es sin costura o soldado?",
      "reason": "La respuesta distingue partidas candidatas.",
      "discriminates": ["7304", "7305", "7306"]
    }
  ]
}
```

Question `id` values are stable snake_case keys that write into the profile (`manufacturing_process`, `composition`, `dimensions.outside_diameter`, …). Free-form chat answers are parsed back into those keys, then the pipeline reruns from SUFFICIENCY.

A chatbot that returns a code plus “93% confianza” without questions is a spec violation.

## 9. Classification session

Persist structured state, not only transcripts:

```text
classification_session
        ├── original_input
        ├── extracted_product_facts     (ProductClassificationProfile)
        ├── answered_questions
        ├── unresolved_questions
        ├── candidate_set
        ├── excluded_candidates
        ├── source_versions             (package + data-* + instrument corpus)
        └── final_decision
```

Turn 2 merges new answers into the profile (`material = stainless_steel`, `head = hexagonal`, `thread = M10`) and **re-executes** the classifier. The LLM is not asked to “remember” turn 1.

Sessions pin `dataset_version` at creation. A later `data-*` publish does not silently mutate an open session. The client may explicitly refresh versions.

## 10. Excluded and unresolved candidates

Every discarded node stores:

```text
candidate_code
level                   hs2 | hs4 | hs6 | fraccion8 | nico10
classification_edition  ligie_version
decision                excluded | unresolved
reason_code
reason_summary
supporting_note         id or null
supporting_rule         id or null
evidence
dataset_version
```

`reason_code` is a closed enum. Initial set:

```text
more_specific_heading_exists
product_function_inconsistent
composition_inconsistent
presentation_inconsistent
excluded_by_heading_text
excluded_by_section_note
excluded_by_chapter_note
excluded_by_subheading_note
excluded_by_gir
excluded_by_complementary_rule
excluded_by_national_note
nico_requires_complementary_rule_10
code_not_in_dataset
edition_mismatch
not_effective_on_as_of
parent_chain_invalid
missing_legal_instruments
missing_product_facts
```

Note/rule reason codes require Block 3 data. Until then those codes are not emitted except `missing_legal_instruments`.

## 11. Legal-instrument model (Wiki + reasoner)

Keep three LIGIE instrument families separate:

```text
Reglas Generales (GIR)
Reglas Complementarias (including 10ª for NICO design)
Notas Nacionales
```

NICO object (when Block 3 exists):

```text
NICO
├── legal_basis: Regla Complementaria 10ª
├── official NICO agreement
├── annotations
├── methodology
├── applicable classification rules
└── relevant national notes
```

Do not store or display “NICO = Nota Nacional”.

Heading text used in v0 is `description` from `arancel-mx`. That is nomenclature wording from the official parse, not a substitute for notes the PDF parser currently skips.

## 12. Candidate validation against `arancel-mx`

Always pin one dataset. Default `as_of` is “current rows in that release” (`is_current`). An explicit `as_of` date uses effective intervals when `validity_basis=legal`; if the release only has `observed_snapshot`, the API must warn `validity_basis_observed_snapshot` and not pretend a legal in-force date.

Checks, in order:

1. Normalize to `hs6` / `fraccion8` / `nico2` / `classification10`. Reject a single field named `fraction` holding 10 digits.
2. `Dataset.lookup(code)` (or equivalent SQL on `arancel_mx`) must hit exactly one current row for that `as_of` policy.
3. Parent chain: NICO → fraction8 → hs6 → hs4 → hs2 must match columns on the row and exist as their own current rows.
4. `ligie_version` on the row equals the session edition (official default today is the dataset’s `ligie_version`, often `LIGIE-2022`).
5. Duplicate current rows: treat as dataset error (`NO_CONFIRMABLE` / `duplicate_current_records`), do not pick “latest” in the classifier.

Display IGI/IGE from `igi_text` / `ige_text` after a code is selected. Rates are not inputs to heading choice except as corroborating evidence.

## 13. Result envelope

```json
{
  "data": {
    "status": "LIKELY | CONFIRMED | NEEDS_MORE_INFORMATION | UNRESOLVED | NO_CONFIRMABLE",
    "classification": {
      "system": "MX_TIGIE_NICO",
      "edition": "LIGIE-2022",
      "as_of": "2026-08-11",
      "hs2": "73",
      "hs4": "7318",
      "hs6": "731815",
      "fraction8": "73181501",
      "nico2": "00",
      "classification10": "7318150100"
    },
    "product_profile": {},
    "alternatives": [],
    "excluded_candidates": [],
    "required_questions": [],
    "reasoning_summary": {
      "rules_applied": [],
      "legal_notes": [],
      "decisive_product_facts": []
    },
    "confidence": {
      "score": 0.0,
      "band": "high | medium | low | very_low",
      "calibration_version": "uncalibrated-v0",
      "factors": []
    }
  },
  "meta": {
    "classifier_version": "aduanamap-cls-0.1.0",
    "mode": "fast | thorough",
    "dataset_versions": {
      "arancel_mx_package": "0.2.0",
      "dataset": "data-2026.08.11",
      "instrument_corpus": null
    },
    "session_id": "..."
  },
  "source_trace": [],
  "warnings": []
}
```

Wire-name alias: JSON `fraction8` maps to dataset column `fraccion8`. JSON `classification10` maps to `nico10`. Never map 10 digits onto `fraccion8`.

`CONFIRMED` is reserved for cases where candidate validation passed **and** required legal instruments for that decision were present and consistent. v0 without Block 3 should not emit `CONFIRMED` for note-dependent distinctions; `LIKELY` or `NEEDS_MORE_INFORMATION` is the ceiling.

`NO_CONFIRMABLE` covers validator contradictions (missing code, broken parent, duplicate current rows). That is stronger than “we are unsure”.

`classification` may be null when status is `NEEDS_MORE_INFORMATION` or `NO_CONFIRMABLE`.

## 14. Cost and latency modes

Two modes, selected by the client:

| Mode | Search loops | Legal validation | Typical use |
|---|---|---|---|
| `fast` | 1 | Heading/subheading `description` + candidate validation only | Interactive typing, bulk pre-screen |
| `thorough` | up to 3 | Full instrument walk when corpus present; otherwise explicit `missing_legal_instruments` | Human review, audit export |

`thorough` is not allowed to hallucinate notes to look complete. If Block 3 is missing, `thorough` still costs more (extra retrieval and loops) but its legal_notes array stays empty and `warnings` includes `instrument_corpus_unavailable`.

## 15. Classification vs regulatory applicability

```text
PRODUCT
   ↓
CLASSIFICATION          ← this spec
   ↓
confirmed/candidate code
   ↓
REGULATORY APPLICABILITY   ← Block 5, not here
   ├── RRNA
   ├── NOM
   ├── permits
   ├── padrones
   ├── customs restrictions
   └── trade remedies
```

Until classification status is `CONFIRMED` or the client explicitly asks for a preview, regulatory fields are:

```text
regulatory_applicability: UNRESOLVED_UNTIL_CLASSIFICATION_CONFIRMED
```

Do not let an RRNA hit drive the heading choice.

## 16. Confidence

`confidence.score` is in `[0, 1]`, derived from observable factors, then mapped through a calibration table.

Factors (each recorded in `confidence.factors`):

```text
input_completeness
candidate_ambiguity
hierarchy_validation
note_conflicts
rule_support
viable_candidate_count
source_completeness
model_agreement
retrieval_evidence_quality
```

`model_agreement` may include a raw model score as **one factor**, never as the published score.

Calibration:

```text
tests/evals/classification/     (AduanaMap repo)
  ├── cases.jsonl               Git-authoritative, reviewed labels
  ├── splits
  └── calibration_version
```

Each eval case pins `dataset` tag, profile facts, expected `classification10` or expected `NEEDS_MORE_INFORMATION`, and allowed exclusions. Cases whose official code later changes must fail until relabeled.

It is valid that:

```text
model_factor = 0.92
calibrated_score = 0.68
```

Band cut-points are part of `calibration_version` and must not be hard-coded in prompts.

v0 may ship with an **uncalibrated** mapping (weighted factors, `calibration_version=uncalibrated-v0`) if the eval set is still small. The API must then set `warnings` to include `confidence_uncalibrated`. Shipping a 0–100 number without that warning is a spec violation.

## 17. Source trace

Each result `source_trace[]` item is at least:

```text
role            profile_extraction | retrieval | validator | instrument
code            if applicable
source_document_id
source_url
sha256
dataset_version
```

Validator entries must be reconstructible from `arancel-mx` provenance for the selected code. Do not cite SIICEX/VUCEM as legal identity.

## 18. Error handling

| Condition | Status | Behavior |
|---|---|---|
| Missing discriminating facts | `NEEDS_MORE_INFORMATION` | Questions; no recommended code |
| Code not in dataset | exclude; maybe `NO_CONFIRMABLE` | Never return that code |
| Parent chain broken | `NO_CONFIRMABLE` | Dataset bug or bad proposal |
| Notes required, corpus absent | `UNRESOLVED` or `LIKELY` + warning | `missing_legal_instruments` |
| Duplicate current rows | `NO_CONFIRMABLE` | Do not auto-pick |
| Offline dataset missing | transport error | No classification payload |
| LLM timeout after 3 loops | `UNRESOLVED` | Keep exclusions and questions gathered so far |

## 19. Testing

AduanaMap tests (not `arancel-mx` CI):

1. Profile merge: turn-2 answers overwrite nulls and do not drop turn-1 known facts.
2. Sufficiency: `"tubo de acero"` → `NEEDS_MORE_INFORMATION` with manufacturing/steel-type questions; no `classification10`.
3. Validator: a proposed 10-digit code absent from a fixture dataset cannot appear as recommended.
4. 8+2: payload with `"fraction": "7318150100"` is rejected; canonical fields required.
5. Exclusion records persist after a later selected code.
6. Session pins `data-*`; lookup uses that pin.
7. `fast` does not emit note-based `reason_code`s when corpus is null.
8. Confidence: published score ≠ raw model factor; uncalibrated warning when applicable.
9. RRNA fields absent from Block 2 responses.
10. Eval replay: frozen cases vs frozen dataset tag.

`arancel-mx` remains responsible for hierarchy/integrity tests of the dataset itself.

## 20. Implementation sequence (after this spec is approved)

This is the intended AduanaMap plan, not work in this PR:

1. Session + profile schema + question objects (no LLM).
2. Validator adapter over `arancel-mx` `Dataset` (exists / parent / pin).
3. v0 search over descriptions + max 3 loops + exclusions.
4. `fast` / `thorough` flags.
5. Eval fixtures + uncalibrated confidence warning.
6. Stop until Block 3 publishes instruments; then v1 legal validation + calibration.

Do not implement steps 1–6 in `jccontrerasg08-cpu/arancel-mx`.

## 21. Success criteria

- “tubo de acero” does not force a heading.
- Discarded headings remain auditable after the user supplies diameter and weld type.
- A recommended `classification10` always exists as `fraccion8`+`nico2` in the pinned release with a valid parent chain.
- Public copy never says NICO is “just national notes” or that Mexico’s internal key is a 10-digit fracción.
- Confidence is factor-based; Camtom-style bands are UX only.
- `arancel-mx` still has no classifier, OCR, or hosted classify API.
