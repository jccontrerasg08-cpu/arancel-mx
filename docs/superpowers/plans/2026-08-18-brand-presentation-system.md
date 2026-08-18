# arancel-mx Brand and Presentation System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Introduce a coherent vector brand system and product-first README/public-site presentation without changing tariff, API, operational, release, dependency, or workflow behavior.

**Architecture:** Keep all product behavior untouched and work only at the presentation boundary: vector assets under `docs/assets/` and `website/assets/`, bilingual README structure, website metadata/brand CSS, focused contracts, and the integration handoff. The current #132 Vercel hub and proxy/operational architecture is treated as immutable behavior for this change.

**Tech Stack:** SVG, Markdown, HTML metadata, CSS, Python/pytest contracts.

**Spec:** `docs/superpowers/specs/2026-08-18-brand-presentation-system-design.md`

## Global Constraints

- Baseline is `fb727ac87e451e3835afad315af29925452e7fc8`.
- Do not modify `vercel.json`, `pyproject.toml`, `requirements*`, `.github/workflows/*`, `api/*`, `src/arancel_mx/operational/*`, or tariff/source/release behavior.
- Do not edit generated `website/assets/index-*.js` or `website/assets/index-*.css`.
- Do not embed PNG/JPEG/base64 raster payloads inside SVG assets.
- Preserve required README strings: `pip install arancel-mx`, `arancel-mx data download`, `arancel-mx lookup 01012101`, package-vs-dataset explanation, `data-YYYY.MM.DD`, and published `0.2.0` status.
- Preserve current #132 hub search assets and same-domain `/v1` routing architecture.
- Work only on `docs/brand-storytelling`; do not touch Dependabot PR #124 or #125.

---

### Task 1: Add presentation contracts first

**Files:**
- Create: `tests/test_brand_presentation.py`
- Read-only dependency: `tests/test_public_site.py`
- Read-only dependency: `tests/package/test_readme_metadata.py`

**Interfaces:**
- Consumes: repository files as text and XML.
- Produces: regression contracts for brand assets, README flow, website metadata, and no-raster SVG policy.

- [ ] **Step 1: Write the failing tests**

Add tests that require:

```python
BRAND_ASSETS = (
    "docs/assets/arancel-mx-logo.svg",
    "docs/assets/arancel-mx-banner.svg",
    "docs/assets/arancel-mx-social.svg",
    "docs/assets/arancel-mx-cover.svg",
    "website/assets/arancel-mx-mark.svg",
    "website/assets/arancel-mx-logo.svg",
)
```

For each asset, parse with `xml.etree.ElementTree`, assert the root tag ends in `svg`, require `<title>` and `<desc>`, and reject `data:image`, `base64,`, `.png`, `.jpg`, and `.jpeg` references.

Require both READMEs to contain the five intent labels/surfaces and the product-first section headings. Require `website/index.html` to include `og:title`, `og:description`, `og:image`, `twitter:card`, `/assets/arancel-mx-social.svg`, the existing `hub-search.css`, and the existing `hub-search.js`.

- [ ] **Step 2: Verify RED**

Run:

```bash
pytest -q tests/test_brand_presentation.py
```

Expected: FAIL because `arancel-mx-logo.svg`, `arancel-mx-social.svg`, `arancel-mx-cover.svg`, website horizontal logo, and social metadata do not exist yet.

- [ ] **Step 3: Commit only the failing contract**

```bash
git add tests/test_brand_presentation.py
git commit -m "test: define brand presentation contract"
```

### Task 2: Introduce the vector brand assets

**Files:**
- Create: `docs/assets/arancel-mx-logo.svg`
- Modify: `docs/assets/arancel-mx-banner.svg`
- Create: `docs/assets/arancel-mx-social.svg`
- Create: `docs/assets/arancel-mx-cover.svg`
- Modify: `website/assets/arancel-mx-mark.svg`
- Create: `website/assets/arancel-mx-logo.svg`

**Interfaces:**
- Consumes: palette and visual language from the spec.
- Produces: reusable vector assets referenced by README and website metadata.

- [ ] **Step 1: Implement minimal vector assets**

Use fixed `viewBox` values, accessible title/description metadata, vector shapes only, and the palette from the spec. Keep the mark simple enough to remain legible at 24 px.

- [ ] **Step 2: Run SVG/brand contracts**

```bash
pytest -q tests/test_brand_presentation.py -k svg
```

Expected: PASS for asset existence/XML/no-raster checks; README/metadata tests may still fail.

- [ ] **Step 3: Commit the asset layer**

```bash
git add docs/assets/arancel-mx-*.svg website/assets/arancel-mx-*.svg
git commit -m "docs: add arancel-mx vector brand system"
```

### Task 3: Reframe the bilingual README story without dropping technical contracts

**Files:**
- Modify: `README.md`
- Modify: `README.en.md`

**Interfaces:**
- Consumes: brand assets and existing detailed technical sections.
- Produces: product-first bilingual onboarding while preserving required downstream/package contracts.

- [ ] **Step 1: Restructure only the top and navigation flow**

Add the new hero, concise value proposition, five-surface chooser, why-it-exists story, 60-second quickstart, and trust-chain overview before deep architecture. Retain existing detailed sections and all required package/release facts.

Spanish chooser categories:

```text
Datos / DuckDB
CLI
Python
HTTP / API read-only
Auditoría y reproducción
```

English chooser categories:

```text
Data / DuckDB
CLI
Python
Read-only HTTP / API
Audit and reproduction
```

- [ ] **Step 2: Run README contracts**

```bash
pytest -q tests/test_brand_presentation.py tests/package/test_readme_metadata.py
```

Expected: PASS.

- [ ] **Step 3: Run documented-URL contracts offline**

```bash
ARANCEL_MX_SKIP_URL_CHECKS=1 pytest -q tests/test_documented_urls.py
```

Expected: PASS.

- [ ] **Step 4: Commit README presentation**

```bash
git add README.md README.en.md
git commit -m "docs: tell the arancel-mx product story"
```

### Task 4: Integrate brand metadata into the current Vercel hub boundary

**Files:**
- Modify: `website/index.html`
- Modify: `website/assets/site-brand.css`
- Do not modify: `website/assets/hub-search.js`
- Do not modify: `website/assets/hub-search.css`
- Do not modify: `vercel.json`

**Interfaces:**
- Consumes: site SVG assets.
- Produces: metadata and stable visual identity without touching hub behavior.

- [ ] **Step 1: Add social/accessibility metadata**

Add Open Graph/Twitter metadata and reference `/assets/arancel-mx-social.svg`. Keep all existing hub scripts/styles and generated bundle references unchanged.

- [ ] **Step 2: Update maintained brand CSS only**

Use `website/assets/arancel-mx-logo.svg` where the stable DOM permits it; keep the compact mark for small nav/favicon surfaces. Avoid selectors tied to minified class names.

- [ ] **Step 3: Run public-site contracts**

```bash
pytest -q tests/test_brand_presentation.py tests/test_public_site.py
```

Expected: PASS.

- [ ] **Step 4: Confirm protected files are unchanged**

```bash
git diff fb727ac -- vercel.json pyproject.toml requirements.txt requirements/ .github/workflows api src/arancel_mx/operational
```

Expected: no diff.

- [ ] **Step 5: Commit website presentation**

```bash
git add website/index.html website/assets/site-brand.css
git commit -m "docs: align public hub branding and social metadata"
```

### Task 5: Refresh the integration handoff for post-#132 reality

**Files:**
- Modify: `docs/integration-handoff.md`
- Modify: `docs/README.md` only if needed to expose the brand/story docs.

**Interfaces:**
- Consumes: #132 architecture.
- Produces: current coordination guidance so later agents do not restore stale site/API assumptions.

- [ ] **Step 1: Update only stale architecture language**

Document that Vercel now owns operational metadata/search and same-domain proxy routes while the reusable FastAPI service remains a separate runtime behind selected proxy paths. Preserve package, release, CI, and dependency ordering guidance.

- [ ] **Step 2: Run documentation-focused tests**

```bash
pytest -q tests/test_brand_presentation.py tests/test_public_site.py tests/package/test_readme_metadata.py
```

Expected: PASS.

- [ ] **Step 3: Commit handoff update**

```bash
git add docs/integration-handoff.md docs/README.md
git commit -m "docs: refresh presentation integration handoff"
```

### Task 6: Final verification and PR

**Files:**
- Review all branch changes.

**Interfaces:**
- Produces: a reviewable presentation-only PR.

- [ ] **Step 1: Re-check current `main`**

If `main` moved after `fb727ac`, compare and update the branch before final verification. Resolve overlap only in presentation files.

- [ ] **Step 2: Run focused verification**

```bash
pytest -q tests/test_brand_presentation.py tests/test_public_site.py tests/package/test_readme_metadata.py
ARANCEL_MX_SKIP_URL_CHECKS=1 pytest -q tests/test_documented_urls.py
python -m ruff check tests/test_brand_presentation.py
```

Expected: 0 failures.

- [ ] **Step 3: Verify protected scopes**

Confirm no branch diff in:

```text
vercel.json
pyproject.toml
requirements.txt
requirements/
.github/workflows/
api/
src/arancel_mx/operational/
```

- [ ] **Step 4: Inspect final diff for whitespace and accidental generated-bundle edits**

Reject any change to `website/assets/index-*.js` or `website/assets/index-*.css`.

- [ ] **Step 5: Open a draft PR first**

Title:

```text
docs: unify arancel-mx brand and product story
```

The PR body must state the exact baseline, changed scopes, protected scopes, focused verification, and that Dependabot #124/#125 were left untouched.

- [ ] **Step 6: Wait for CI before merge**

Do not merge from this task. Required checks and Vercel preview are the final integration gate.