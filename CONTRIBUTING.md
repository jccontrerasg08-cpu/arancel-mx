# Contribuir a arancel-mx

Gracias por mejorar el proyecto. Trabaja desde un fork y abre un pull request
pequeño, enfocado y verificable.

## Preparación

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --requirement requirements.txt pytest
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider -q
```

No incluyas `.env`, tokens, bases locales, descargas originales, RFC reales,
alertas, historiales de usuario ni otros datos personales u operativos.

## Pull requests

1. Explica el problema y el alcance del cambio.
2. Agrega o actualiza pruebas que fallen sin el cambio y pasen con él.
3. Ejecuta la suite completa y `git diff --check`.
4. Para datos o activos, documenta autoridad/autor, URL exacta, versión o fecha,
   SHA-256, transformación y términos de redistribución.
5. Conserva la atribución y las licencias de terceros.

Al enviar una contribución aceptas que se publique bajo Apache-2.0, conforme a
la sección 5 de la licencia. El repositorio público no escribe ni sincroniza
automáticamente cambios hacia repositorios privados del mantenedor.

Para vulnerabilidades, usa el proceso privado de [SECURITY.md](SECURITY.md), no
un issue público.
