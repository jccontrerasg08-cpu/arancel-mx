# Treaty preferences research spike

**Status:** exploratory — not yet part of the verified core dataset.

## Goal

Assess the feasibility of adding a clearly labeled, provenance-tracked layer for preferential tariff rates under Mexico’s free-trade agreements (T-MEC, EU, CPTPP, etc.) without contaminating the core LIGIE/NICO verified tariff.

## Current boundary

The public `arancel_mx` view and the static API expose only the general IGI/IGE rates from the verified LIGIE snapshot. Preferential rates, PROSEC, IMMEX, and non-tariff regulations are intentionally out of the core contract (see project overview and research coverage map).

## Spike questions

1. Which official instruments publish the preferential rate schedules (DOF decrees, SNICE annexes, treaty annexes)?
2. Can each preferential rate be tied to a fraction, an origin rule, and a validity interval with the same SHA-256 / instrument-identity discipline used for general rates?
3. What is the expected cardinality and update frequency?
4. How should the consumer surface distinguish “general rate” from “preferential rate (requires origin proof)”?

## Recommended next step (if pursued)

- Produce a small, versioned inventory of 2–3 treaties (T-MEC + one other) with source URLs, hashes, and a proposed schema that lives **beside** the core dataset (separate table or separate release asset).
- Do **not** merge preferential rates into the existing `igi_text` column.
- Keep the fail-closed rule: if the official source does not list a preference for a fraction, the dataset must not invent one.

## Non-goals

- Automatic classification of origin.
- Legal advice on whether a particular shipment qualifies.
- Replacing the official SNICE or VUCEM tools.
