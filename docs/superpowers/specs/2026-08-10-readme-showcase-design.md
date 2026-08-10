# arancel-mx README showcase design

Date: 2026-08-10
Status: approved design, ready for implementation planning

## Goal

Redesign the public `README.md` so `arancel-mx` communicates its value in the first few seconds, while preserving the repository's existing technical content, CI contract, official-source traceability, and current assets.

The visual direction combines:

- Astryx-style premium hero composition, centered identity, strong information hierarchy, badges, quick links, and architecture-oriented storytelling.
- Docusaurus-style open-source credibility, dense but useful badges, clear onboarding, and fast routes to installation, docs, contribution, and status.
- `arancel-mx`-specific visuals for Mexican tariff data, LIGIE/NICO mapping, official-source provenance, DuckDB artifacts, and reproducible releases.

Primary language: Spanish.
Secondary language: full English mirror in `README.en.md`.

## Success criteria

The new README should:

1. Explain what `arancel-mx` is within the first viewport.
2. Make the project look like a serious public-data and open-source package rather than an internal script repository.
3. Show the data path from official sources to reproducible release artifacts.
4. Visually explain HS6 -> MX8 -> NICO10.
5. Preserve only claims that are already true in the repository or clearly label future work as roadmap.
6. Preserve the current public-distribution test contract.
7. Keep installation and CLI usage easy to copy.
8. Reuse existing assets where useful.
9. Avoid JavaScript-dependent README effects and rely on GitHub-compatible Markdown, HTML, SVG, GIF, and badges.
10. Keep the Spanish and English versions structurally aligned.

## Existing assets to reuse

Current repository assets include:

- `docs/demo.gif`
- `docs/demo.svg`
- `docs/dof_timeline.png`
- `docs/nico_flow.png`
- `docs/data-model.md`
- `docs/sources.md`
- `docs/release-process.md`

The terminal demo remains the primary animated asset.

## New assets

Create a focused visual set under `docs/assets/`:

- `docs/assets/arancel-mx-banner.svg`
- `docs/assets/hs-mx-nico-flow.svg`
- `docs/assets/pipeline.svg`
- `docs/assets/provenance.svg`
- `docs/assets/dataset-status.svg`

### Design principles for assets

- Clean and professional rather than decorative.
- Legible in GitHub light and dark themes where practical.
- No external JavaScript.
- No visual claims that depend on live data unless generated automatically.
- Avoid excessive motion. One primary GIF is enough.
- SVG assets should provide visual hierarchy, diagrams, cards, or data-flow explanation.

## README top section

The README opens with a centered hero inspired by Astryx and Docusaurus.

It should contain:

1. Full-width or wide `arancel-mx` banner.
2. Project name.
3. One-line positioning statement.
4. Language selector.
5. Useful badges.
6. Quick navigation links.
7. Main terminal demo.

Suggested positioning line:

> Datos arancelarios de Mexico, reproducibles, auditables y trazables.

Language switcher:

```html
<p align="center">
  <strong>Español</strong> ·
  <a href="./README.en.md">English</a>
</p>
```

English README uses the inverse selector.

## Badge strategy

Use badges only when they communicate a real project state.

Initial candidates:

- CI
- Python 3.11+
- Apache-2.0
- DuckDB
- PRs welcome
- latest release, only if releases are configured and trustworthy

Avoid decorative badges that do not help a user make a decision.

## Quick navigation

Provide a compact centered navigation line such as:

- Quick Start
- Dataset
- CLI
- Python
- Docs
- Sources
- Contributing

Links should point to internal README anchors or repository files.

## README information architecture

### 1. Hero

Purpose: answer "what is this?" immediately.

Contents:

- banner
- project name
- positioning statement
- language selector
- badges
- quick navigation

### 2. Demo

Use `docs/demo.gif` as the main animated element.

Supporting copy should be short and action-oriented:

- Busca
- Normaliza
- Verifica
- Publica

Do not add multiple competing GIFs.

### 3. Alcance

Required exact heading:

```markdown
## Alcance
```

Explain that `arancel-mx` is a focused public-data layer for Mexican tariff information, with traceability toward official sources.

The section should clarify that the public core is data and tooling rather than a full commercial customs product.

### 4. HS6 -> MX8 -> NICO10

Use `docs/assets/hs-mx-nico-flow.svg`.

Core visual concept:

```text
HS 6 digitos
   ↓
Fraccion arancelaria MX 8 digitos
   ↓
NICO 2 digitos adicionales
   ↓
Identificador mexicano de 10 digitos
```

Use a clearly labeled example only if it is validated against the project's data or official source records before publication.

### 5. Por que arancel-mx

Present three primary project properties:

- Trazabilidad
- Reproducibilidad
- Auditabilidad

Map them to real mechanisms:

- DOF / SNICE / Diputados provenance
- DuckDB / CSV / JSON deterministic outputs
- SHA256 manifests and source evidence

Use `docs/assets/provenance.svg` if it improves scanning.

### 6. Pipeline

Use `docs/assets/pipeline.svg` to show:

```text
DOF / SNICE / Diputados
          ↓
     Discovery
          ↓
      Capture
      URL + hash
          ↓
       Parser
          ↓
   Normalization
          ↓
    Validation
          ↓
  Reconciliation
          ↓
      DuckDB
    ↙    ↓    ↘
  CSV   JSON  manifest
          ↓
   GitHub Release
```

The visual must reflect actual or intended repository modules. Future automation should be labeled as roadmap where not yet implemented.

### 7. Instalacion

Required exact heading:

```markdown
## Instalación
```

Keep the current venv and editable dev-install workflow.

Commands:

```bash
python -m venv .venv
python -m pip install -e ".[dev]"
python -m arancel_mx --help
```

Separate activation commands for PowerShell and macOS/Linux.

### 8. Uso desde CLI

Document only commands that currently exist.

Current commands to preserve:

- `python -m arancel_mx --help`
- `python -m arancel_mx build ...`
- `python -m arancel_mx update ...`
- `python -m arancel_mx reconcile ...`
- `python -m arancel_mx release ...`

Avoid documenting speculative CLI commands until implemented.

### 9. Uso desde Python

Required exact heading:

```markdown
## Uso desde Python
```

The current stable public example should remain minimal and truthful:

```python
import arancel_mx

print(arancel_mx.__version__)
```

Potential future APIs such as `search`, `lookup`, HS mapping, or NICO lookup belong in roadmap until implemented.

### 10. Dataset status

Use a compact visual or table showing capabilities such as:

- LIGIE tracking
- NICO tracking
- DOF provenance
- SNICE provenance
- DuckDB output
- CSV output
- JSON output
- SHA256 manifests
- automated updates
- PyPI publication

Status labels must be verified from repository state before publication.

Suggested status vocabulary:

- stable
- available
- in progress
- planned

Avoid presenting roadmap work as complete.

### 11. Fuentes oficiales

Keep the literal phrase `fuentes oficiales` for CI compatibility.

Prefer a compact table with source and purpose, then provide concrete links.

Primary groups:

- Diario Oficial de la Federacion
- Camara de Diputados
- SNICE

Point users to `src/arancel_mx/sources/source_registry.json` and `docs/sources.md` for the technical source registry.

### 12. Cambio de nomenclatura y proceso oficial

Reuse:

- `docs/dof_timeline.png`
- `docs/nico_flow.png`

Move them lower in the README so they support the narrative without dominating the first viewport.

Explain that the diagrams are contextual source/process references, not dynamic repository status displays.

### 13. Arquitectura y estructura del repositorio

Required exact heading:

```markdown
## Estructura del repositorio
```

Show the current Python package boundaries:

```text
src/arancel_mx/
├── domain/
├── parsers/
├── pipeline/
├── release/
├── sources/
└── storage/
```

Each directory should receive a one-line description.

The README should favor boundaries and responsibilities over a full file dump.

### 14. Documentacion

Provide direct links to:

- `docs/data-model.md`
- `docs/sources.md`
- `docs/release-process.md`
- `CONTRIBUTING.md`
- `SECURITY.md`

### 15. Pruebas

Required exact heading:

```markdown
## Pruebas
```

Keep:

```bash
python -m pytest -q
python -m build
git diff --check
```

State that CI should run the same development dependency set used locally.

### 16. Roadmap

Roadmap should distinguish current and future work.

Candidate items to verify before publishing:

Current or near-current:

- source registry
- XLS/XLSX/PDF ingestion
- canonical normalization
- DuckDB outputs
- deterministic artifacts
- provenance
- SHA256 manifests

Future or in progress:

- HS6 <-> MX8 <-> NICO10 public lookup API
- search-oriented CLI
- automated DOF watcher
- automatic data releases
- PyPI trusted publishing
- public documentation site
- API or MCP access

Do not use checkmarks for anything that has not been verified in the implementation review.

### 17. Legal disclaimer

The README must include the exact phrase:

`No constituye asesoría legal`

Recommended form:

> `arancel-mx` es una herramienta tecnica y de datos. **No constituye asesoría legal.** Para decisiones regulatorias, de cumplimiento o clasificacion arancelaria deben consultarse las fuentes oficiales aplicables.

### 18. Contributing, security, and license

Keep these short and easy to find.

Required literal references for CI:

- `CONTRIBUTING.md`
- `SECURITY.md`
- `Apache-2.0`

Use a normal ASCII hyphen in `Apache-2.0`.

## English README

Create `README.en.md` as a full English mirror, not a partial summary.

Requirements:

- same section order
- same visuals
- same commands
- same claims
- same links
- English language selector with link back to `README.md`
- no divergence in feature status

The Spanish README remains the repository default.

## CI compatibility contract

The current public-distribution test requires these strings to appear in `README.md`:

```text
arancel-mx
apache-2.0
python -m arancel_mx
contributing.md
security.md
no constituye asesoría legal
fuentes oficiales
## alcance
## instalación
## uso desde python
## estructura del repositorio
## pruebas
```

Implementation must preserve all of them after lowercase normalization.

Do not weaken or delete the test merely to accommodate the redesign.

## GitHub README constraints

The implementation must assume GitHub's README rendering environment:

- no custom JavaScript
- limited inline HTML/CSS behavior
- SVG and GIF are preferred for visual composition
- external images should be avoided when repository-local assets can be used
- links and badges must remain functional in GitHub rendering
- visual content must remain understandable when images fail to load

## Accessibility

- Provide useful `alt` text for all images.
- Do not encode essential meaning only through color.
- Keep sufficient text contrast inside custom SVGs.
- Keep headings semantic and sequential.
- Avoid animated assets that flash or move excessively.

## Performance

- Keep image assets reasonably small.
- Prefer SVG for diagrams and hero graphics.
- Keep one main GIF rather than several animations.
- Optimize existing PNG/GIF assets only if quality is preserved.

## Files expected to change during implementation

Primary:

- `README.md`
- `README.en.md`

New:

- `docs/assets/arancel-mx-banner.svg`
- `docs/assets/hs-mx-nico-flow.svg`
- `docs/assets/pipeline.svg`
- `docs/assets/provenance.svg`
- `docs/assets/dataset-status.svg`

Possible supporting test updates only if needed to validate new bilingual or asset requirements, but the existing README contract must remain intact.

## Non-goals

This README redesign does not itself implement:

- a new tariff search API
- a new CLI command
- automatic DOF synchronization
- PyPI publication
- a documentation website
- live dataset status generation

Those can be implemented separately after the README accurately distinguishes current features from roadmap.

## Validation plan

Before considering the README redesign complete:

1. Verify every documented command against the current CLI.
2. Verify every capability marked available against repository code or workflows.
3. Run `python -m pytest -q`.
4. Run `python -m build`.
5. Run `git diff --check`.
6. Confirm the public-distribution README test passes.
7. Render the README on GitHub and inspect both light and dark themes.
8. Verify all repository-local images render correctly.
9. Verify language-switch links in both directions.
10. Confirm the English README has no feature-status drift from the Spanish README.

## Implementation order

Recommended sequence after approval of this spec:

1. Verify current feature and workflow status.
2. Build the Spanish README content structure.
3. Create the visual assets.
4. Integrate the existing demo and official-process images.
5. Create the English mirror.
6. Run tests and build checks.
7. Review GitHub rendering.
8. Refine asset sizing and information density.

## Final design decision

Use the "full showcase" approach:

- Spanish-first README
- complete English mirror
- Astryx-inspired premium hero
- Docusaurus-inspired badges and onboarding
- one primary GIF
- multiple lightweight SVG explanatory visuals
- strong source-provenance storytelling
- accurate current-state vs roadmap separation
- no fake APIs or unverified feature claims
- CI contract preserved
