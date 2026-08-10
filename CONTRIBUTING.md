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

No incluyas credenciales, bases locales, descargas originales no revisadas, datos personales ni rutas absolutas de tu equipo. Los artefactos generados y descargas pertenecen a rutas ignoradas por Git.

Al enviar una contribución aceptas que se publique bajo Apache-2.0 conforme a la sección 5 de la licencia. Para vulnerabilidades, sigue [SECURITY.md](SECURITY.md) y no abras un issue público.
