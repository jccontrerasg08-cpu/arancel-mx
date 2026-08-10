# Docusaurus Documentation Site Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Publish a bilingual static documentation site for `arancel-mx` on GitHub Pages without coupling Node.js or Docusaurus to the tariff ETL/runtime and without creating a second manually maintained source of truth for technical documentation.

**Architecture:** Keep the Python/data project at repository root and add an isolated `website/` Docusaurus project. Docusaurus consumes root technical docs through the docs plugin, excludes internal `docs/superpowers/**`, stores English translations through native i18n, and deploys only the generated static site through a dedicated least-privilege GitHub Pages workflow.

**Tech Stack:** Docusaurus 3.10.2 as verified from official docs during planning, Node.js >=20, npm lockfile + `npm ci`, TypeScript Docusaurus config/components, GitHub Actions, GitHub Pages, Docusaurus native i18n.

## Global Constraints

- Re-verify the current stable Docusaurus version from `https://docusaurus.io/docs/installation` immediately before the implementation PR; during planning the stable version is `3.10.2` and the documented requirement is Node.js `20.0` or above.
- All `@docusaurus/*` packages must use the same exact version.
- Commit `website/package-lock.json`; CI uses `npm ci`, never floating installs.
- Do not run Node.js tooling inside `.github/workflows/official-data-pipeline.yml`.
- Do not move Python package files, data parsers, release code, or source registry into `website/`.
- Default locale is Spanish `es`; secondary locale is English `en`.
- GitHub Pages is a single deployment; English lives under the localized `/en/` path while Spanish remains the default path.
- The project-page URL is `https://jccontrerasg08-cpu.github.io/arancel-mx/` unless repository Pages settings are deliberately changed later.
- Internal implementation specs under `docs/superpowers/` must not be exposed in public navigation or generated public docs.
- Root `README.md` and `README.en.md` remain concise repository entrypoints; they are not copied wholesale into the site.
- Public technical docs should be sourced from root `docs/` where practical. English translated Markdown belongs to Docusaurus native `website/i18n/en/docusaurus-plugin-content-docs/current/` rather than a second English root docs tree.
- Pages deploy job receives only `contents: read`, `pages: write`, `id-token: write`.
- Pull-request docs CI receives `contents: read` only and never deploys.
- All GitHub Actions references must be pinned to full commit SHAs. Resolve current official action tags immediately before the PR and record the resolved SHAs in the PR double-check evidence.
- Every implementation PR must include the same double-check gate required by the approved certification spec.

---

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
                ├── data-model.md
                ├── production-certification.md
                └── ...public translated docs

.github/workflows/
├── docs-ci.yml
└── docs-pages.yml
```

The docs plugin source path is root `../docs`. Public docs are filtered with explicit excludes so `docs/superpowers/**` never enters the site build.

### Task 1: Scaffold a minimal pinned Docusaurus site

**Files:**
- Create: `website/package.json`
- Create: `website/package-lock.json`
- Create: `website/tsconfig.json`
- Create: `website/docusaurus.config.ts`
- Create: `website/sidebars.ts`
- Create: `website/src/css/custom.css`
- Create: `website/src/pages/index.tsx`
- Modify: `.gitignore`

**Interfaces:**
- Produces: `cd website && npm run build` static site at `website/build/`.

- [ ] **Step 1: Re-verify upstream versions before writing package files**

Open the official Docusaurus installation page and record in the PR body:

```text
stable Docusaurus version
minimum Node.js version
verification date
```

During planning the verified values are Docusaurus `3.10.2` and Node.js `>=20.0`. If upstream stable changes before implementation, use the newly verified stable version consistently for all `@docusaurus/*` packages and update this plan's execution note in the PR body; do not mix Docusaurus package versions.

- [ ] **Step 2: Create a minimal package manifest manually rather than committing disposable scaffold content**

Use exact dependencies for the verified stable version. For the planning-time version the dependency core is:

```json
{
  "private": true,
  "scripts": {
    "start": "docusaurus start",
    "build": "docusaurus build",
    "clear": "docusaurus clear",
    "serve": "docusaurus serve",
    "write-translations": "docusaurus write-translations"
  },
  "dependencies": {
    "@docusaurus/core": "3.10.2",
    "@docusaurus/preset-classic": "3.10.2",
    "@mdx-js/react": "^3.0.0",
    "clsx": "^2.1.1",
    "prism-react-renderer": "^2.4.0",
    "react": "^19.0.0",
    "react-dom": "^19.0.0"
  },
  "engines": {
    "node": ">=20.0"
  }
}
```

If the re-verified Docusaurus package metadata requires different React/peer versions, use the exact compatible versions generated/resolved by npm and explain the difference in the PR double check rather than forcing the planning-time values.

- [ ] **Step 3: Generate and commit lockfile**

Run:

```bash
cd website
npm install
npm ci
npx docusaurus --version
```

Expected: the reported Docusaurus version exactly matches the pinned version and `npm ci` completes from the clean lockfile.

- [ ] **Step 4: Configure project-page routing and i18n**

In `docusaurus.config.ts` configure:

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

Disable the blog unless there is actual project content for it. Add navbar links for Docs, GitHub Releases, GitHub repository, and the locale dropdown.

- [ ] **Step 5: Add a minimal landing page**

The landing page must state only implemented capabilities: LIGIE/NICO source capture, provenance, DuckDB/CSV/JSON, fail-closed reconciliation, six-asset releases, CLI, and automated pipeline. Do not claim search APIs or legal advisory capability that the package does not provide.

- [ ] **Step 6: Ignore generated Node/Docusaurus output**

Add only:

```text
website/node_modules/
website/build/
website/.docusaurus/
```

Do not ignore `website/package-lock.json`.

- [ ] **Step 7: Verify the initial build**

Run:

```bash
cd website
npm ci
npm run build
cd ..
git diff --check
```

Expected: build succeeds and `website/build/` remains untracked.

- [ ] **Step 8: Commit**

```bash
git add website .gitignore
git commit -m "docs: scaffold Docusaurus site"
```

### Task 2: Consume canonical root docs and exclude internal implementation material

**Files:**
- Modify: `website/docusaurus.config.ts`
- Modify: `website/sidebars.ts`
- Create: `tests/test_docs_site_contract.py`
- Modify public docs under `docs/` only where front matter or public ordering is required.

**Interfaces:**
- Consumes: root `docs/` as canonical Spanish technical docs.
- Produces: public docs routes under `/arancel-mx/docs/...` with `docs/superpowers/**` excluded.

- [ ] **Step 1: Add RED static contract tests before changing Docusaurus docs configuration**

```python
from pathlib import Path


def test_public_docs_site_excludes_internal_superpowers_specs():
    config = Path("website/docusaurus.config.ts").read_text(encoding="utf-8")
    assert "../docs" in config
    assert "superpowers/**" in config
```

Add another test asserting no `website/docs/` directory exists, so the project cannot silently drift into hand-maintained duplicate Spanish docs.

- [ ] **Step 2: Confirm RED**

Run: `python -m pytest tests/test_docs_site_contract.py -q`

Expected: FAIL until root docs consumption is configured.

- [ ] **Step 3: Point preset-classic docs to `../docs`**

Use the docs plugin option `path: '../docs'`. Configure explicit excludes including at least:

```text
superpowers/**
```

If Docusaurus 3.10.2 rejects external docs paths during the proof build, stop this task and use the approved deterministic-copy fallback: create `website/scripts/sync-docs.mjs` that copies only a fixed allowlist into a generated ignored directory and supports `--check`. Do not create hand-maintained duplicates.

- [ ] **Step 4: Define explicit public sidebar**

Do not use auto-generated navigation for the entire root docs tree. `sidebars.ts` lists only public product docs such as data model, source/provenance guidance, release verification, production certification, and contribution guidance. Internal plans/specs remain unreachable because they are excluded from build input.

- [ ] **Step 5: Build and inspect generated routes**

Run:

```bash
cd website
npm ci
npm run build
find build -type f | grep -E 'superpowers|production-hardening' && exit 1 || true
cd ..
python -m pytest tests/test_docs_site_contract.py -q
git diff --check
```

Expected: no public build path contains internal superpowers material.

- [ ] **Step 6: Commit**

```bash
git add website/docusaurus.config.ts website/sidebars.ts tests/test_docs_site_contract.py docs
git commit -m "docs: publish canonical root documentation"
```

Stage only root docs actually changed for public front matter/navigation.

### Task 3: Add native English i18n with core ES/EN parity

**Files:**
- Create: `website/i18n/en/code.json`
- Create: `website/i18n/en/docusaurus-theme-classic/navbar.json`
- Create: `website/i18n/en/docusaurus-theme-classic/footer.json`
- Create: `website/i18n/en/docusaurus-plugin-content-docs/current/*.md`
- Modify: `website/docusaurus.config.ts`
- Modify: `tests/test_docs_site_contract.py`

**Interfaces:**
- Produces: Spanish default site and English site under `/en/` in one build.

- [ ] **Step 1: Generate Docusaurus translation skeletons**

Run:

```bash
cd website
npm ci
npm run write-translations -- --locale en
```

Commit only translation files that are used. Remove generated noise for plugins/features that are disabled.

- [ ] **Step 2: Translate public navigation and landing-page strings**

Translate labels faithfully. Keep technical identifiers such as `LIGIE`, `NICO`, `HS6`, `MX8`, `DuckDB`, `SHA256SUMS`, and GitHub workflow names unchanged where they are identifiers.

- [ ] **Step 3: Translate the core public docs set**

At minimum include English counterparts for every document present in the public sidebar. Do not translate `docs/superpowers/**` because those files are excluded and internal.

- [ ] **Step 4: Add parity test**

The Python static test reads `sidebars.ts` public document IDs and verifies corresponding translated Markdown exists under `website/i18n/en/docusaurus-plugin-content-docs/current/` for every public Spanish doc that requires translation.

- [ ] **Step 5: Build all locales and each locale separately**

Run:

```bash
cd website
npm ci
npm run build
npm run build -- --locale es
npm run build -- --locale en
cd ..
python -m pytest tests/test_docs_site_contract.py -q
git diff --check
```

Expected: all builds succeed. For the all-locales build, Spanish is at the base path and English is under `/en/` as documented by Docusaurus.

- [ ] **Step 6: Commit**

```bash
git add website/i18n website/docusaurus.config.ts tests/test_docs_site_contract.py
git commit -m "docs: add English Docusaurus localization"
```

### Task 4: Add read-only docs CI for pull requests

**Files:**
- Create: `.github/workflows/docs-ci.yml`
- Modify: `tests/test_docs_site_contract.py`

**Interfaces:**
- Produces: a non-required or separately-required `docs` job that validates Docusaurus changes without deployment permissions.

- [ ] **Step 1: Resolve official action tags to full SHAs before writing workflow**

Use GitHub API or `gh api` against the official action repositories to resolve the current tag commits for:

```text
actions/checkout@v6
actions/setup-node@v4
```

Record the tag and resolved full SHA in the PR double-check section. Do not use floating tags in committed YAML.

- [ ] **Step 2: Add RED workflow contract assertions**

Require:

```text
contents: read
no pages: write
no id-token: write
no contents: write
npm ci
npm run build
--locale es
--locale en
```

- [ ] **Step 3: Create docs CI workflow**

Trigger on `pull_request` and pushes to `main` when these paths change:

```text
website/**
docs/**
README.md
README.en.md
.github/workflows/docs-ci.yml
```

Use Node 20 because Docusaurus 3.10.2 officially requires Node >=20; if the implementation-time Docusaurus version raises the requirement, use the newly verified compatible Node LTS and document it.

- [ ] **Step 4: Run Python contract tests and local docs build**

```bash
python -m pytest tests/test_docs_site_contract.py -q
cd website
npm ci
npm run build
npm run build -- --locale es
npm run build -- --locale en
```

- [ ] **Step 5: Commit**

```bash
git add .github/workflows/docs-ci.yml tests/test_docs_site_contract.py
git commit -m "ci: validate Docusaurus documentation"
```

### Task 5: Add least-privilege GitHub Pages deployment

**Files:**
- Create: `.github/workflows/docs-pages.yml`
- Modify: `tests/test_docs_site_contract.py`

**Interfaces:**
- Produces: deployment of `website/build/` to the `github-pages` environment from protected `main` only.

- [ ] **Step 1: Confirm repository Pages source is GitHub Actions before enabling deploy**

In repository Settings -> Pages, select GitHub Actions as the publishing source. Do not deploy from a `gh-pages` branch because the approved design keeps generated output out of Git history.

- [ ] **Step 2: Resolve Pages action tags to full SHAs**

Resolve current official tags for:

```text
actions/checkout@v6
actions/setup-node@v4
actions/configure-pages@v5
actions/upload-pages-artifact@v4
actions/deploy-pages@v4
```

The official GitHub Pages docs currently require the deploy job to have at least `pages: write` and `id-token: write`; keep `contents: read` and no broader permissions.

- [ ] **Step 3: Add RED static workflow contract**

Assert build and deploy are separate jobs, deploy has `needs: build`, the environment is `github-pages`, PR events cannot execute deploy, and permissions are exactly:

```yaml
contents: read
pages: write
id-token: write
```

No `contents: write`, `issues: write`, `packages: write`, or release scripts are permitted.

- [ ] **Step 4: Implement Pages workflow**

Trigger on push to `main` for docs/website paths and `workflow_dispatch`. Build job runs `npm ci` and `npm run build` from `website/`, then uploads `website/build` with `upload-pages-artifact`. Deploy job uses `actions/deploy-pages` and the `github-pages` environment.

- [ ] **Step 5: Verify workflow contract and local build**

```bash
python -m pytest tests/test_docs_site_contract.py -q
cd website
npm ci
npm run build
cd ..
git diff --check
```

- [ ] **Step 6: Commit**

```bash
git add .github/workflows/docs-pages.yml tests/test_docs_site_contract.py
git commit -m "ci: deploy docs to GitHub Pages"
```

### Task 6: Add npm Dependabot coverage and public documentation links

**Files:**
- Modify: `.github/dependabot.yml`
- Modify: `README.md`
- Modify: `README.en.md`
- Modify: `CONTRIBUTING.md`
- Create: `docs/documentation-site.md`
- Modify: `tests/test_docs_site_contract.py`

**Interfaces:**
- Produces: discoverable public docs site and maintainable Node dependency policy.

- [ ] **Step 1: Add npm Dependabot configuration**

Add:

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

Preserve existing pip and GitHub Actions entries.

- [ ] **Step 2: Add README links without replacing repository quick-start content**

Add a prominent `Documentation`/`Documentación` link pointing to:

```text
https://jccontrerasg08-cpu.github.io/arancel-mx/
```

Keep installation, CLI examples, legal disclaimer, release links, and core architecture in the root READMEs so GitHub visitors can still understand the project without leaving the repository.

- [ ] **Step 3: Document contributor workflow**

`docs/documentation-site.md` explains:

```text
cd website
npm ci
npm run start
npm run build
npm run build -- --locale es
npm run build -- --locale en
```

It also explains that root `docs/` is canonical Spanish technical content, English translations live under native Docusaurus i18n, internal `docs/superpowers/` is excluded, and generated `website/build/` is never committed.

- [ ] **Step 4: Add static contract assertions for Dependabot and README link**

Ensure the test catches accidental removal of the `/website` npm Dependabot entry and the public site URL.

- [ ] **Step 5: Verify**

```bash
python -m pytest -q
python -m build
cd website
npm ci
npm run build
npm run build -- --locale es
npm run build -- --locale en
cd ..
git diff --check
```

- [ ] **Step 6: Commit**

```bash
git add .github/dependabot.yml README.md README.en.md CONTRIBUTING.md docs/documentation-site.md tests/test_docs_site_contract.py
git commit -m "docs: document and maintain public docs site"
```

### Task 7: Live Pages deployment certification

**Files:**
- No code changes required unless the live deployment exposes a reproducible configuration bug.
- Update documentation only if actual deployed behavior differs from documented assumptions.

**Interfaces:**
- Produces: a live ES/EN site and evidence that docs deployment is independent from production data publication.

- [ ] **Step 1: Double-check before merging the Pages PR**

Verify:

```text
main CI green
Production certification complete
Docusaurus version and Node requirement re-verified from official docs
Pages workflow action SHAs resolve to official action repositories
Pages source set to GitHub Actions
no dataset release permissions in docs workflows
no internal superpowers docs in website/build
```

- [ ] **Step 2: Merge through the protected branch ruleset**

Use squash merge only after `test` and docs CI are green.

- [ ] **Step 3: Verify the Pages workflow**

Require build and deploy success and verify the deployment URL reported by `actions/deploy-pages` is under `https://jccontrerasg08-cpu.github.io/arancel-mx/`.

- [ ] **Step 4: Smoke-test public routes**

Check at least:

```text
/
/docs/
/en/
/en/docs/
```

Check links to the repository and Releases. Confirm no `/superpowers/` route is present.

- [ ] **Step 5: Re-run production isolation checks**

After docs deployment, verify no new `data-*` release/tag and no production data-alert Issue was created by docs workflows.

- [ ] **Step 6: Final repository verification**

```bash
python -m pytest -q
python -m build
cd website
npm ci
npm run build
cd ..
git diff --check
```

The Docusaurus subproject is complete only after both ES/EN public routes and production-isolation checks pass.
