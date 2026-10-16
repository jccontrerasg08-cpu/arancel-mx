# Depth program: from snapshot to a consolidated, point-in-time tariff record

- **Status:** Gate 0 approved by the owner on 2026-10-16 (later gates still need their own confirmation)
- **Operating model:** Claude does the research, code, tests, docs and PRs. The owner confirms every gate. Nothing merges, publishes a release, or changes a public contract without an explicit "yes".
- **Boundary that never moves:** `arancel-mx` retrieves and verifies evidence. It does not classify goods, compute a legally binding duty, or replace the DOF, SAT, ANAM or a licensed customs broker.

## 0. How we work (human-in-the-loop protocol)

Every unit of work runs through the same five steps:

| Step | Claude does | You do |
|---|---|---|
| 1. Propose | Write a one-page decision record in `docs/decisions/NNNN-*.md` (context, options, recommendation, cost, risks). | Approve, edit, or reject. |
| 2. Build | Implement on a feature branch, run lint/types/tests/browser checks locally. | Nothing. |
| 3. Evidence | Post a PR with the numbers: tests, check results, sample diffs, before/after. | Read the evidence summary. |
| 4. Merge | Drive CI to green and answer review comments. | Confirm merge. |
| 5. Publish | Only for data/API changes: prepare the release or deploy. | Confirm publish. |

Rules:

- One gate = one decision record + one PR (or a small, named stack). No surprise scope.
- Each gate ends with **ideas for the next gate**; you choose which ones survive.
- Anything that needs a person, money, credentials or a legal opinion is marked **[owner]** and never assumed.
- Unknown facts (decree dates, counts, rates) are researched and cited from primary sources, never filled from memory.

## 1. Target state

For any code (HS2 → NICO10) and any date, the project can answer, with a citation chain to the published bytes:

1. Did the code exist, and what were its description, unit and hierarchy?
2. What were the IGI/IGE rates, and which DOF instrument set them?
3. What other official measures were attached (preferential schedules, sector programs, quotas, trade remedies, non-tariff requirements), each with its own source and validity?
4. What changed, when it was published, and when it took effect.
5. Where official sources disagree, and how the project resolved each disagreement.

## 2. Workstreams

Each workstream lists what already exists in the repo, what is added, and the external check that proves it.

### A. Legal-temporal core (foundation; everything else depends on it)

Exists: `effective_from`/`effective_to`, distinct time fields (`docs/data-model.md`), `source_history` diffs per release, DOF PDF discovery (`sources/dof_pdf.py`), Chamber of Deputies source (`sources/diputados.py`).

Adds:

- **A1. Instrument inventory.** A registry of every DOF instrument that created or amended the LIGIE (2022 decree onward) and the NICO Acuerdo and its amendments: DOF date, entry-into-force rule, transitory articles, URL, SHA-256, ELI/FRBR-style identifier (work / expression / manifestation).
- **A2. Amendment operations.** Each instrument parsed into typed operations: `create`, `delete`, `modify_description`, `modify_rate`, `modify_unit`, `split`, `merge`, `renumber`, `temporary_rate` (with expiry).
- **A3. Replay engine.** Deterministic replay from the 2022 base to any date, producing a bitemporal table (`valid_from`, `valid_to`, `published_at`, `captured_at`, `instrument_id`).
- **A4. Consolidation check.** Replay output vs Chamber of Deputies consolidated text vs current SNICE/VUCEM capture, per field, written to a disagreement register.
- **A5. `AS OF` everywhere.** `arancel-mx lookup 85171301 --as-of 2024-03-01`, `Dataset(...).as_of(date)`, `GET /v1/lookup/{code}?as_of=`, and a per-code timeline in the web explorer.

Proof: ≥30 dated test points re-derived from DOF text by hand-auditable fixtures; replay result equals consolidated text, or each mismatch has a typed reason.

### B. Extraction quality

- **B1. Dual extraction.** Two independent extractors per source type (e.g. pdfplumber and camelot for PDF tables, plus HTML where it exists). Disagreement blocks the build unless it is listed in a reviewed allowlist.
- **B2. OCR fallback** only for scanned pages, flagged as lower-confidence and never silently mixed with text extraction.
- **B3. Rate grammar.** Formal grammar (Ex., ad valorem, specific, mixed, prohibited, "Ex." partial descriptions, temporary rates) with property-based tests (Hypothesis).
- **B4. Hierarchy invariants.** NICO→fraction→HS6 (HS 2022)→HS4→HS2; no orphans; residual "Los demás" lines consistent; every fraction's HS6 exists in the WCO list.
- **B5. Golden fixtures** for high-risk chapters (textiles, footwear, steel, vehicles, electronics) and a semantic diff per release that names the instrument behind each change.

Proof: zero unresolved parser disagreements; invariant suite passes on every historical replay date, not only today.

### C. Nomenclature depth

- **C1. HS 2022 conformity** at six digits, using WCO correlation tables 2017↔2022.
- **C2. HS 2028 readiness.** Correlation 2022↔2028 once published, and a migration plan for the new LIGIE it will require.
- **C3. Legal notes.** Section, chapter and national notes (Notas Nacionales) and the General Rules of Interpretation as they appear in the LIGIE, versioned like rates.
- **C4. Units.** Unit of measure (UMT) mapped to SAT Annex 22 catalogues.
- **C5. Official classification criteria** published by SAT/ANAM, linked by code with dates. WCO explanatory notes and classification opinions are copyrighted: link and reference only, never redistribute. **[owner]** confirms this licensing stance.

### D. Measures beyond the general rate (each module is optional; you pick)

Each module follows the same pattern as A: instrument inventory → operations → validity → disagreement register → `AS OF`.

- **D1. Preferential schedules** under Mexico's trade agreements (T-MEC/USMCA first, then the EU, CPTPP, Pacific Alliance, ALADI agreements), including phase-out staging.
- **D2. Sector programs (PROSEC) and Rule 8 (Regla Octava)** rates and eligibility text.
- **D3. Quotas (cupos)** published in DOF.
- **D4. Trade remedies.** Antidumping and countervailing duties from DOF resolutions (by code, origin, exporter, rate, validity).
- **D5. Non-tariff requirements (RRNA).** SE, SENASICA, COFEPRIS, SEMARNAT and NOM agreements by code, with validity. Presented as "an official instrument lists this code", never as "you must comply with X".
- **D6. Other taxes at import** (IVA, IEPS, DTA) as dated references only, if you want them at all.

Proof: for each module, a sample of codes checked against the issuing authority's own publication; counts per instrument match the instrument's annex.

### E. External validation (independent of you and me)

- **E1. DOF re-derivation** (from A).
- **E2. Trade-statistics coverage.** Every fraction with recorded imports in INEGI/Banxico foreign-trade statistics for a month exists and is in force in the dataset for that month. Reverse check: codes in force with zero trade for 24 months are listed (not an error, a signal).
- **E3. WTO Tariff Download Facility / IDB and ITC Market Access Map.** Applied MFN rates compared code by code; every difference explained. **[owner]** registers for any account these require.
- **E4. Annex 22 consistency.** Fraction/NICO/unit combinations match SAT catalogues.
- **E5. Broker audit.** ISO 2859-sized, risk-stratified sample packet; a licensed customs broker reviews it blind; error rate reported with its confidence interval. **[owner]** finds and engages the broker; Claude prepares the packet and scoring.
- **E6. Mirror check (optional).** For T-MEC preferential rates, compare against the published US and Canada schedules for the same agreement lines where they correspond.

Release rule: a release states which checks ran, their results, and their dates in `manifest.json`.

### F. Change detection and alerting

- **F1. Daily read-only DOF watcher** (already designed in `docs/source-history.md`): detect new instruments that mention LIGIE, NICO, cupos, cuotas compensatorias, PROSEC or the agreements in D; open an issue with the evidence. It never publishes.
- **F2. Impact preview.** For a detected instrument, a draft operation list and the affected codes before any release.
- **F3. Consumer notifications.** Release feed (Atom/JSON) and per-code change feed so integrators can subscribe to "tell me when 8517.13.01 changes".

### G. Product surfaces

- **G1. Code timeline** page: every version of a code with instrument, dates and diff.
- **G2. Compare two dates**: everything that changed between date X and Y, filterable by chapter and instrument.
- **G3. Instrument page**: one DOF instrument → every operation it made → every affected code.
- **G4. Disagreement explorer**: the register from A4/B1, public, with resolutions.
- **G5. Duty-components view** (only if D modules exist): shows each measure separately with its source, explicitly not a total duty calculation. Wording reviewed by **[owner]**.
- **G6. API**: `as_of`, `/v1/instruments`, `/v1/changes?from=&to=`, `/v1/disagreements`; OpenAPI and compatibility policy updated (`docs/compatibility.md`).

### H. Trust, governance and longevity

- **H1. Supply-chain provenance.** Signed releases (Sigstore / GitHub artifact attestations), SLSA-style build provenance in the manifest.
- **H2. Source preservation.** Captured DOF bytes mirrored to the Internet Archive and stored with the release; Software Heritage for code.
- **H3. Citable data.** Zenodo DOI per data release, `CITATION.cff`. **[owner]** links the Zenodo account.
- **H4. Correction process.** Public issue form "report a data discrepancy" → triage → evidence → fix → release note crediting the reporter.
- **H5. Licensing review.** What can be redistributed (DOF, SAT catalogues, WCO material, trade statistics). **[owner]** decides; Claude prepares the source-by-source table.
- **H6. Metrics.** Coverage, freshness lag (DOF publication → release), disagreement count, external-check pass rates, published on the site.

## 3. Proposed gate order

| Gate | Content | Why this order |
|---|---|---|
| G0 | Approve this program, the protocol, and the licensing stance questions (H5, C5). | Sets the rules. |
| G1 | A1 instrument inventory (research only, no code changes to data). | Everything depends on knowing every instrument. |
| G2 | A2–A3 operations + replay engine behind a flag; B3 rate grammar. | Core model. |
| G3 | B1, B4, B5 extraction quality + invariants on all replay dates. | Make the core trustworthy before exposing it. |
| G4 | A4 consolidation check + disagreement register; E1, E2, E4. | First independent proof. |
| G5 | A5 `AS OF` in CLI/Python/API + G1–G3 web pages; schema/compatibility update. | First user-visible release. |
| G6 | F1–F3 change detection and feeds. | Keeps it current. |
| G7 | C1–C5 nomenclature depth; HS 2028 plan. | |
| G8+ | D modules, one per gate, in the order you choose. | Largest scope; optional. |
| Parallel | E3, E5, H1–H6 as owner items unblock. | |

## 4. What I need from you, ever

- Yes/no/edit at each gate.
- Licensing decisions (H5, C5).
- Accounts or registrations: WTO/ITC data access, Zenodo, any paid source.
- The broker for E5.
- Final wording for anything that could read as advice (G5, D5).

## 5. Decision log

| Date | Gate | Decision |
|---|---|---|
| 2026-10-16 | G0 | Program, protocol and gate order approved as written. |
| 2026-10-16 | G0 | All D modules in eventual scope (D1 preferential/FTA, D2 PROSEC/Regla Octava, D3 quotas, D4 trade remedies, D5 RRNA/NOM, D6 other taxes), each behind its own gate. |
| 2026-10-16 | G0 | Licensing for WCO and other copyrighted material deferred: no such source is used until the H5 source-by-source licensing table is approved. |
| 2026-10-16 | G1 | Inventory verified at text level from the Diputados ledger (26 instruments and amendments). 1,667/1,667 decree-set rates match `data-2026.09.14`; 9803.00.01 is stale after the 2026-10-13 decree; validity fields are empty dataset-wide. Byte capture pending. See `docs/research/ligie-instrument-inventory.md`. |
| 2026-10-16 | F1 | Proposed decision 0001: daily SIDOF watch on Vercel Cron, a GitHub issue as the human confirmation, GitHub Actions only for build and publish. The extra capture workflow was withdrawn. Awaiting owner approval. |
