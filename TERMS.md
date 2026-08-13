# Términos

El código original de `arancel-mx` se publica bajo la [Apache License 2.0](LICENSE).
El aviso de atribución está en [NOTICE](NOTICE).

Al enviar una contribución aceptas que se publique bajo Apache-2.0 conforme a la sección 5 de la licencia.

## Datos y publicaciones oficiales

Las publicaciones de la Cámara de Diputados, el Diario Oficial de la Federación y SNICE/Secretaría de Economía conservan su propio estatus jurídico. Este repositorio **no** las relicencia como Apache-2.0 ni como dominio público. Los bytes capturados en `official-sources.tar.gz` son evidencia de verificación, no una cesión de derechos de esas autoridades.

`arancel-mx` **no constituye asesoría legal**.

## Dependencias de código abierto

Las dependencias de Python no se copian a este repositorio. Conservan sus propias licencias, declaradas por cada proyecto. El runtime público está en `pyproject.toml` (DuckDB, filelock, requests). El extra `maintainer` añade openpyxl, PyMuPDF y xlrd. No hay conflicto conocido con Apache-2.0.

## Excepciones

Quedan fuera de la licencia Apache-2.0 de este proyecto:

- textos y bytes de autoridades mexicanas citados o archivados para procedencia;
- obras de terceros usadas por dependencia, no vendoreadas en el árbol.

Véanse [LICENSE](LICENSE), [NOTICE](NOTICE), [SECURITY.md](SECURITY.md) y [CONTRIBUTING.md](CONTRIBUTING.md).

## English

Original code is Apache-2.0 ([LICENSE](LICENSE) and [NOTICE](NOTICE)). Contributions are Apache-2.0 under license section 5.

Diputados, DOF (Official Gazette), and SNICE publications keep their own legal status and are not relicensed. `official-sources.tar.gz` is verification evidence, not a rights transfer.

This is not legal advice.

Python dependencies are not vendored; public runtime is in `pyproject.toml`.

Exceptions: Mexican authority texts/bytes, and third-party dependencies.
