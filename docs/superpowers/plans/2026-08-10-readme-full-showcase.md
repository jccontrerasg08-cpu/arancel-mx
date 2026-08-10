# arancel-mx README Full Showcase Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Redesign the public README into a Spanish-first, bilingual, full-showcase OSS landing page without losing any current README information, while preserving CI requirements and accurately distinguishing implemented features from roadmap work.

**Architecture:** Keep `README.md` as the Spanish source of truth and add `README.en.md` as a full English mirror. Reuse the existing terminal GIF and official-process images, including `dof_timeline.png` as part 1 and `dof_timeline2.png` as part 2, and add lightweight repository-local SVGs for hero, mapping, provenance, pipeline, and status. Preserve every current URL, command, source reference, contribution instruction, license/NOTICE reference, and acknowledgement.

**Tech Stack:** GitHub-flavored Markdown, repository-local SVG/GIF/PNG assets, Mermaid for readable fallback diagrams, Python 3.11 package docs, pytest/build CI.

## Global Constraints

- Spanish is the default README language; `README.en.md` is the complete English mirror.
- Do not delete or omit any information currently present in `README.md`.
- Preserve `docs/demo.gif`, `docs/dof_timeline.png`, `docs/dof_timeline2.png`, and `docs/nico_flow.png`.
- Document `dof_timeline.png` as part 1 and `dof_timeline2.png` as part 2.
- Preserve every current official-source URL and CLI command.
- Preserve literal CI-required strings in `README.md`: `arancel-mx`, `apache-2.0`, `python -m arancel_mx`, `contributing.md`, `security.md`, `no constituye asesoría legal`, `fuentes oficiales`, `## alcance`, `## instalación`, `## uso desde python`, `## estructura del repositorio`, `## pruebas`.
- Use ASCII hyphen in `Apache-2.0`.
- Do not document speculative APIs as implemented.
- Avoid JavaScript-only effects; use GitHub-compatible Markdown/HTML/SVG/GIF.
- Final public branch must not contain `docs/superpowers`, because `tests/test_public_distribution.py` forbids it.

---

### Task 1: Baseline preservation contract

**Files:**
- Modify: `tests/test_public_distribution.py`

**Interfaces:**
- Consumes: current README content contract.
- Produces: regression assertions that protect current README information during redesign.

- [ ] **Step 1: Extend the README contract test**

Add exact checks for existing URLs, commands, image references, `source_registry.json`, `LICENSE`, `NOTICE`, and the three official-process image files so future redesigns cannot silently drop them.

- [ ] **Step 2: Verify the test fails before README redesign if newly required headings/assets are absent**

Run: `python -m pytest tests/test_public_distribution.py -q`
Expected: failure only for currently missing redesigned README requirements, not import errors.

- [ ] **Step 3: Commit the preservation test**

```bash
git add tests/test_public_distribution.py
git commit -m "test: preserve public README information contract"
```

### Task 2: Spanish README full-showcase redesign

**Files:**
- Modify: `README.md`

**Interfaces:**
- Consumes: current README content and all current repository-local images/URLs/commands.
- Produces: Spanish default README with full-showcase information architecture.

- [ ] **Step 1: Build the hero and navigation**

Add centered hero, Spanish/English selector, existing badges plus DuckDB/PRs-welcome badges, quick navigation, and the existing `docs/demo.gif`.

- [ ] **Step 2: Preserve and expand core sections**

Retain every current bullet and sentence under summary, differentiation, features, installation, CLI, documentation, sources, process/calendar, contributions, license, and acknowledgements. Reorganize into semantic headings while preserving the information.

- [ ] **Step 3: Add required new sections**

Add `## Alcance`, HS6 -> MX8 -> NICO10 explanation, architecture/pipeline, `## Uso desde Python`, model/artifacts, `## Estructura del repositorio`, `## Pruebas`, project status, roadmap, security, and legal disclaimer.

- [ ] **Step 4: Preserve official-process images with correct part labels**

Render in order:

1. `docs/dof_timeline.png` as "Parte 1"
2. `docs/dof_timeline2.png` as "Parte 2"
3. `docs/nico_flow.png` as NICO/DOF flow

Keep the existing attribution note to DOF/SNICE.

- [ ] **Step 5: Verify the focused README test passes**

Run: `python -m pytest tests/test_public_distribution.py::test_readme_describes_the_focused_public_project -q`
Expected: PASS.

- [ ] **Step 6: Commit**

```bash
git add README.md
git commit -m "docs: redesign Spanish README without information loss"
```

### Task 3: Full English mirror

**Files:**
- Create: `README.en.md`

**Interfaces:**
- Consumes: final Spanish README structure, commands, links, feature status, and visuals.
- Produces: complete English mirror with link back to `README.md`.

- [ ] **Step 1: Translate all explanatory text while preserving commands and links exactly**

Use the same section order, visuals, source URLs, commands, status claims, roadmap boundaries, and legal caveat.

- [ ] **Step 2: Add bidirectional language selector**

English README must contain `Español` linking to `README.md` and `English` marked current.

- [ ] **Step 3: Commit**

```bash
git add README.en.md
git commit -m "docs: add complete English README mirror"
```

### Task 4: Repository-local visual assets

**Files:**
- Create: `docs/assets/arancel-mx-banner.svg`
- Create: `docs/assets/hs-mx-nico-flow.svg`
- Create: `docs/assets/pipeline.svg`
- Create: `docs/assets/provenance.svg`
- Create: `docs/assets/dataset-status.svg`
- Modify: `README.md`
- Modify: `README.en.md`

**Interfaces:**
- Consumes: stable project claims only.
- Produces: GitHub-renderable visuals with useful alt text and no JavaScript.

- [ ] **Step 1: Create banner SVG**

Use a clean dark/light-compatible vector banner containing `arancel-mx`, Mexican tariff-data positioning, and subtle data-grid/code motifs.

- [ ] **Step 2: Create HS/MX/NICO mapping SVG**

Show HS 6 -> Mexican tariff fraction 8 -> NICO +2 -> 10-digit Mexican identifier without asserting a specific commodity code example unless verified.

- [ ] **Step 3: Create pipeline SVG**

Show official sources -> discovery -> capture/hash -> parser -> normalization -> validation -> reconciliation -> DuckDB -> CSV/JSON/manifest -> release.

- [ ] **Step 4: Create provenance and dataset-status SVGs**

Use labels only for capabilities already verified by source/tests; mark search API and PyPI as evolving/planned.

- [ ] **Step 5: Embed assets in both READMEs with fallback explanatory text**

- [ ] **Step 6: Commit**

```bash
git add docs/assets README.md README.en.md
git commit -m "docs: add README showcase visual assets"
```

### Task 5: Remove private planning artifacts and verify release readiness

**Files:**
- Delete: `docs/superpowers/specs/2026-08-10-readme-showcase-design.md`
- Delete: `docs/superpowers/plans/2026-08-10-readme-full-showcase.md`
- Verify: `README.md`
- Verify: `README.en.md`
- Verify: `tests/test_public_distribution.py`

**Interfaces:**
- Consumes: complete redesigned documentation.
- Produces: public branch compliant with repository distribution policy.

- [ ] **Step 1: Delete `docs/superpowers` planning/spec files from the public branch**

The repository test explicitly forbids this path.

- [ ] **Step 2: Run the full test suite**

Run: `python -m pytest -q`
Expected: all tests pass.

- [ ] **Step 3: Build distributions**

Run: `python -m build`
Expected: wheel and sdist build successfully.

- [ ] **Step 4: Check whitespace**

Run: `git diff --check`
Expected: no output.

- [ ] **Step 5: Verify no-loss README coverage**

Confirm every old command, URL, source, image, contribution instruction, `LICENSE`, `NOTICE`, and acknowledgement remains represented in `README.md`.

- [ ] **Step 6: Commit cleanup**

```bash
git add -A
git commit -m "docs: finalize public README showcase"
```

- [ ] **Step 7: Open PR against `main` and require CI green before merge**
