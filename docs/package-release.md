# Release del paquete de Python

Este documento es el contrato de mantenimiento para publicar `arancel-mx` en TestPyPI y PyPI. La instalación, la CLI y la API de Python para consumidores viven en [`docs/consumer-cli.md`](consumer-cli.md) y [`docs/external-consumption.md`](external-consumption.md). La transacción de la GitHub Release `data-*` vive en [`docs/release-process.md`](release-process.md).

## Estado de las versiones

`arancel-mx==0.3.6` está publicado en PyPI. El checkout declara `project.version` `0.3.7`; esa versión no está en PyPI hasta que `pkg-v0.3.7` pase TestPyPI y la matriz de sistemas operativos y versiones de Python. `0.3.3`, `0.3.4` y `0.3.5` existen sólo en TestPyPI y no deben promoverse ni reconstruirse con las mismas versiones:

- `0.3.3` falló porque el workflow anterior interpretaba `$GITHUB_WORKSPACE` con PowerShell;
- `0.3.4` no podía imprimir una flecha Unicode en la ayuda de la CLI con CP1252;
- `0.3.5` se certificó antes de que se integraran en main cambios posteriores de assets del Central Hub y de la API.

La versión `0.3.7` alinea el sitio estático del paquete con la reconstrucción de la fuente del frontend integrada después de `pkg-v0.3.6`.

El dataset no se empaqueta en el wheel ni en el sdist. Los datos arancelarios publicados permanecen en GitHub Releases inmutables con nombre `data-YYYY.MM.DD`.

Quien mantenga el repositorio y necesite el pipeline de ETL y parsing puede instalar el extra opcional:

```bash
pip install "arancel-mx[maintainer]"
```

## Versiones del paquete y de los datos son independientes

La distribución de Python usa versiones de paquete PEP 440, como `0.3.6` (PyPI) y `0.3.7` (en el árbol). Los datasets arancelarios usan tags de fecha inmutables, como `data-2026.08.17` (el actual `/releases/latest`). La descripción larga de la página del proyecto en PyPI sigue siendo la de la subida de `0.3.6` hasta que `pkg-v0.3.7` complete sus compuertas de release.

Un cambio en el paquete no crea un dataset arancelario nuevo. Un dataset arancelario nuevo no exige reconstruir el wheel de Python.

## Tags de git y GitHub Releases

Los candidatos del paquete usan tags de git como:

```text
pkg-v0.2.0
```

El workflow del paquete **no debe crear una GitHub Release** para los tags `pkg-v*`. Las GitHub Releases quedan reservadas para los bundles `data-*`, porque los enlaces públicos `/releases/latest/download/...` del repositorio forman parte del contrato de descarga del dataset.

El canal de publicación del paquete es, en cambio:

```text
git tag pkg-vX.Y.Z
        ↓
GitHub Actions construye una sola vez
        ↓
TestPyPI
        ↓
certificación externa
        ↓
aprobación manual de producción
        ↓
PyPI
```

## Regla de construir una sola vez

El wheel y el sdist que se promueven a PyPI deben ser exactamente los mismos bytes certificados a través de TestPyPI. Una publicación de producción no puede reconstruir el paquete después de la certificación en staging. Los valores SHA256 se generan justo después de la única construcción y se vuelven a comprobar antes de cada paso de publicación.

## Compuertas de release

Una versión del paquete no se considera lista sólo porque `python -m build` termine bien. La secuencia de release también exige:

1. validación del contenido de la distribución;
2. revisión de dependencias;
3. instalaciones limpias fuera del checkout del código fuente;
4. matrices de compatibilidad de Python y sistema operativo;
5. instalación desde TestPyPI por versión exacta;
6. descarga real del dataset con verificaciones de integridad y consulta;
7. nueva prueba en modo estricto sin conexión;
8. aprobación manual del environment `pypi`;
9. instalación desde PyPI después de publicar.

Trusted Publishing subió `arancel-mx==0.2.0` el 2026-08-12. La matriz externa completa de sistemas operativos y versiones de Python del diseño del 2026-08-11 no fue una compuerta bloqueante para esa subida. `0.3.7` trata Ubuntu/Windows/macOS × CPython 3.11, 3.12 y 3.13 como una compuerta de publicación bloqueante después de TestPyPI (`external-certification-matrix` en `publish-python-package.yml`). No se afirma compatibilidad con CPython 3.14 ni con otros modos de instalación (pipx/uv).

## Relacionado

- [Configuración de TestPyPI y PyPI](testpypi-pypi-setup.md)
- [CLI de consumo](consumer-cli.md)
- [Proceso de release](release-process.md)
- [Política de compatibilidad](compatibility.md)
