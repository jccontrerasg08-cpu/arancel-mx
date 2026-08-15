# Suggest infra (PR #78)

Lock retrieve-only `search` / `suggest` already on `cursor/retrieval-suggest-0f14` so the PR is mergeable against current `main`. No new ranking, no WCO CLI, no table restyle.

## In

- Merge `origin/main` (do not rebase/force-push).
- CLI goldens against `consumer_duckdb` (in-process `main()` and `python -m arancel_mx` with `PYTHONPATH=$ROOT/src`):
  - `search reproductores --format json --dataset fixture.duckdb`
  - `suggest reproductores --format json --dataset fixture.duckdb`
- Missing local DuckDB already fails closed (`error:` on stderr, exit 2, not “invalid data release tag”). Keep that test.
- Published-bundle canary, after `data download` + `data verify --bundle`, also runs `arancel-mx suggest reproductores --offline`. Cite needs no network; this does need the downloaded DuckDB.
- Probe / wheel install smoke already run `Dataset.suggest("reproductores")`. Leave them.

## Out

- Do not change `SUGGEST_REPRODUCTORES_TABLE` in `tests/consumer/test_cli_suggest_local.py`.
- Do not add `arancel-mx wco`.
- Do not restyle search/suggest tables (no shared banner helper here).
- No LLM, no nomenclator vendor, no WCO in `source_registry.json`, no SAT anexos in DuckDB, do not say “legally grounded”.

## Errors

Existing consumer boundary: stderr `error: …`, exit 2. Do not invent new codes.

## Tests

`PYTHONPATH=$PWD/src python -m pytest -q` on the files you touch, then `tests/consumer/test_cli_suggest_local.py tests/test_published_bundle_canary.py tests/package/test_consumer_probe.py`.
