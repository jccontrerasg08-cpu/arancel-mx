# Certificación de producción

Este runbook documenta el workflow controlado de certificación de producción del repositorio y la evidencia requerida antes de considerar saludables sus límites de escritura en GitHub.

> El workflow de certificación está separado deliberadamente del pipeline oficial de datos arancelarios. Nunca debe publicar una release productiva `data-*` ni crear un Issue productivo `[DATA ALERT]`.

## Baseline live certificado

Los límites de escritura de Releases e Issues se ejercieron correctamente desde `main` protegido el 2026-08-11 UTC.

- Workflow: `Production certification`
- Run: `31450616908`
- Commit: `a14c57ee3aeeb982e6aa7077ae1b34582585db8b`
- Conclusión general: `success`
- `offline`: `success`
- `release-boundary`: `success`
- `issue-boundary`: `success`
- Tag temporal: `certification-31450616908`
- Estado final de release: ausente
- Estado final de tag/ref: ausente
- Issue de certificación: `#28`, `[CERTIFICATION ALERT] 31450616908`, cerrado
- Release productiva `data-2026.08.10`: sin cambios

Esta evidencia certifica únicamente los límites aislados de escritura en GitHub. No sustituye los gates de fuentes oficiales, reconciliación legal, integridad de release, timestamps o artifact attestations documentados en otras partes del repositorio.

## Límites de seguridad

El workflow es sólo manual (`workflow_dispatch`) y se ejecuta desde `main` confiable.

Sus namespaces están aislados deliberadamente:

```text
Release/tag temporal: certification-<github-run-id>
Issue de certificación: [CERTIFICATION ALERT] <github-run-id>
Release productiva:     data-YYYY.MM.DD
Alerta productiva:      [DATA ALERT] ...
```

Los helpers de certificación rechazan namespaces productivos. Una release de certificación permanece draft/prerelease durante toda su vida y se elimina después de verificarla. El Issue de certificación se cierra y se conserva como evidencia auditable.

Los permisos son por job:

```text
offline            contents: read
release-boundary   contents: write
issue-boundary     contents: read + issues: write
```

El workflow usa `github.token`; no requiere PAT externo.

## Ejecución manual

En GitHub:

1. Abre **Actions**.
2. Selecciona **Production certification**.
3. Elige **Run workflow**.
4. Selecciona la rama **main**.
5. Ejecuta el workflow.

No ejecutes el workflow de mutación live desde una rama de pull request.

Antes de ejecutarlo, verifica:

```text
main está protegido
el required check `test` está verde en main actual
no existe un DATA ALERT productivo abierto atribuible al main actual
no existe un draft/tag de certificación para el nuevo run
los permisos del workflow siguen coincidiendo con este runbook
```

## Ciclo esperado de una ejecución exitosa

El límite de release ejecuta:

```text
preflight de recursos de certificación existentes
crear draft/prerelease temporal
persistir localmente el release ID exacto
subir certification-proof.json
verificar metadata/digest del asset
DELETE del draft exacto por release ID
DELETE del tag/ref temporal si existe
verificar ausencia de release por ID y listado
verificar ausencia de tag/ref
cleanup always-run repite la comprobación de ausencia
```

El límite de Issues crea un Issue aislado de certificación, lo verifica, registra finalización y lo cierra. El Issue cerrado permanece como evidencia auditable.

Un run exitoso debe terminar con los tres jobs verdes y estas postcondiciones:

```text
0 drafts de certificación restantes para el run
0 tags/refs de certificación restantes para el run
1 [CERTIFICATION ALERT] cerrado para el run
0 tags data-* nuevos
0 releases productivas modificadas por certificación
SHA de main sin cambios por certificación
```

Si falla alguna postcondición de cleanup, detente. Elimina únicamente el recurso de certificación exacto después de comprobar independientemente su run ID y namespace. Nunca elimines ni edites una release `data-*` al reparar cleanup de certificación.

## Inspección de evidencia

Para el baseline certificado revisa:

```text
Actions  → Production certification → run 31450616908
Issues   → #28 [CERTIFICATION ALERT] 31450616908
Releases → confirmar que no queda draft Production certification 31450616908
Tags     → confirmar que certification-31450616908 está ausente
```

El log de `release-boundary` debe contener un resultado final equivalente a:

```json
{
  "release_absent": true,
  "status": "passed",
  "tag": "certification-31450616908",
  "tag_absent": true
}
```

El resultado de `issue-boundary` debe identificar el Issue de certificación con `state: "closed"`.

## Certificación smoke de artefactos del paquete

Primero construye las distribuciones:

```bash
python -m build
```

Después prueba ambos artefactos en virtualenvs aislados fuera del checkout:

```bash
python scripts/certify_package_install.py dist/*.whl
python scripts/certify_package_install.py dist/*.tar.gz
```

Cada instalación limpia verifica:

```text
import arancel_mx
python -m arancel_mx --help
arancel-mx --help
packaged sources/source_registry.json is present
```

CI y el workflow manual de certificación ejecutan el mismo límite smoke para wheel y sdist.

## Verificación del bundle público

Un bundle público sólo es válido cuando contiene exactamente:

```text
arancel_mx.duckdb
arancel_mx.csv
arancel_mx.json
manifest.json
SHA256SUMS
official-sources.tar.gz
```

La capa independiente de certificación valida el conjunto exacto de assets, checksums, seguridad e identidades del source archive y equivalencia lógica CSV/JSON. DuckDB tiene su propio contrato de consumidor y probe de versión mínima.

Para el límite documentado de compatibilidad mínima de DuckDB:

```bash
python scripts/check_duckdb_compat.py out/release/arancel_mx.duckdb
```

CI ejecuta adicionalmente este probe dentro de un entorno aislado con DuckDB `1.1.0`.

## Comandos rutinarios de verificación

Antes de integrar cambios de certificación:

```bash
python -m pytest -q
python -m build
git diff --check
```

Un PR que modifique certificación también debe demostrar que parte del `main` protegido actual, que los supuestos cambiantes de API/Actions se verificaron contra documentación oficial, que se conservan permisos mínimos, que Actions siguen fijadas por SHA completo, que no se versionaron credenciales ni datasets productivos generados, que cleanup es fail-closed y que cualquier mutación live sólo ocurre después de merge desde `main` confiable.

## Recuperación ante fallos

Si un run live de certificación falla:

1. Lee el log exacto del job antes de modificar código.
2. Revisa Releases, Tags e Issues independientemente en GitHub.
3. Identifica el recurso exacto `certification-<run-id>` antes de cleanup.
4. Nunca infieras propiedad por un nombre parcial ni elimines una release productiva `data-*`.
5. Agrega un test RED que reproduzca el fallo live antes de implementar el fix.
6. Integra el fix sólo después de que pase el gate normal del repositorio.
7. Elimina cualquier huérfano legacy creado antes de que existiera estado persistente de cleanup confiable.
8. Repite `Production certification` desde `main` protegido y exige de nuevo todas las postcondiciones.

## Alcance de esta certificación

El run live exitoso demuestra que el repositorio puede ejercer y revertir de forma segura su límite aislado de escritura de GitHub Release y puede crear/cerrar un Issue aislado con permisos mínimos por job.

Por sí solo **no demuestra** que exista una actualización oficial arancelaria, que una reconciliación legal futura vaya a pasar, que una futura release productiva vaya a ser inmutable, que una futura artifact attestation vaya a verificarse o que todas las fuentes oficiales externas estén accesibles en este momento.

Esos siguen siendo gates productivos separados.
