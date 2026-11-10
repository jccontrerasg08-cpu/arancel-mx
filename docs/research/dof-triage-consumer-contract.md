# DOF trade-change triage as a supplemental research signal

> **Non-production integration note.** This document is a review gate and developer handoff, not an automatic change feed into arancel-mx. The certified arancel-mx release chain, legal instruments ledger, official reconciliation, and read-only static API remain unchanged.

## Existing, independent official monitoring

The existing `scripts/watch_dof.py` in this repository fetches official SIDOF notes across several days and proposes **GitHub issues for human review** for possible tariff instruments. That procedure already exists and must remain the authoritative repository-local monitoring workflow; it never modifies tariff data or decides the legal effect of a notice.

Separately, the public `dof-diff-lab` repository now offers an offline `triage` command over its local normalized catalogs, which produces broader *title-only* trade-regulation candidate JSON. This supplementary signal can help a researcher find material outside a narrowly tariff-focused keyword set, particularly **RGCE, RRNA, permits and import/export quotas**.

| Concern | arancel-mx `watch_dof.py` | DOF Intelligence Lab `triage` |
|---|---|---|
| Primary input | Official SIDOF service | Already normalized, locally stored SIDOF/DOF titles |
| Output | Review-only issue candidates | Read-only candidate JSON with rule IDs, official URL and coverage |
| Possible use | Tariff evidence review | Research backlog or trade-regulation discovery |
| Authority | No legal effect asserted | No legal effect asserted |
| Can update tariffs? | No | No |
| Can publish a dataset? | No | No |
| Handles absent publications? | Existing monitor semantics | A missing local catalog is **not** an authoritative no-publication event |

## Contract and review gates

1. Independently run `python -m dof_diff_lab sync --date YYYY-MM-DD --root .` inside the other repository to capture official metadata. The project must preserve title-source provenance and any available SHA-256.
2. `python -m dof_diff_lab triage --root . --start YYYY-MM-DD --end YYYY-MM-DD` prints versioned JSON. Review `schema_version=1.0`, `rule_version=trade-title-v1`, `status`, and `coverage` before interpreting any candidates.
3. Only examine rows with `review_status=unverified_title_match` and an official `https://dof.gob.mx` or `https://sidof.segob.gob.mx` source. The `priority_review` field is a lexical prioritization **not a legal or financial severity score**.
4. Compare candidates against the existing `dof-candidate` issues and official tariff sources, avoiding duplicated review work. **Never import a candidate into `legal_instruments.json` automatically.**
5. A human must read the **full official instrument** to confirm its domain, affected tariff codes, effective dates, scope, retroactivity, subsequent amendments and relevance. A title match can be false; absence of a match does not mean the law did not change.
6. A verified change follows the **existing fail-closed official dataset pipeline** with sources, instrument registry, reconciliation, validation and immutable release gates; it is not applied from the triage output.

### Example command

```bash
# Run from a checked-out copy of the DOF Intelligence Lab repository,
# after the relevant date has been independently synchronized.
python3 -m dof_diff_lab triage --root . --start 2026-11-01 --end 2026-11-10 --limit 100
```

**Do not** put the above command in the official arancel dataset builder. Its intended role is an analyst's triage workflow, and its results do not certify changes to TIGIE/NICO. It is acceptable to discuss discoveries as hypotheses subject to independent verification.

## Architecture decision

Keep both watchers separate. Treat the DOF triage feed as a low-trust discovery signal, not as a new canonical legal source. `arancel-mx` already has the tested official watcher and strict evidence ledger, so building a second automatic publisher or duplicating SIDOF ingestion here would add unnecessary risk and maintenance. If we later propose automated feeds across repositories, require a versioned consumer schema, recorded deduplication evaluation, official-domain link checks, publication-date coverage metrics, manual review, and zero write permission to the data/release pipelines.

See [DOF Intelligence Lab](https://github.com/jccontrerasg08-cpu/dof-diff-lab) and its [trade watch contract](https://github.com/jccontrerasg08-cpu/dof-diff-lab/blob/main/docs/trade-watch-contract.md). This integration note assumes that feature has passed CI and is merged before users rely on the command.

