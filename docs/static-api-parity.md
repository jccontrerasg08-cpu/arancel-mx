# Static API parity

Three readers must return the same lookup, hierarchy, and search behavior for one verified release:

| Reader | Location |
|---|---|
| Python `Dataset` | [src/arancel_mx/consumer/query.py](../src/arancel_mx/consumer/query.py) |
| Python static client | [src/arancel_mx/static_api.py](../src/arancel_mx/static_api.py) |
| Browser client | [frontend/src/static-api.js](../frontend/src/static-api.js) |

`tests/test_static_api.py` (`test_browser_client_matches_python_reference`) fails when the browser client drifts from the Python reference.

## Rules that have to stay identical

- Accepted code lengths are 2, 4, 6, 8, and 10 digits. Dots, spaces, and hyphens are removed. Any other character is rejected.
- Display formatting is `8517.13.01` for 8 digits and `8517.13.01 00` for 10 digits.
- Search text is Unicode-normalized (NFKD), casefolded by stripping marks, and lowercased. `ß` becomes `ss`.
- `SCORER_VERSION` is `"1"` in both the Python query module and the browser client. A scoring change bumps both.
- Chapter files are `records/{hs2}.json`. One file per chapter is the size trade-off. Do not emit one file per code.
- The browser cache is a page-lifetime `Map`. A new release is visible after reload. That matches immutable releases; it is not a live subscription.

## What the static API is not

It does not apply preferential rates, invent NICO codes, or classify goods. `suggest` stays retrieve-only and carries the same disclaimer in both clients.
