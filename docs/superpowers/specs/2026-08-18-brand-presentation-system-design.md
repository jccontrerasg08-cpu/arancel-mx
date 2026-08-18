# arancel-mx Brand and Presentation System Design

## Goal

Make the public presentation of `arancel-mx` explain the project in seconds without weakening the repository's technical and legal trust boundaries. The brand system must be reusable across GitHub, the public Vercel hub, documentation, social previews, and presentations.

## Baseline

This design targets `main` at `fb727ac87e451e3835afad315af29925452e7fc8`, after PR #132 (`feat: centralize verified data hub on Vercel`). The current Vercel surface now combines:

- a Spanish-first public hub served from `website/`;
- Vercel-contained operational metadata/search backed by Neon;
- same-domain proxy routes for the reusable FastAPI API;
- certified public release assets as the source for operational synchronization.

This design must not revert that architecture or reintroduce the pre-#132 assumption that `/v1/meta` is always served outside Vercel.

## Product story

The concise story is:

> `arancel-mx` converts scattered official Mexican tariff publications into verifiable, reproducible data that developers, analysts, and trade teams can consume through files, DuckDB, Python, CLI, and a read-only HTTP surface.

The README and public site should answer, in this order:

1. What is this?
2. Why does it exist?
3. What can I do with it?
4. Which interface should I use?
5. Why should I trust the output?
6. How is it built and verified?
7. Where are the deeper technical/legal details?

## Scope boundary

This is presentation and documentation work. It may modify brand assets, README information architecture, public-site metadata and brand CSS, focused presentation tests, and the integration handoff documentation.

It must not modify:

- tariff parsing or normalization logic;
- source authority or legal reconciliation rules;
- DuckDB schemas;
- API response contracts;
- Neon synchronization logic;
- GitHub release semantics;
- dependency versions;
- production workflows.

## Brand system

### Palette

- Navy: `#102A43` for trust, data, and primary typography.
- Deep navy: `#071827` for dark surfaces.
- Mexico green: `#008A5B` for action, verification, and code-like brackets.
- Mexico red: `#CE1126` as a restrained customs/trade accent only.
- Off-white: `#F8FAFC` and white for accessible light surfaces.
- Cool gray: `#D8E2EA` for technical supporting detail.

### Visual language

The core mark is a simplified customs/security/document/trade symbol:

- lock/gateway shape for controlled, verified data;
- document for official-source evidence;
- green check for validation;
- restrained green/red side panels for Mexico/customs context.

The horizontal wordmark is framed by green square brackets and uses a green dot before `mx`. SVGs must use only vector primitives and text-independent paths/shapes where practical. No raster image may be embedded inside an SVG.

### Assets

Create or replace:

- `docs/assets/arancel-mx-logo.svg`: horizontal primary logo for README/docs.
- `docs/assets/arancel-mx-banner.svg`: README hero/social-style presentation banner.
- `docs/assets/arancel-mx-social.svg`: 1280×640 repository/social preview composition.
- `docs/assets/arancel-mx-cover.svg`: 1600×900 dark presentation cover.
- `website/assets/arancel-mx-mark.svg`: small-size site/fav icon mark.
- `website/assets/arancel-mx-logo.svg`: horizontal site wordmark.

All assets must include accessible `<title>` and `<desc>` metadata and use fixed `viewBox` dimensions.

## README information architecture

Both `README.md` and `README.en.md` keep all existing technical commitments required by tests, but the top-level order changes to product-first:

1. Brand hero and one-sentence value proposition.
2. Compact badges and language switch.
3. Primary calls to action: website, latest data, install, quickstart, docs.
4. `Por qué existe / Why it exists`.
5. `Elige cómo usarlo / Choose how to use it` with five interfaces:
   - files + DuckDB;
   - CLI;
   - Python;
   - read-only HTTP/API surface;
   - audit/reproduction tools.
6. 60-second quickstart with `pip install arancel-mx`, `arancel-mx data download`, and `arancel-mx lookup 01012101`.
7. Trust model and official-source flow.
8. Detailed capabilities, architecture, data model, source policy, releases, contribution, acknowledgements.

The README must continue to distinguish package versioning from immutable dataset releases (`data-YYYY.MM.DD`) and retain the documented PyPI 0.2.0 publication facts required by current tests.

## Website presentation integration

Do not edit the generated React bundle (`website/assets/index-*.js` or generated CSS). Use the maintained boundary instead:

- `website/index.html` for metadata, favicon/brand asset links, Open Graph and Twitter card metadata;
- `website/assets/site-brand.css` for stable brand styling and logo sizing;
- existing `hub-search.js` / `hub-search.css` remain functionally unchanged.

The website should advertise the current verified hub, not the earlier "separate API only" architecture.

## Storytelling and tool flow

The primary user paths are:

| Intent | Recommended surface | Why |
|---|---|---|
| Download a verified dataset | GitHub release assets / DuckDB | immutable, portable, auditable |
| Inspect a code quickly | CLI | fastest local workflow |
| Integrate into Python | `Dataset` API | typed/reusable application integration |
| Build a service or UI | read-only HTTP surface | stable service boundary |
| Verify provenance/reproducibility | manifest, SHA256, source capture, `provenance`, `data verify` | trust and audit workflow |

Commands should be grouped by workflow instead of presented as one undifferentiated list.

## Trust narrative

The user should be able to see that the project does not ask them to trust a README claim. The core trust chain is:

`official sources → capture → source identity + SHA256 → legal reconciliation → parse → normalize → validate → canonical DuckDB → immutable release`

The README must preserve the fail-closed principle, the distinction between legal/current-source evidence and convenience/discovery sources, and the warning that the project does not constitute legal advice.

## Tests and verification

Add focused presentation contracts before implementation:

- required brand assets exist and are valid SVG text;
- no brand SVG embeds raster/base64 images;
- README hero references the new banner/logo and retains existing package/data quickstart contracts;
- Spanish and English README contain the same five interface categories;
- website metadata includes Open Graph/social image references and keeps current hub assets and `/v1` architecture untouched;
- `vercel.json` remains byte-for-byte unchanged by this work.

Run at minimum:

- `pytest -q tests/test_brand_presentation.py tests/test_public_site.py tests/package/test_readme_metadata.py`
- `ARANCEL_MX_SKIP_URL_CHECKS=1 pytest -q tests/test_documented_urls.py`
- `python -m ruff check tests/test_brand_presentation.py`
- XML parse all new SVG assets.
- `git diff --check` equivalent through final patch inspection.

Full CI remains the merge gate.

## Merge safety

Work stays on `docs/brand-storytelling`. Do not edit PR #124 or #125. Before merge, update the branch if `main` moves and re-run the focused presentation/public-site contracts. Merge only by the repository's allowed squash method after required checks are green.