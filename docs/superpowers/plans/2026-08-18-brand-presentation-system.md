# arancel-mx Brand and Presentation System Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Introduce a coherent vector brand system and product-first README/public-site presentation without changing tariff, API, operational, release, dependency, workflow, routing, or generated-site behavior.

**Architecture:** Keep all product behavior untouched and work only at the maintained presentation boundary: vector assets under `docs/assets/` and `website/assets/`, bilingual README structure, stable `site-brand.css`, focused contracts, and the integration handoff. The current #132 Vercel/Neon/proxy architecture is immutable behavior for this change. `website/index.html` is treated as generated output and is not hand-edited.

**Tech Stack:** SVG, Markdown, CSS, Python/pytest contracts.

**Spec:** `docs/superpowers/specs/2026-08-18-brand-presentation-system-design.md`

## Global Constraints

- Baseline is `fb727ac87e451e3835afad315af29925452e7fc8`.
- Do not modify `vercel.json`, `pyproject.toml`, `requirements*`, `.github/workflows/*`, `api/*`, `src/arancel_mx/operational/*`, or tariff/source/release behavior.
- Do not edit `website/index.html` by hand.
- Do not edit generated `website/assets/index-*.js` or `website/assets/index-*.css`.
- Do not embed PNG/JPEG/base64 raster payloads inside SVG assets.
- Preserve required README strings: `pip install arancel-mx`, `arancel-mx data download`, `arancel-mx lookup 01012101`, package-vs-dataset explanation, `data-YYYY.MM.DD`, and published `0.2.0` status.
- Reflect the #132 weekly Monday schedule and Vercel operational/proxy architecture accurately.
- Preserve current #132 hub search assets and same-domain `/v1` routing architecture.
- Work only on `docs/brand-storytelling`; do not touch Dependabot PR #124 or #125.

---

### Task 1: Add presentation contracts first

**Files:**
- Create: `tests/test_brand_presentation.py`
- Read-only dependency: `tests/test_public_site.py`
- Read-only dependency: `tests/package/test_readme_metadata.py`
- Read-only dependency: `tests/test_public_distribution.py`

**Interfaces:**
- Consumes: repository files as text and trusted version-controlled SVG XML.
- Produces: regression contracts for brand assets, README flow, stable site assets, and no-raster SVG policy.

- [ ] **Step 1: Write the failing tests**

Require these assets:

```python
BRAND_ASSETS = (
    "docs/assets/arancel-mx-logo.svg",
    "docs/assets/arancel-mx-banner.svg",
    "docs/assets/arancel-mx-social.svg",
    "docs/assets/arancel-mx-cover.svg",
    "website/assets/arancel-mx-mark.svg",
    "website/assets/arancel-mx-logo.svg",
    "website/assets/arancel-mx-social.svg",
)
```

For each asset, parse the trusted repository XML, assert the root tag ends in `svg`, require `<title>`, `<desc>`, and `viewBox`, and reject `data:image`, `base64,`, `.png`, `.jpg`, and `.jpeg` references.

Require both READMEs to contain the five intent labels/surfaces and product-first headings. Require the existing public-site hub assets to remain referenced and require `site-brand.css` to expose both mark and horizontal logo without depending on generated bundle class names.

- [ ] **Step 2: Verify RED**

Run:

```bash
pytest -q tests/test_brand_presentation.py
```

Expected: FAIL because the new vector assets and product-story contracts are not present yet.

- [ ] **Step 3: Commit the failing contract**

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
- Create: `website/assets/arancel-mx-social.svg`

**Interfaces:**
- Consumes: palette and visual language from the spec.
- Produces: reusable vector assets for README/docs/site/presentation use.

- [ ] **Step 1: Implement vector-only assets**

Use fixed `viewBox` values, accessible title/description metadata, vector shapes/text only, and the palette from the spec. Keep the compact mark legible at favicon/nav sizes.

- [ ] **Step 2: Run asset contracts**

```bash
pytest -q tests/test_brand_presentation.py -k brand_assets
```

Expected: PASS for asset existence/XML/accessibility/no-raster checks.

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
- Produces: product-first bilingual onboarding while preserving downstream/package/release/source contracts.

- [ ] **Step 1: Add the product-first information architecture**

Lead with:

```text
value proposition
→ why it exists
→ choose a surface
→ 60-second quickstart
→ trust chain
→ deep technical documentation
```

Spanish chooser categories:

```text
Datos / DuckDB
CLI
Python
HTTP / API
Auditoría y reproducción
```

English chooser categories:

```text
Data / DuckDB
CLI
Python
HTTP / API
Audit and reproduction
```

Keep legal disclaimers, official-source URLs, package/release version distinction, maintenance commands, governance links, image references, and source/provenance language already protected by repository tests.

- [ ] **Step 2: Synchronize post-#132 facts**

Document the current weekly `17 11 * * 1` schedule and preserve the former daily `17 11 * * *` only as migration context where legacy documentation contracts still require it. Document Vercel `/v1/meta` and `/v1/search` as operational projections, with remaining public routes proxied to the reusable FastAPI runtime. Keep the verified release as source of truth.

- [ ] **Step 3: Run README/documentation contracts**

```bash
pytest -q \
  tests/test_brand_presentation.py \
  tests/package/test_readme_metadata.py \
  tests/test_public_distribution.py \
  tests/test_autonomous_documentation.py \
  tests/api/test_public_api_docs_contract.py \
  tests/consumer/test_docs_contract.py \
  tests/test_repository_settings_docs.py
```

Expected: PASS.

- [ ] **Step 4: Run documented-URL contracts**

```bash
ARANCEL_MX_SKIP_URL_CHECKS=1 pytest -q tests/test_documented_urls.py
```

Expected: PASS offline; full CI will also exercise the configured live official-URL check.

- [ ] **Step 5: Commit README presentation**

```bash
git add README.md README.en.md
git commit -m "docs: tell the arancel-mx product story"
```

### Task 4: Integrate the brand only through stable website assets

**Files:**
- Modify: `website/assets/site-brand.css`
- Do not modify: `website/index.html`
- Do not modify: `website/assets/hub-search.js`
- Do not modify: `website/assets/hub-search.css`
- Do not modify: `website/assets/index-*.js`
- Do not modify: `website/assets/index-*.css`
- Do not modify: `vercel.json`

**Interfaces:**
- Consumes: deployable mark/logo/social SVG assets from Task 2.
- Produces: stable brand tokens without changing hub layout, routing, search, runtime, or generated output.

- [ ] **Step 1: Update maintained brand CSS only**

Expose stable variables for the mark, horizontal logo, and palette. Keep the existing compact mark insertion for known stable home-link selectors. Do not select minified/generated class names and do not inject a second wordmark into the generated DOM.

- [ ] **Step 2: Preserve generated-site ownership**

Do not inject Open Graph/Twitter tags by manually patching `website/index.html`. The 1280×640 deployable SVG is source material for the future reproducible build/regeneration path that owns the generated document.

- [ ] **Step 3: Run public-site contracts**

```bash
pytest -q tests/test_brand_presentation.py tests/test_public_site.py
```

Expected: PASS.

- [ ] **Step 4: Confirm protected scopes are unchanged**

```bash
git diff fb727ac -- \
  vercel.json pyproject.toml requirements.txt requirements/ \
  .github/workflows api src/arancel_mx/operational \
  website/index.html
```

Expected: no diff.

- [ ] **Step 5: Commit website brand compatibility layer**

```bash
git add website/assets/site-brand.css website/assets/arancel-mx-*.svg
git commit -m "docs: align stable public hub branding"
```

### Task 5: Refresh the integration handoff for post-#132 reality

**Files:**
- Modify: `docs/integration-handoff.md`

**Interfaces:**
- Consumes: #132 architecture.
- Produces: current coordination guidance so later agents do not restore stale site/API assumptions or hand-edit generated site output.

- [ ] **Step 1: Update stale architecture language**

Document that Vercel owns operational metadata/search and same-domain proxy routing while the reusable FastAPI service remains a separate runtime behind selected proxy paths. Document the verified release as source of truth and the generated-site asset boundary.

- [ ] **Step 2: Run documentation-focused tests**

```bash
pytest -q tests/test_brand_presentation.py tests/test_public_site.py tests/package/test_readme_metadata.py
```

Expected: PASS.

- [ ] **Step 3: Commit handoff update**

```bash
git add docs/integration-handoff.md
git commit -m "docs: refresh presentation integration handoff"
```

### Task 6: Final verification and draft PR

**Files:**
- Review all branch changes.

**Interfaces:**
- Produces: a reviewable presentation-only PR with external CI/preview evidence.

- [ ] **Step 1: Re-check current `main`**

Use a branch comparison immediately before completion. If `main` moved after `fb727ac`, update/review the branch before claiming it is current.

- [ ] **Step 2: Run or observe full CI**

Required evidence includes:

```text
Ruff
mypy
full pytest suite
documented official URL check
python build
DuckDB compatibility
built-distribution smoke test
tracked-file cleanliness
browser smoke
FastAPI Cloud runtime smoke
```

- [ ] **Step 3: Verify protected scopes**

Confirm the final PR contains no diff in:

```text
vercel.json
pyproject.toml
requirements.txt
requirements/
.github/workflows/
api/
src/arancel_mx/operational/
website/index.html
website/assets/index-*.js
website/assets/index-*.css
```

- [ ] **Step 4: Inspect final diff**

Confirm every changed file belongs to README/docs/tests/brand assets/stable brand CSS and that no generated binary or credential-like content entered the PR.

- [ ] **Step 5: Keep the PR draft until gates are green**

Title:

```text
docs: unify arancel-mx brand and product story
```

The PR body must state the exact baseline, changed scopes, protected scopes, verification evidence, and that Dependabot #124/#125 were left untouched.

- [ ] **Step 6: Do not merge from this plan**

Full CI, Vercel preview, current-main comparison, and final human review are required before ready/merge.