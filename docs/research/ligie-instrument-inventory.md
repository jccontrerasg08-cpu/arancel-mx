# LIGIE 2022 instrument inventory (Gate 1, seed)

- **Status:** seed list, **not verified**. Built from web search results because this session's sandbox cannot reach `dof.gob.mx`, `sidof.segob.gob.mx` or `diputados.gob.mx`. No row may be used by the pipeline until it is marked `verified` against the published DOF bytes (URL + SHA-256).
- **Scope:** every DOF instrument that created or changed the LIGIE 2022 Tarifa, plus instruments that change rates for listed fractions through sector programs (PROSEC, IMMEX annexes, basic-basket exemption). NICO Acuerdo and its amendments are still missing (see open items).
- **Primary ledger to verify against:** Cámara de Diputados, LIGIE 2022 reform index (`https://www.diputados.gob.mx/LeyesBiblio/ref/ligie_2022.htm`), which publishes numbered Tarifa PDFs (`LIGIE_2022_tarifaNN_<date>.pdf`). `sources/diputados.py` already parses this ledger.

## Seed rows

| # | DOF date | Edition | Instrument (as reported) | Change type (A2) | Verified |
|---|---|---|---|---|---|
| 1 | 2022-06-07 | — | Decree issuing the LIGIE 2022 (base Tarifa) | base | no |
| 2 | 2022-11-18 | — | Decree amending the 2022 decree | modify (tbd) | no |
| 3 | 2023-01-06 | — | Amendment | tbd | no |
| 4 | 2023-01-16 | — | Amendment | tbd | no |
| 5 | 2023-05-18 | — | Amendment | tbd | no |
| 6 | 2023-06-23 | — | Amendment | tbd | no |
| 7 | 2023-08-15 | — | Temporary rate increases (~392 fractions), later abrogated by #9 | temporary_rate | no |
| 8 | 2023-12-27 | — | Amendment | tbd | no |
| 9 | 2024-04-22 | evening | Temporary rates on ~544 fractions (5–50 %), valid to 2026-04-23; abrogates #7 (Diputados `tarifa09`) | temporary_rate, abrogation | no |
| 10 | 2024-05-08 | — | Amendment | tbd | no |
| 11 | 2024-08-26 | — | Amends Sector Promotion Programs (PROSEC) decree | D2 | no |
| 12 | 2024-12-19 | evening | Tarifa + IMMEX decree: 35 % on 138 apparel fractions, 15 % on 17 textile fractions; IMMEX annex II removals (Diputados `tarifa11`) | modify_rate, D2 | no |
| 13 | 2025-11-10 | — | Decree modifying Tarifa rates (Diputados `tarifa13`) | modify_rate | no |
| 14 | 2025-12-29 | — | Reform of ~1,463 fractions, increases 5–50 % for non-FTA origins (textiles, footwear, steel, aluminium, auto parts, plastics) | modify_rate | no |
| 15 | 2025-12-31 | — | Amends basic-basket tariff exemption decree | D2 | no |
| 16 | 2026-03-26 | — | Amends a prior Tarifa/sector-program decree; another adds an Article Fourteen (Décimo Cuarto) | tbd | no |
| 17 | 2026-04-23 | evening | Tarifa + PROSEC decree: ~185 fractions kept/updated (5–35 %); PROSEC additions at exempt rate | modify_rate, D2 | no |
| 18 | 2026-10-13 | morning | Decree modifying the Tarifa (SIDOF headline only) | tbd | no |

## Findings that already change the design

- **Expiry and reversion are real, not edge cases.** Row 9 set rates valid until 2026-04-23. Reported reading: fractions not renewed by rows 14 or 17 revert to the rates in force before row 9. The replay engine (A3) must model `temporary_rate` with automatic reversion, not only explicit amendments.
- **Row 18 is three days old.** The current published dataset may not reflect it. This is the first concrete test for the daily watcher (F1) and the replay engine.
- **Tarifa changes travel with other decrees** (IMMEX, PROSEC, basic basket). D2 is closer to the core than planned.

## Open items before Gate 1 can close

1. Read the Diputados index and every `tarifaNN` PDF; fill the exact title, DOF `codigo`, URL, SHA-256, entry-into-force rule and transitory articles for each row.
2. Add the NICO Acuerdo and each amendment (SE, DOF).
3. Add errata (fe de erratas) and evening-edition publications that the search missed.
4. Cross-check against SIDOF by date.
5. Fill the "change type" column from each instrument's text.

## Search sources used for the seed (secondary, not evidence)

- Cámara de Diputados Tarifa PDFs: [22 Apr 2024](https://www.diputados.gob.mx/LeyesBiblio/ref/ligie_2022/LIGIE_2022_tarifa09_22abr24.pdf), [19 Dec 2024](https://www.diputados.gob.mx/LeyesBiblio/ref/ligie_2022/LIGIE_2022_tarifa11_19dic24.pdf), [10 Nov 2025](https://www.diputados.gob.mx/LeyesBiblio/ref/ligie_2022/LIGIE_2022_tarifa13_10nov25.pdf), [index](http://www.diputados.gob.mx/LeyesBiblio/ref/ligie_2022.htm)
- [DOF 19 Dec 2024 note](https://www.dof.gob.mx/nota_detalle.php?codigo=5745788&fecha=19/12/2024); SIDOF notes [5785818](https://sidof.segob.gob.mx/notas/5785818), [5800977](https://sidof.segob.gob.mx/notas/5800977)
- [SCJN DOF synthesis 26 Mar 2026](https://www.scjn.gob.mx/sites/default/files/sintesis_dof_gocdmx/documento/2026-03/DOF%2026032026%20S%C3%8DNTESIS.pdf)
- Commentary: [Galicia, 2026 TIGIE reform](https://galicia.com.mx/links/files/Actualizaciones/GC.-Actualizacion.-Comercio.-Reforma-2026-TIGIE.pdf), [Crowe](https://www.crowe.com/mx/noticias/decreto-modifica-la-tigie-y-el-prosec), [Stratego](https://www.stratego-st.com/?p=36049), [CJ Aduanero](https://blog.cjaduanero.com/e-v-19-12-2024-se-modifica-tarifa-de-la-ligie-y-el-decreto-para-el-fomento-immex/)
