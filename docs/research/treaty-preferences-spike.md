# Treaty preferences research spike

**Status:** exploratory. Not implemented. Not part of the verified core dataset.

## Boundary

The public view `arancel_mx` and `/data/v1` publish the general IGI/IGE from the verified LIGIE snapshot. A preferential rate under T-MEC, the EU agreement, CPTPP, or any other treaty is a different legal fact: it applies only when origin is proved. It must not be written into `igi_text`, `igi_kind`, or `igi_value`.

If an official source does not list a preference for a fraction, the dataset must not invent one.

## Proposed side asset (not built)

If this is pursued, publish a separate release asset, for example `preferences.json`, with its own SHA-256 line in `SHA256SUMS`. Do not add columns to `PUBLIC_COLUMNS` in the first iteration.

One row would need at least:

| Field | Required meaning |
|---|---|
| `code` | Current `fraccion8` that already exists in the verified dataset |
| `treaty_id` | Stable id of the agreement, not a display name alone |
| `preferential_igi_text` | Rate text as published. Not a rewritten percent |
| `origin_rule_ref` | Pointer to the rule of origin, or an explicit `unknown` |
| `proof_required` | Always `true` for a preferential rate |
| `effective_from` / `effective_to` | Only when the instrument states them |
| `source_url` | Official instrument |
| `source_sha256` | Bytes that were read |
| `instrument_id` | Id inside a versioned registry, same discipline as `legal_instruments.json` |

Rejected designs:

- Overloading `igi_text` with the preferential rate and hiding the general rate.
- A boolean `has_treaty` with no instrument.
- Filling a missing schedule with `0%` because a treaty exists in general.

## Open questions before any schema is accepted

1. Which DOF or SNICE annex is the authority for each treaty’s rate list, and which URL stays stable enough to hash?
2. Are preferences expressed on `fraccion8`, on HS6, or on both?
3. How often the annexes change relative to the daily LIGIE pipeline.
4. Whether PROSEC stays a third asset. It is not a treaty preference and should not share this table.

## Non-goals

- Deciding whether a shipment qualifies.
- Classifying origin.
- Replacing SNICE or VUCEM.
