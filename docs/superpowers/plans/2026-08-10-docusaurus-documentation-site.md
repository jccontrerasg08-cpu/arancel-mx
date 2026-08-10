# Docusaurus Documentation Site Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish a bilingual static documentation site for `arancel-mx` on GitHub Pages without coupling Node.js or Docusaurus to the tariff ETL/runtime and without creating a second manually maintained source of truth for technical documentation.

**Architecture:** Keep the Python/data project at repository root and add an isolated `website/` Docusaurus project. Canonical Spanish product documentation remains under root `docs/`; Docusaurus consumes that directory directly, excludes maintainer/internal material, and stores English translations only through native Docusaurus i18n. A read-only docs CI validates TypeScript and both locales, while a separate least-privilege Pages workflow deploys only static output from protected `main`.

**Tech Stack:** Docusaurus 3.10.2 planning baseline, Node.js >=20, TypeScript >=5.1, npm lockfile + `npm ci`, React/classic preset versions validated from a temporary official Docusaurus scaffold at implementation time, GitHub Actions, GitHub Pages, Docusaurus native i18n.

## Global Constraints

- Immediately before the first implementation PR, re-verify the stable Docusaurus release from the official versions/installation pages. During plan self-review on 2026-08-10, the official stable release is `3.10.2` and the documented Node.js floor is `>=20.0`.
- Re-verify TypeScript support from the official Docusaurus TypeScript page. During plan self-review, the documented TypeScript floor is `>=5.1` and the required support packages are `typescript`, `@docusaurus/module-type-aliases`, `@docusaurus/tsconfig`, and `@docusaurus/types`.
- All `@docusaurus/*` packages in the site use the same exact Docusaurus version.
- Before committing `website/package.json`, create a disposable official TypeScript scaffold with the verified Docusaurus version and use its compatible React/MDX/theme dependency versions as evidence. Do not commit the disposable scaffold.
- Commit `website/package-lock.json`; CI uses `npm ci`, never floating installs.
- Do not run Node.js tooling inside `.github/workflows/official-data-pipeline.yml`.
- Do not move Python package files, source capture/parsers, release code, source registry, or generated datasets into `website/`.
- Default locale is Spanish `es`; secondary locale is English `en`.
- The project-page URL is `https://jccontrerasg08-cpu.github.io/arancel-mx/` unless repository Pages settings are deliberately changed and documented later.
- Root `README.md` and `README.en.md` remain concise repository entrypoints with installation, quick CLI usage, legal disclaimer, architecture summary, releases, and documentation links.
- Internal `docs/superpowers/**` and maintainer-only `docs/operations/**` are excluded from public Docusaurus input.
- Public Spanish documentation has one canonical root file per topic. English translations live only under `website/i18n/en/docusaurus-plugin-content-docs/current/`.
- Pages deploy receives only `contents: read`, `pages: write`, and `id-token: write`. Pull-request docs CI receives `contents: read` only.
- All committed GitHub Actions references use full commit SHAs resolved from official action repositories immediately before the corresponding PR.
- Every implementation PR uses the approved double-check gate from `2026-08-10-production-certification-rollout-index.md`.

---

## Canonical public documentation set

The public sidebar contains exactly these Spanish source files:

```text
docs/getting-started.md
docs/cli.md
docs/python-api.md
docs/dataset.md
docs/hs-mx-nico.md
docs/data-model.md
docs/sources.md
docs/provenance.md
docs/release-process.md
docs/reproducibility.md
docs/verify-release.md
docs/production-certification.md
```

The corresponding English translation files are exactly:

```text
website/i18n/en/docusaurus-plugin-content-docs/current/getting-started.md
website/i18n/en/docusaurus-plugin-content-docs/current/cli.md
website/i18n/en/docusaurus-plugin-content-docs/current/python-api.md
website/i18n/en/docusaurus-plugin-content-docs/current/dataset.md
website/i18n/en/docusaurus-plugin-content-docs/current/hs-mx-nico.md
website/i18n/en/docusaurus-plugin-content-docs/current/data-model.md
website/i18n/en/docusaurus-plugin-content-docs/current/sources.md
website/i18n/en/docusaurus-plugin-content-docs/current/provenance.md
website/i18n/en/docusaurus-plugin-content-docs/current/release-process.md
website/i18n/en/docusaurus-plugin-content-docs/current/reproducibility.md
website/i18n/en/docusaurus-plugin-content-docs/current/verify-release.md
website/i18n/en/docusaurus-plugin-content-docs/current/production-certification.md
```

`CONTRIBUTING.md` remains at repository root and is linked from the navbar/footer rather than duplicated as a Docusaurus doc. `docs/arancel-mx.md` remains available for repository-specific historical/contextual content but is not part of the public sidebar unless a later reviewed PR gives it a distinct non-duplicative role.

## Planned file structure

```text
website/
├── package.json
├── package-lock.json
├── tsconfig.json
├── docusaurus.config.ts
├── sidebars.ts
├── src/
│   ├── css/custom.css
│   └── pages/index.tsx
├── static/
│   └── img/
└── i18n/
    └── en/
        ├── code.json
        ├── docusaurus-theme-classic/
        │   ├── navbar.json
        │   └── footer.json
        └── docusaurus-plugin-content-docs/
            └── current/
                ├── getting-started.md
                ├── cli.md
                ├── python-api.md
                ├── dataset.md
                ├── hs-mx-nico.md
                ├── data-model.md
                ├── sources.md
                ├── provenance.md
                ├── release-process.md
                ├── reproducibility.md
                ├── verify-release.md
                └── production-certification.md

.github/workflows/
├── docs-ci.yml
└── docs-pages.yml
```

### Task 1: Create the canonical Spanish public docs set

**Files:**
- Create: `docs/getting-started.md`
- Create: `docs/cli.md`
- Create: `docs/python-api.md`
- Create: `docs/dataset.md`
- Create: `docs/hs-mx-nico.md`
- Modify: `docs/data-model.md`
- Modify: `docs/sources.md`
- Create: `docs/provenance.md`
- Modify: `docs/release-process.md`
- Create: `docs/reproducibility.md`
- Create: `docs/verify-release.md`
- Modify: `docs/production-certification.md`
- Modify: `README.md`
- Modify: `README.en.md`
- Create: `tests/test_public_docs_contract.py`

**Interfaces:**
- Consumes: current README, data model, source docs, release process, production certification evidence, implemented CLI/package interfaces.
- Produces: twelve non-overlapping Spanish public docs with stable topic ownership.

- [ ] **Step 1: Write the RED public-doc-set contract test**

```python
from pathlib import Path

PUBLIC_DOCS = {
    "getting-started.md",
    "cli.md",
    "python-api.md",
    "dataset.md",
    "hs-mx-nico.md",
    "data-model.md",
    "sources.md",
    "provenance.md",
    "release-process.md",
    "reproducibility.md",
    "verify-release.md",
    "production-certification.md",
}


def test_canonical_public_docs_exist():
    for name in PUBLIC_DOCS:
        assert (Path("docs") / name).is_file(), name
```

Add assertions that `README.md` links to `docs/getting-started.md` and `README.en.md` links to the future public site without claiming it is live until Pages deployment has succeeded.

- [ ] **Step 2: Confirm RED**

Run: `python -m pytest tests/test_public_docs_contract.py -q`

Expected: FAIL for the new canonical files that do not yet exist.

- [ ] **Step 3: Write topic-owned docs from implemented behavior only**

Use these exact responsibilities:

```text
getting-started.md          installation + first verified local commands
cli.md                      build/check-updates/reconcile/release command contract
python-api.md               currently supported import surface; explicitly 0.x/limited API
dataset.md                  six assets, row levels, how to consume CSV/JSON/DuckDB
hs-mx-nico.md               HS2 -> HS4 -> HS6 -> MX8 -> NICO10 hierarchy
sources.md                  official authorities, roles, source registry behavior
provenance.md               source_document/source_capture/record provenance and legal evidence
release-process.md          automated build/publish/fail-closed lifecycle
reproducibility.md          locks, hashes, deterministic text/logical output semantics
verify-release.md           SHA256SUMS, manifest, attestations/release verification when proven
production-certification.md live certification/runbook evidence
```

Do not present a search API or legal advisory service as implemented. `python-api.md` must state that the public Python API is intentionally limited during 0.x.

- [ ] **Step 4: Reduce README duplication without removing GitHub usability**

Keep install, short CLI example, legal disclaimer, source/release summary, badges, architecture diagram/summary, and links. Move deep explanations to the canonical docs instead of maintaining two full narratives.

- [ ] **Step 5: Verify**

```bash
python -m pytest tests/test_public_docs_contract.py -q
python -m pytest -q
python -m build
git diff --check
```

- [ ] **Step 6: Commit**

```bash
git add docs/getting-started.md docs/cli.md docs/python-api.md docs/dataset.md docs/hs-mx-nico.md docs/data-model.md docs/sources.md docs/provenance.md docs/release-process.md docs/reproducibility.md docs/verify-release.md docs/production-certification.md README.md README.en.md tests/test_public_docs_contract.py
git commit -m "docs: define canonical public documentation"
```

### Task 2: Scaffold pinned Docusaurus with official TypeScript support

**Files:**
- Create: `website/package.json`
- Create: `website/package-lock.json`
- Create: `website/tsconfig.json`
- Create: `website/docusaurus.config.ts`
- Create: `website/sidebars.ts`
- Create: `website/src/css/custom.css`
- Create: `website/src/pages/index.tsx`
- Modify: `.gitignore`
- Create: `tests/test_docs_site_contract.py`

**Interfaces:**
- Produces: `npm run typecheck` and `npm run build` from `website/` with Spanish as default locale.

- [ ] **Step 1: Re-verify upstream and create a disposable reference scaffold**

Run outside the repository or under a temporary ignored path:

```bash
npx create-docusaurus@3.10.2 docusaurus-reference classic --typescript
cd docusaurus-reference
npm ci
npx docusaurus --version
```

If the official stable version is no longer 3.10.2, substitute the newly verified stable version in both commands. Record the generated dependency versions and delete the reference directory after comparison.

- [ ] **Step 2: Create `website/package.json` with the verified dependency set**

Required scripts:

```json
{
  "start": "docusaurus start",
  "build": "docusaurus build",
  "clear": "docusaurus clear",
  "serve": "docusaurus serve",
  "write-translations": "docusaurus write-translations",
  "typecheck": "tsc --noEmit"
}
```

Required Docusaurus packages use the same exact verified version:

```text
@docusaurus/core
@docusaurus/preset-classic
@docusaurus/module-type-aliases
@docusaurus/tsconfig
@docusaurus/types
```

Also include `typescript` at a version meeting the verified Docusaurus floor plus the React/ReactDOM/MDX/Prism/clsx versions from the disposable official scaffold. Do not guess peer dependency versions.

- [ ] **Step 3: Use the official TypeScript base config**

`website/tsconfig.json`:

```json
{
  "extends": "@docusaurus/tsconfig",
  "compilerOptions": {
    "baseUrl": "."
  }
}
```

- [ ] **Step 4: Configure routing, i18n, docs source, and exclusions**

`docusaurus.config.ts` must include:

```ts
url: 'https://jccontrerasg08-cpu.github.io',
baseUrl: '/arancel-mx/',
i18n: {
  defaultLocale: 'es',
  locales: ['es', 'en'],
  localeConfigs: {
    es: {label: 'Español', htmlLang: 'es-MX'},
    en: {label: 'English', htmlLang: 'en-US'},
  },
},
```

Configure preset docs with `path: '../docs'`, explicit sidebar, and excludes for `superpowers/**` and `operations/**`. Disable the blog. The navbar includes Inicio/Home, Docs, Releases, GitHub, Contribuir/Contributing, and locale dropdown.

- [ ] **Step 5: Define explicit sidebar IDs**

`sidebars.ts` lists only:

```text
getting-started
cli
python-api
dataset
hs-mx-nico
data-model
sources
provenance
release-process
reproducibility
verify-release
production-certification
```

Do not use auto-generated sidebars for the root docs tree.

- [ ] **Step 6: Add site-contract tests**

Assert the config contains `../docs`, both exclusion patterns, ES/EN locales, the GitHub Pages base URL, and that `website/docs` does not exist. Assert every public sidebar ID belongs to the exact canonical set from `tests/test_public_docs_contract.py`.

- [ ] **Step 7: Ignore generated output only**

Add:

```text
website/node_modules/
website/build/
website/.docusaurus/
```

Do not ignore `website/package-lock.json` or `website/i18n/`.

- [ ] **Step 8: Generate lockfile and verify**

```bash
cd website
npm install
npm ci
npm run typecheck
npm run build
cd ..
python -m pytest tests/test_docs_site_contract.py -q
git diff --check
```

- [ ] **Step 9: Commit**

```bash
git add website .gitignore tests/test_docs_site_contract.py
git commit -m "docs: scaffold typed Docusaurus site"
```

### Task 3: Add complete English i18n parity

**Files:**
- Create: `website/i18n/en/code.json`
- Create: `website/i18n/en/docusaurus-theme-classic/navbar.json`
- Create: `website/i18n/en/docusaurus-theme-classic/footer.json`
- Create the twelve exact translation files listed in the canonical translation section above.
- Modify: `tests/test_docs_site_contract.py`

**Interfaces:**
- Produces: Spanish default routes and English `/en/` routes from one Docusaurus build.

- [ ] **Step 1: Generate the official translation skeleton**

```bash
cd website
npm ci
npm run write-translations -- --locale en
```

Keep only translation files for enabled site features.

- [ ] **Step 2: Translate navigation/site strings**

Preserve technical identifiers (`LIGIE`, `NICO`, `HS6`, `MX8`, `DuckDB`, `SHA256SUMS`, workflow names) where they are identifiers rather than prose.

- [ ] **Step 3: Translate all twelve public docs**

Translate source-supported content faithfully. Do not add English-only product claims absent from the canonical Spanish source.

- [ ] **Step 4: Add exact parity test**

The test declares the same twelve IDs and asserts every English file exists. It also asserts no English file exists under an `operations` or `superpowers` path.

- [ ] **Step 5: Verify all builds**

```bash
cd website
npm ci
npm run typecheck
npm run build
npm run build -- --locale es
npm run build -- --locale en
cd ..
python -m pytest tests/test_docs_site_contract.py -q
git diff --check
```

- [ ] **Step 6: Commit**

```bash
git add website/i18n tests/test_docs_site_contract.py
git commit -m "docs: add complete English documentation parity"
```

### Task 4: Add read-only documentation CI

**Files:**
- Create: `.github/workflows/docs-ci.yml`
- Modify: `tests/test_docs_site_contract.py`

**Interfaces:**
- Produces: PR/push documentation check with no deployment/write permissions.

- [ ] **Step 1: Resolve official action tags to full SHAs**

Resolve current official tags for `actions/checkout` and `actions/setup-node` immediately before the PR. Record tag -> SHA mappings in the PR double-check evidence.

- [ ] **Step 2: Add RED workflow contract test**

Require:

```text
permissions contents: read
npm ci
npm run typecheck
npm run build
npm run build -- --locale es
npm run build -- --locale en
no pages: write
no id-token: write
no contents: write
```

- [ ] **Step 3: Implement docs CI**

Trigger on `pull_request` and pushes to `main` for:

```text
website/**
docs/**
README.md
README.en.md
.github/workflows/docs-ci.yml
.github/workflows/docs-pages.yml
.github/dependabot.yml
```

Use the Node version supported by the verified Docusaurus stable release; Node 20 satisfies the planning-time 3.10.2 requirement.

- [ ] **Step 4: Verify**

```bash
python -m pytest tests/test_docs_site_contract.py -q
cd website
npm ci
npm run typecheck
npm run build
npm run build -- --locale es
npm run build -- --locale en
cd ..
git diff --check
```

- [ ] **Step 5: Commit**

```bash
git add .github/workflows/docs-ci.yml tests/test_docs_site_contract.py
git commit -m "ci: validate bilingual Docusaurus docs"
```

### Task 5: Add least-privilege GitHub Pages deployment

**Files:**
- Create: `.github/workflows/docs-pages.yml`
- Modify: `tests/test_docs_site_contract.py`

**Interfaces:**
- Produces: deployment of `website/build/` to `github-pages` from protected `main`.

- [ ] **Step 1: Confirm Pages repository setting**

Set Settings -> Pages -> Source to GitHub Actions. Do not create a `gh-pages` branch.

- [ ] **Step 2: Resolve official Pages action tags to full SHAs**

Resolve current official tags for:

```text
actions/checkout
actions/setup-node
actions/configure-pages
actions/upload-pages-artifact
actions/deploy-pages
```

Record every mapping in the PR body. GitHub's current official Pages docs require `pages: write` and `id-token: write` for deploy.

- [ ] **Step 3: Add RED Pages workflow contract test**

Assert build and deploy are separate jobs, deploy uses `needs: build`, environment name `github-pages`, and exactly these deploy permissions:

```yaml
contents: read
pages: write
id-token: write
```

Assert there is no `contents: write`, `issues: write`, schedule trigger, release script, or production data pipeline invocation.

- [ ] **Step 4: Implement Pages workflow**

Trigger on pushes to `main` affecting website/public docs/READMEs plus `workflow_dispatch`. Build runs `npm ci`, `npm run typecheck`, `npm run build`, then uploads `website/build/`. Deploy uses `actions/deploy-pages` and outputs its page URL.

- [ ] **Step 5: Verify locally/static contract**

```bash
python -m pytest tests/test_docs_site_contract.py -q
cd website
npm ci
npm run typecheck
npm run build
cd ..
git diff --check
```

- [ ] **Step 6: Commit**

```bash
git add .github/workflows/docs-pages.yml tests/test_docs_site_contract.py
git commit -m "ci: deploy documentation to GitHub Pages"
```

### Task 6: Add npm Dependabot and contributor docs workflow

**Files:**
- Modify: `.github/dependabot.yml`
- Modify: `CONTRIBUTING.md`
- Create: `docs/documentation-site.md`
- Modify: `README.md`
- Modify: `README.en.md`
- Modify: `tests/test_docs_site_contract.py`

**Interfaces:**
- Produces: maintained npm dependencies and contributor instructions for the docs site.

- [ ] **Step 1: Extend Dependabot without removing current ecosystems**

Add exactly:

```yaml
- package-ecosystem: "npm"
  directory: "/website"
  schedule:
    interval: weekly
    day: monday
  labels:
    - dependencies
    - documentation
  open-pull-requests-limit: 5
```

Keep the existing pip and GitHub Actions entries unchanged.

- [ ] **Step 2: Document local docs workflow**

`docs/documentation-site.md` documents:

```bash
cd website
npm ci
npm run typecheck
npm run start
npm run build
npm run build -- --locale es
npm run build -- --locale en
```

It also states root `docs/` is canonical Spanish product content, English translations use native i18n, `docs/superpowers/` and `docs/operations/` are excluded, and generated `website/build/` is never committed.

- [ ] **Step 3: Add public site links only after successful Pages deployment**

Once the Pages URL is proven live, link `https://jccontrerasg08-cpu.github.io/arancel-mx/` from both READMEs and CONTRIBUTING. Until then, keep repository-local docs links so no dead public URL is presented as operational.

- [ ] **Step 4: Extend static tests**

Require the npm Dependabot entry, docs workflow commands, and after Pages has succeeded, the exact public site URL in both READMEs.

- [ ] **Step 5: Verify**

```bash
python -m pytest -q
python -m build
cd website
npm ci
npm run typecheck
npm run build
npm run build -- --locale es
npm run build -- --locale en
cd ..
git diff --check
```

- [ ] **Step 6: Commit**

```bash
git add .github/dependabot.yml CONTRIBUTING.md docs/documentation-site.md README.md README.en.md tests/test_docs_site_contract.py
git commit -m "docs: maintain public documentation workflow"
```

### Task 7: Certify the live Pages deployment and production isolation

**Files:**
- No code changes unless the live deployment exposes a reproducible configuration error.
- Update: `docs/documentation-site.md` only if actual verified deployment behavior requires a correction.

**Interfaces:**
- Produces: live ES/EN docs and evidence that docs workflows cannot mutate production data releases.

- [ ] **Step 1: Double-check before Pages merge**

Require current main CI green, Production Certification completed, Docusaurus/Node/TypeScript versions re-verified, official action SHAs recorded, Pages source set to GitHub Actions, no internal docs in `website/build`, and no data-release permissions in docs workflows.

- [ ] **Step 2: Merge through protected main using squash**

Do not bypass required `test` or docs CI.

- [ ] **Step 3: Verify Pages build/deploy**

Require both jobs success and a deployment URL under `https://jccontrerasg08-cpu.github.io/arancel-mx/`.

- [ ] **Step 4: Smoke-test public routes**

Verify successful HTTP responses/content for:

```text
https://jccontrerasg08-cpu.github.io/arancel-mx/
https://jccontrerasg08-cpu.github.io/arancel-mx/docs/getting-started
https://jccontrerasg08-cpu.github.io/arancel-mx/en/
https://jccontrerasg08-cpu.github.io/arancel-mx/en/docs/getting-started
```

Verify no public route or generated file exposes `superpowers` or `operations` content.

- [ ] **Step 5: Verify production isolation**

Compare releases/tags/issues before and after docs deploy. Require no new `data-*` release/tag and no production `[DATA ALERT]` issue caused by docs workflows.

- [ ] **Step 6: Final repository verification**

```bash
python -m pytest -q
python -m build
cd website
npm ci
npm run typecheck
npm run build
cd ..
git diff --check
```

The Docusaurus subproject is complete only after both locales are live and production-isolation checks pass.
