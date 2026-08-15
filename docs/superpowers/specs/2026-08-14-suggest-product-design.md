# Suggest product (stacked PR)

Human CLI face on top of PR #78. Stack on `cursor/retrieval-suggest-0f14`. New branch `cursor/suggest-product-0f14`.

## In

- `arancel-mx wco cite 61|gir` — print URL and local path if cached; never downloads.
- `arancel-mx wco download 61|gir` — `--offline` fail-closed (`WcoSupportError`, stderr `error:`, exit 2).
- Shared banner helper for **search and suggest** table rows:

  `--- {i}/{n}  {code}  score={score}  confidence={confidence}  scorer={scorer_version} ---`

- `suggest` still prints ficha + notas nacionales + WCO support URL (cite, never download).
- `search` table uses the banner, then one compact line (`formatted_code  Nivel  description`). No ficha.
- Spanish `--help` for `suggest` and `wco` (and nested `cite` / `download`).
- CLI golden: `suggest reproductores` on a fixture **with** a real `arancel_mx_national_notes` row (reuse the insert in `test_suggest_national_notes_attach_when_present`).
- Empty suggest table: retrieve-only disclaimer, then `No results.`
- JSON/CSV contracts stay (keys, CSV headers). Table is the human face.

## Out

- No LLM, no nomenclator vendor, no WCO in `source_registry.json`, no SAT anexos in DuckDB, do not say “legally grounded”.
- Do not touch canary workflow (infra PR owns it).
- Do not change `tests/consumer/test_cli_search_json.py` or `tests/consumer/test_cli_suggest_json.py` if present.

## Errors

- `WcoSupportError` subclasses `ArancelMXError` so `main()` prints `error:` and returns 2.
- Invalid chapter / unknown target: argparse or the same `error:` / 2 boundary. No traceback.
- `cite` never calls download. Offline + missing cache on `download` fails closed.

## Tests

New `tests/consumer/test_cli_wco.py` (cite URL, cite does not download, download `--offline` missing cache, `gir`). New search table golden. Notes-present suggest golden. Spanish help asserts. `PYTHONPATH=$PWD/src`.
