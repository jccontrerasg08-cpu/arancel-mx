# Hub citation and release-tag guidance

The web hub at [arancel-mx.vercel.app](https://arancel-mx.vercel.app/) displays the current verified release tag (for example `2026.11.09`).

## Recommended citation

When you use a result from the hub or from the static API, cite:

1. The exact dataset tag (`data-YYYY.MM.DD`)
2. The release URL
3. The SHA-256 of the asset you actually consumed (from `SHA256SUMS`)

```text
arancel-mx dataset data-2026.11.09
https://github.com/jccontrerasg08-cpu/arancel-mx/releases/tag/data-2026.11.09
```

## Copy-citation pattern (manual)

On a record page the hub shows the release badge. A practical workflow is:

1. Note the release tag visible in the header or footer.
2. Open the corresponding GitHub Release.
3. Copy the SHA-256 of `arancel_mx.duckdb` (or CSV/JSON) from `SHA256SUMS`.
4. Record the code you looked up and the date of consultation.

Future hub improvements can add a one-click “Copy citation” button that assembles this string. Until then the pattern above is deterministic and sufficient for audit trails.

## Mobile notes

The hub is responsive. On narrow screens the navigation collapses into a menu; the search box and release badge remain accessible. Hierarchy breadcrumbs and the record summary stay readable without horizontal scrolling for typical fraction codes.
