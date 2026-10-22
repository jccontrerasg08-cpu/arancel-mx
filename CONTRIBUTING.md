# Contribuir a arancel-mx

Gracias por mejorar el proyecto. Trabaja desde un fork y abre un pull request pequeño, enfocado y verificable.

## Preparación

```bash
python -m venv .venv
python -m pip install -e ".[dev]"
python -m pytest -q
```

## Tipos de contribución

- fuentes oficiales y reglas de descubrimiento;
- parsers y fixtures offline;
- modelo, normalización y validaciones arancelarias;
- almacenamiento, conciliación y artefactos de publicación;
- documentación, seguridad y experiencia de contribución.

## Flujo recomendado

1. Ubica tu cambio en la [arquitectura](docs/architecture.md) y respeta sus invariantes. Si tocas documentación, sigue la [guía de estilo](docs/documentation-style.md).
2. Lee y aplica la [Política de desarrollo verificable](docs/governance/DEVELOPMENT_POLICY.md), incluida su clasificación de evidencia y su puerta de cambio.
3. Explica el problema y limita el alcance.
4. Agrega una prueba que falle antes del cambio y pase después.
5. Para una fuente, documenta autoridad, URL canónica, función documental y prioridad.
6. Para un fixture, registra el origen y evita incluir información privada.
7. Ejecuta `python -m pytest -q`, `python -m build` y `git diff --check`.
8. Actualiza la documentación cuando cambien interfaces, esquema o proceso de publicación, y registra evidencia fechada para cambios de seguridad, datos o despliegue.
9. Para una decisión transversal —API, esquema, release, seguridad, automatización o mantenimiento futuro— usa la plantilla de [`docs/decisions/0000-template.md`](docs/decisions/0000-template.md). No la uses para una corrección local o cambio editorial rutinario.
10. Cuando una contribución modifique biblioteca, CLI o `/v1`, aplica la [política de compatibilidad](docs/compatibility.md): los cambios incompatibles requieren reemplazo, aviso y changelog.
11. Para revisar reportes nuevos, sigue la checklist semanal de [`docs/operations/issue-triage.md`](docs/operations/issue-triage.md). La rutina ordena la cola; no sustituye la revisión técnica ni cierra casos controvertidos automáticamente.

## Mantener el código simple

El repositorio incluye el método [Ponytail](https://github.com/dietrichgebert/ponytail) para agentes de código (Cursor lee `.cursor/rules/ponytail.mdc`; Claude Code, `.claude/skills/`). Resume lo que se espera también de un cambio humano: el cambio completo más pequeño, reutilizar lo que ya existe antes que escribir algo nuevo, sin abstracciones ni dependencias que nadie pidió, y una prueba para cada lógica no trivial.

- `ponytail-review` revisa un diff buscando sólo sobreingeniería.
- `ponytail-audit` hace lo mismo sobre todo el repositorio.
- `ponytail-debt` lista los atajos marcados con `shortcut:` o `ponytail:`, cada uno con su límite y su condición de mejora.

Estas herramientas no sustituyen la revisión de corrección, seguridad ni datos oficiales.

## Revisión en GitHub

arancel-mx no reimplementa la UI de GitHub. Para revisar PRs, instala en el navegador:

- [Octotree](https://github.com/ovity/octotree)
- [Refined GitHub](https://github.com/refined-github/refined-github)
- [Pretty Pull Requests](https://github.com/brentyates/prettypullrequests)

No abras issues pidiendo esas funciones aquí.

## Cambios en GitHub Actions

Un cambio de workflow es un cambio de producción: el pipeline oficial publica datos y firma provenance. Mantén permisos mínimos por job, acciones fijadas por SHA completo con comentario de versión, y valores dinámicos pasados por `env:` en lugar de interpolarlos dentro de un script de shell.

El contrato estructural se verifica offline con `python -m pytest tests/test_workflow_hardening.py -q`. Antes de abrir el pull request conviene además auditar con las herramientas estándar del ecosistema:

```bash
zizmor .github/workflows/
actionlint
```

No incluyas credenciales, bases locales, descargas originales no revisadas, datos personales ni rutas absolutas de tu equipo. Los artefactos generados y descargas pertenecen a rutas ignoradas por Git.

Al enviar una contribución aceptas que se publique bajo Apache-2.0 conforme a la sección 5 de la licencia. Los términos de uso, atribución y excepciones están en [TERMS.md](TERMS.md). Para un release público, usa [opensource-checklist.md](opensource-checklist.md) o el formulario [`.github/ISSUE_TEMPLATE/open_source_release.yml`](.github/ISSUE_TEMPLATE/open_source_release.yml). Para vulnerabilidades, sigue [SECURITY.md](SECURITY.md) y no abras un issue público.
