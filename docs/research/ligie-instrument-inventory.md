# LIGIE 2022 instrument inventory (Gate 1)

- **Observed:** 2026-10-16
- **Primary ledger:** Cámara de Diputados, [LIGIE 2022 reform index](https://www.diputados.gob.mx/LeyesBiblio/ref/ligie_2022.htm). Last law reform: DOF 2025-12-29. Latest Tarifa change: DOF 2026-10-13.
- **Machine-readable copy:** [`ligie-instrument-inventory.json`](ligie-instrument-inventory.json)
- **Verification level: text read, not byte-verified.** Each instrument's text was read from the Diputados PDF copy of the DOF publication through an external fetch service, because this session's sandbox cannot reach the official hosts. SHA-256 hashes and DOF-original copies are still pending (see "Open items").

This replaces the earlier search-based seed list. That list had five errors, all fixed here:
- 2023-12-27 and 2025-12-31 are basic-basket exemption decrees, not Tarifa reforms.
- 2023-06-23 is the white-maize decree.
- 2024-08-26 is a PROSEC amendment and is not in the LIGIE ledger.
- 2025-12-29 is a Congress law reform, not an executive decree.
- The 2025-07-21 law reform was missing.

## Instruments

Edition comes from the first-page header (VES = evening, MAT = morning). Instruments are listed in the ledger's order within each section.

| ID | DOF date | Ed. | Instrument | In force | Ends | Rows |
|---|---|---|---|---|---|---|
| orig | 2022-06-07 | | Expedition of the LIGIE 2022 | 10 business days after SAT's readiness notice (date to confirm) | | base |
| ref01 | 2025-07-21 | MAT | Law reform: totoaba fractions, chapter 03 note 4 | 180 days later (≈2026-01-17) | | 11 codes |
| ref02 | 2025-12-29 | MAT | Law reform: Tarifa rates | 2026-01-01 | permanent | 1,463 |
| tarifa01 | 2022-11-18 | VES | Temporary import exemptions | with LIGIE | 2023-05-17, abrogated by tarifa03 | 72 |
| tarifa02 | 2022-11-18 | VES | Tarifa + automotive, IMMEX, border, Chetumal, PROSEC, used vehicles, quotas | with LIGIE | staged/partial | large |
| tarifa02 mod01 | 2024-04-22 | MAT | Amends article Fourteen (quotas) of tarifa02 | 2024-04-23 | | |
| tarifa02 mod02 | 2026-03-26 | MAT | Adds 7302.10.02 rails to the quotas, in-quota Ex. | 2026-03-26 | | 1 |
| tarifa03 | 2023-01-06 | VES | Basic-basket exemption decree | 2023-01-07 | extended to 2026-12-31 | 133 |
| tarifa04 | 2023-01-16 | VES | White maize export 50 % | 2023-01-17 | 2023-06-30, abrogated by tarifa06 | 1 |
| tarifa05 | 2023-05-18 | VES | Basic basket: adds tilapia, removes wheat | 2023-05-18 | | 6 |
| tarifa06 | 2023-06-23 | VES | White maize 50 % import / 50 % export | 2023-06-24 | 2023-12-31 | 1 |
| tarifa07 | 2023-08-15 | VES | Temporary rates on 392 fractions | 2023-08-16 | abrogated by tarifa09 | 392 |
| tarifa08 | 2023-12-27 | MAT | Basic basket extended to 2024-12-31 | 2023-12-28 | | 0 |
| tarifa09 | 2024-04-22 | VES | Temporary rates on 544 fractions (5–50 %) | 2024-04-23 | 2026-04-23 | 544 |
| tarifa10 | 2024-05-08 | VES | Removes aluminium from tarifa09; ammonium sulfate 35 % | 2024-05-09 | | 3 |
| tarifa11 | 2024-12-19 | VES | 35 % apparel / 15 % textiles; IMMEX annexes | 2024-12-20 | 2026-04-23 | 155 |
| tarifa12 | 2024-12-31 | VES | Basic basket changes, extended to 2025-12-31 | 2025-01-01 | | 35 |
| tarifa13 | 2025-11-10 | VES | Sugar 156 % / 210.44 % | 2025-11-11 | permanent | 8 |
| tarifa14 | 2025-12-31 | MAT | Basic basket removals, extended to 2026-12-31 | 2025-12-31 (art. 1 from 2026-01-01) | | 33 |
| tarifa15 | 2026-04-23 | VES | 185 fractions at 5–35 % + PROSEC | 2026-04-24 | permanent | 185 |
| tarifa16 | 2026-10-13 | MAT | 9803.00.01 auto-assembly parts → Ex. | 2026-10-14 | 2031-10-14 (five years) | 1 |
| acuerdo01 | 2022-07-14 | | Correlation tables TIGIE 2020–2022 | | | not read |
| acuerdo02 | 2022-08-22 | MAT | NICO and correlation tables | with LIGIE | | 12,455 pairs |
| acuerdo02 mod01 | 2023-06-30 | MAT | NICO: +53, −18 | | | |
| acuerdo02 mod02 | 2024-03-22 | MAT | NICO: +6, −3 | 2024-03-22 | | |
| acuerdo03 | 2022-12-02 | | National Notes | | | not read |

"Rows" counts tariff rows recovered by the local parser. They equal the counts each decree states for itself (544, 155, 1,463, 185).

## Checks against the published dataset `data-2026.09.14`

| Check | Result |
|---|---|
| Current rate for every fraction set by tarifa10, tarifa13, ref02, ref01 and tarifa15, applied in order of entry into force | **1,667 / 1,667 match** (IGI and IGE) |
| NICOs created by acuerdo02 mod01/mod02 present | 59 / 59 |
| NICOs suppressed by acuerdo02 mod01/mod02 absent | 21 / 21 |
| Temporary rates (tarifa09 minus 2 removed, plus tarifa11) that expired on 2026-04-23 without renewal | **0 of 697**: every one was renewed by ref02 or tarifa15. The earlier "automatic reversion" reading from secondary commentary is not supported by the texts. |
| tarifa15 rate changes against the rate it replaced | 0 of 180 overlapping fractions; 5 newly set, all matching |
| 9803.00.01 after tarifa16 (in force 2026-10-14) | **Stale**: dataset and live API show IGI 10; the decree sets Ex. The pipeline reads rates from the SNICE workbook, so the dataset changes only after SNICE republishes it; the pipeline does not read decrees. |
| Fractions without any NICO | 49. 43 are prohibited-import fractions that also have no NICO in acuerdo02 (consistent). **6 are the totoaba fractions created by ref01** (0302.89.02, 0302.99.04, 0303.89.02, 0303.99.04, 0304.89.01, 0304.89.02); no NICO instrument in the ledger covers them. |
| Validity fields in the dataset | `effective_from`, `effective_to`, `rate_effective_*`, `published_at` are empty on all 26,641 current rows; `validity_basis` is `observed_snapshot`. This is the gap workstream A closes. |
| Description text | 0304.89.02 reads "manejo **intesivo**" in the dataset; the DOF text reads "manejo intensivo". First entry for the disagreement register. |

## What this changes in the plan

- **Operation types needed by the replay engine (A2)**, all observed in real instruments:
  - `modify_rate`, `create`, `temporary_rate` with fixed end date or duration, `staged_rate` (tarifa02 steel phase-down), `abrogation`, `derogation` of articles of another decree (tarifa07 → tarifa02);
  - `remove_from_decree` (tarifa10 → tarifa09), `extend_validity` (basic basket), `quota_rate` (tarifa02 article Fourteen), and NICO `create`/`suppress`/`annotation`;
  - entry into force by fixed date, by day of or day after publication, by a duration ("180 days"), or by an external event (the SAT readiness notice).
- **Sector programs travel with the Tarifa.** tarifa02, tarifa07, tarifa09, tarifa11 and tarifa15 also amend PROSEC or IMMEX, and basic-basket exemptions are their own decree chain. D2 should follow right after the core.
- **Quota rates are separate from general rates.** 7302.10.02 shows 20 % (general) and Ex. (in quota) at the same time. The model needs a separate measure layer (D3), not an overwrite.

## Open items

1. **Byte capture and SHA-256:** fetch each instrument's Word file and signed edition PDF through the SIDOF services (`/documentos/doc/{codNota}`, `/documentos/pdf/{codDiario}`; see decision 0001), or run `scripts/capture_instrument_research.py` locally for the Diputados copies.
2. **LIGIE 2022 entry-into-force date:** find the SAT notice. The original and the consolidated Tarifa PDFs time out on the fetch service, so this was not read.
3. **1005.90.04 white maize export rate:** the dataset shows IGE 50. The only temporary 50 % export rate ended on 2023-12-31. Confirm the base rate in the original or consolidated Tarifa.
4. **Totoaba NICOs:** search DOF for a NICO amendment after 2024-03-22 that the ledger does not list.
5. **acuerdo01 and acuerdo03** (correlation tables, National Notes): not read yet.
6. **ref01 day count:** confirm 2026-01-17 under the applicable counting rule.
