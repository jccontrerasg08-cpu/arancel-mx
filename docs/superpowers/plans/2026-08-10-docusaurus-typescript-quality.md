# Docusaurus TypeScript Quality Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Ensure the Docusaurus site uses the officially supported TypeScript toolchain and catches configuration/component type errors before Pages deployment.

**Architecture:** This plan is a prerequisite companion to `2026-08-10-docusaurus-documentation-site.md`. It adds only the official TypeScript support packages and a typecheck command; it does not change the Python runtime or documentation content model.

**Tech Stack:** Docusaurus 3.10.2 planning baseline, TypeScript >=5.1 for Docusaurus 3.10.2, `@docusaurus/module-type-aliases`, `@docusaurus/tsconfig`, `@docusaurus/types`, npm.

## Global Constraints

- Re-verify Docusaurus stable version and TypeScript minimum immediately before implementation.
- During planning, official Docusaurus 3.10.2 docs specify TypeScript 5.1 minimum and explicitly require `typescript`, `@docusaurus/module-type-aliases`, `@docusaurus/tsconfig`, and `@docusaurus/types` for TypeScript setup.
- Every `@docusaurus/*` package in the site uses the same Docusaurus version.
- Type checking is documentation CI only; it never enters the official tariff data pipeline.

---

### Task 1: Declare the official TypeScript support packages

**Files:**
- Modify: `website/package.json`
- Modify: `website/package-lock.json`
- Modify: `website/tsconfig.json`

**Interfaces:**
- Produces: `npm run typecheck` using the Docusaurus-supported TS config.

- [ ] **Step 1: Re-verify official TypeScript support docs**

Record the current Docusaurus version, minimum TypeScript version, and required support packages in the implementation PR double-check section.

- [ ] **Step 2: Add dev dependencies**

For Docusaurus 3.10.2, declare the same exact `3.10.2` version for:

```text
@docusaurus/module-type-aliases
@docusaurus/tsconfig
@docusaurus/types
```

Declare `typescript` at a version satisfying Docusaurus 3.10.2's documented `>=5.1` minimum and compatible with the generated lockfile. Add:

```json
"typecheck": "tsc --noEmit"
```

to `scripts`.

- [ ] **Step 3: Use the official base tsconfig**

`website/tsconfig.json`:

```json
{
  "extends": "@docusaurus/tsconfig",
  "compilerOptions": {
    "baseUrl": "."
  }
}
```

- [ ] **Step 4: Regenerate lockfile and verify**

```bash
cd website
npm install
npm ci
npm run typecheck
npm run build
```

Expected: typecheck and production build succeed.

- [ ] **Step 5: Commit**

```bash
git add website/package.json website/package-lock.json website/tsconfig.json
git commit -m "docs: enable Docusaurus TypeScript checks"
```

### Task 2: Enforce type checking in docs CI

**Files:**
- Modify: `.github/workflows/docs-ci.yml`
- Modify: `tests/test_docs_site_contract.py`

**Interfaces:**
- Produces: pull-request docs CI that fails on TypeScript config/component errors before build/deploy.

- [ ] **Step 1: Add RED contract test**

Assert `.github/workflows/docs-ci.yml` contains `npm run typecheck` before `npm run build`.

- [ ] **Step 2: Confirm RED**

Run: `python -m pytest tests/test_docs_site_contract.py -q`

- [ ] **Step 3: Add typecheck step to docs CI**

Order must be:

```text
npm ci
npm run typecheck
npm run build
npm run build -- --locale es
npm run build -- --locale en
```

- [ ] **Step 4: Verify**

```bash
python -m pytest tests/test_docs_site_contract.py -q
cd website
npm ci
npm run typecheck
npm run build
cd ..
git diff --check
```

- [ ] **Step 5: Commit**

```bash
git add .github/workflows/docs-ci.yml tests/test_docs_site_contract.py
git commit -m "ci: typecheck Docusaurus site"
```
