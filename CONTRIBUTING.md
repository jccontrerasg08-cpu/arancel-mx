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

1. Explica el problema y limita el alcance.
2. Agrega una prueba que falle antes del cambio y pase después.
3. Para una fuente, documenta autoridad, URL canónica, función documental y prioridad.
4. Para un fixture, registra el origen y evita incluir información privada.
5. Ejecuta `python -m pytest -q`, `python -m build` y `git diff --check`.
6. Actualiza la documentación cuando cambien interfaces, esquema o proceso de publicación.

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

Al enviar una contribución aceptas que se publique bajo Apache-2.0 conforme a la sección 5 de la licencia. Los términos de uso, atribución y excepciones están en [TERMS.md](TERMS.md). Para un release público, usa [opensource-checklist.md](opensource-checklist.md). Para vulnerabilidades, sigue [SECURITY.md](SECURITY.md) y no abras un issue público.
