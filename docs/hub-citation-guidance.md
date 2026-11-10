# Hub citation and release-tag guidance

The hub at [arancel-mx.vercel.app](https://arancel-mx.vercel.app/) is a projection of one immutable GitHub Release. Cite that release, not “the website today”.

## What identifies the dataset

`GET /data/v1/meta.json` is the machine-readable identity. The fields to record are:

| Field | Use in a citation |
|---|---|
| `dataset_tag` | Release name, shaped `data-YYYY.MM.DD` |
| `dataset_version` | Same calendar version without the `data-` prefix |
| `schema_version` | Manifest schema. Current public releases use `"2"` |
| `release_verified` | Must be `true` before the result is cited as a verified release |
| `package_version` | Python package that exported the files. It does not pin the data |

Example citation:

```text
arancel-mx dataset data-2026.11.09
schema 2, release_verified true
https://github.com/jccontrerasg08-cpu/arancel-mx/releases/tag/data-2026.11.09
SHA-256 of the consumed asset, from that release's SHA256SUMS
code consulted, and the consultation date
```

Fetch the identity before copying a number from the page:

```bash
curl -fsS "https://arancel-mx.vercel.app/data/v1/meta.json"
```

If `release_verified` is not `true`, do not describe the result as a verified release.

## Manual copy-citation

1. Read `dataset_tag` from `meta.json` or from the release badge in the hub header or footer.
2. Open `https://github.com/jccontrerasg08-cpu/arancel-mx/releases/tag/<dataset_tag>`.
3. Copy the SHA-256 line for the asset you used (`arancel_mx.duckdb`, `arancel_mx.csv`, or `arancel_mx.json`) from `SHA256SUMS`.
4. Record the code and the consultation date next to that tag.

There is no one-click “Copy citation” control yet. The steps above are deterministic. A future control should assemble only these fields and must not invent a SHA-256.

## Mobile

The header collapses into a menu on narrow screens. The release badge and the search box stay reachable. A fraction code and its IGI/IGE summary are meant to be readable without horizontal scrolling. Prefer the static JSON for anything you will archive; the page layout is not the citation.

## What not to cite as the tariff

- A search suggestion. `suggest` is retrieve-only and says so.
- A VUCEM comparison. `compare` is informational and is not the legal identity.
- A preferential rate, PROSEC rate, or RRNA that the core dataset does not publish.
