# Configuración de Trusted Publisher en TestPyPI y PyPI

El workflow [`publish-python-package.yml`](../.github/workflows/publish-python-package.yml) publica el paquete de Python con Trusted Publishing de GitHub Actions (OIDC) y **no** guarda tokens de subida. El repositorio puede demostrar la intención y la estructura del workflow, pero no la configuración de los registros y de los environments, que vive en las interfaces web de PyPI y de GitHub. Esta lista de verificación es para quien mantiene el paquete y se completa una vez, antes de crear el primer tag `pkg-v*`.

## Requisitos previos

1. Crea una cuenta en PyPI y otra, separada, en TestPyPI, ambas con 2FA activado.
2. Confirma que el nombre normalizado del proyecto, `arancel-mx`, está disponible en ambos registros o que ya te pertenece. Usa `scripts/check_package_registry_name.py` si está disponible; si no, revisa `https://pypi.org/project/arancel-mx/` y `https://test.pypi.org/project/arancel-mx/`.
3. Confirma que no existe ningún secreto de larga duración para el paquete: no debe haber `PYPI_TOKEN`, `TEST_PYPI_TOKEN`, `.pypirc` ni una credencial equivalente en los secretos del repositorio, de la organización o de los environments.

## Environments de GitHub

4. Crea un environment de GitHub Actions llamado `testpypi`.
5. Crea un environment de GitHub Actions llamado `pypi`.
6. Agrega al menos un required reviewer (**Required reviewers**) al environment `pypi`, para que la publicación de producción espere una aprobación manual. TestPyPI puede publicar sin reviewer.

## Configuración del Trusted Publisher

7. En TestPyPI, agrega un Trusted Publisher **pending** para este repositorio con:
   - Owner: `jccontrerasg08-cpu`
   - Repository: `arancel-mx`
   - Workflow filename: `publish-python-package.yml`
   - Environment: `testpypi`
8. En PyPI, agrega el mismo Trusted Publisher, pero con el environment `pypi`.

## Invariantes de la release

El workflow y las pruebas hacen cumplir estas reglas:

- Los tags usan la forma `pkg-vX.Y.Z` y deben ser iguales a `project.version` en `pyproject.toml`. Los tags de pre-release usan `pkg-vX.Y.ZrcN`.
- Los tags de pre-release publican sólo en TestPyPI; los tags finales además publican en PyPI después de la aprobación manual.
- La distribución se construye una sola vez y los mismos bytes se suben a ambos registros; los hashes se vuelven a verificar antes de cada subida.
- El workflow nunca crea una GitHub Release. Sólo las releases `data-YYYY.MM.DD` respaldan los enlaces públicos de descarga del dataset.

## Antes del primer tag real

9. Vuelve a verificar el SHA del commit vigente de `pypa/gh-action-pypi-publish` y actualiza el pin si existe una release más nueva y revisada.
10. Confirma que `main` está en verde, fija `project.version` en el valor deseado y crea `pkg-vX.Y.Z` (o `pkg-vX.Y.ZrcN`) en la punta actual de `main`.

Las pruebas del repositorio verifican este documento y la estructura del workflow, pero la publicación real sólo empieza después de que una persona mantenedora complete los pasos de interfaz anteriores.

## Relacionado

- [Release del paquete de Python](package-release.md)
- [Configuración de GitHub](operations/github-settings.md)
- [Proceso de release](release-process.md)
