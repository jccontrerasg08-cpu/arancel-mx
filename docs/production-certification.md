# Certificación de producción

Este runbook es para quien mantiene el repositorio: documenta el workflow controlado de certificación de producción y la evidencia que se exige antes de considerar sanas sus fronteras de escritura en GitHub. El workflow de certificación está separado a propósito del pipeline oficial de datos arancelarios: nunca debe publicar una release de producción `data-*` ni crear un issue de producción `[DATA ALERT]`.

## Línea base certificada

Las fronteras de escritura de releases e issues se ejercitaron con éxito desde `main` protegida el 2026-08-11 UTC.

| Campo | Valor |
|---|---|
| Workflow | `Production certification` |
| Ejecución | `31450616908` |
| Commit | `a14c57ee3aeeb982e6aa7077ae1b34582585db8b` |
| Conclusión general | `success` |
| `offline` | `success` |
| `release-boundary` | `success` |
| `issue-boundary` | `success` |
| Tag temporal de release | `certification-31450616908` |
| Estado final de la release | ausente |
| Estado final del tag/ref | ausente |
| Issue de certificación | `#28`, `[CERTIFICATION ALERT] 31450616908`, cerrado |
| Release de producción `data-2026.08.10` | sin cambios |

Esta evidencia certifica sólo las fronteras aisladas de escritura en GitHub. No sustituye las compuertas de fuentes oficiales, reconciliación legal, integridad de la release, sello de tiempo ni atestación de artefactos documentadas en otras partes del repositorio.

## Fronteras de seguridad

El workflow es sólo manual (`workflow_dispatch`) y corre desde `main`, que es de confianza.

Sus espacios de nombres están aislados deliberadamente:

```text
Temporary release/tag: certification-<github-run-id>
Certification Issue:   [CERTIFICATION ALERT] <github-run-id>
Production release:    data-YYYY.MM.DD
Production alert:      [DATA ALERT] ...
```

Los helpers de certificación rechazan los espacios de nombres de producción. Una release de certificación permanece como draft/prerelease durante toda su vida y se borra después de la verificación. Un issue de certificación se cierra y se conserva como rastro auditable.

Los permisos se asignan por job:

```text
offline            contents: read
release-boundary   contents: write
issue-boundary     contents: read + issues: write
```

El workflow usa el `github.token` integrado; no requiere un PAT externo.

## Disparo manual

En GitHub:

1. Abre **Actions**.
2. Selecciona **Production certification**.
3. Elige **Run workflow**.
4. Selecciona la rama **main**.
5. Ejecuta el workflow.

No dispares el workflow de mutación real desde una rama de pull request.

Antes de dispararlo, verifica que:

- `main` está protegida;
- el check obligatorio `test` está en verde en el `main` actual;
- ningún `DATA ALERT` de producción abierto es atribuible al `main` actual;
- no existe ya un draft o tag de certificación para la nueva ejecución;
- los permisos del workflow siguen coincidiendo con este runbook.

## Ciclo de vida esperado

La frontera de releases sigue este ciclo:

```text
preflight for existing certification resources
create temporary draft/prerelease
persist exact temporary release ID locally
upload certification-proof.json
verify asset metadata/digest
DELETE the exact draft by release ID
DELETE the temporary certification tag/ref if present
verify release absence by ID and listing
verify tag/ref absence
always-run cleanup repeats the absence check
```

La frontera de issues crea un issue de certificación aislado, lo verifica, registra que terminó y lo cierra. El issue queda cerrado como evidencia de auditoría.

Una ejecución exitosa debe terminar con los tres jobs en verde y con estas poscondiciones:

| Poscondición | Valor esperado |
|---|---|
| Drafts de certificación restantes de la ejecución | 0 |
| Tags/refs de certificación restantes de la ejecución | 0 |
| Issues `[CERTIFICATION ALERT]` cerrados de la ejecución | 1 |
| Tags `data-*` nuevos | 0 |
| Releases de producción modificadas por la certificación | 0 |
| SHA de `main` | sin cambios por la certificación |

Si falla cualquier poscondición de limpieza, detente. Borra sólo el recurso de certificación exacto después de comprobar por separado su ID de ejecución y su espacio de nombres. Nunca borres ni edites una release `data-*` mientras reparas la limpieza de la certificación.

## Revisar la evidencia

Para la línea base certificada, revisa:

```text
Actions → Production certification → run 31450616908
Issues  → #28 [CERTIFICATION ALERT] 31450616908
Releases → confirm no Production certification 31450616908 draft remains
Tags     → confirm certification-31450616908 is absent
```

El log de la frontera de releases debe contener un resultado final equivalente a:

```json
{
  "release_absent": true,
  "status": "passed",
  "tag": "certification-31450616908",
  "tag_absent": true
}
```

El resultado de la frontera de issues debe identificar el issue de certificación con `state: "closed"`.

El smoke de instalación del paquete, `certify_bundle()` sobre el bundle público y los comandos rutinarios de `pytest`/`build` están en [`docs/release-process.md`](release-process.md) y [`docs/package-release.md`](package-release.md). Este runbook cubre sólo las fronteras aisladas de escritura en GitHub.

## Recuperación ante fallas

Si falla una ejecución real de certificación:

1. Lee el log exacto del job antes de cambiar código.
2. Revisa Releases, Tags e Issues por separado en GitHub, porque los endpoints de listado pueden tener consistencia eventual.
3. Identifica el recurso exacto `certification-<run-id>` antes de limpiar.
4. Nunca infieras la pertenencia a partir de un nombre parcial ni borres una release de producción `data-*`.
5. Agrega una prueba en RED que reproduzca la falla real antes de implementar la corrección.
6. Integra la corrección sólo después de que pase la compuerta normal del repositorio.
7. Elimina cualquier huérfano heredado creado por código anterior al estado de limpieza persistido y confiable.
8. Vuelve a ejecutar `Production certification` desde `main` protegida y exige de nuevo todas las poscondiciones.

## Alcance de esta certificación

La ejecución real exitosa demuestra que el repositorio puede ejercitar y revertir con seguridad su frontera aislada de escritura de releases en GitHub, y que puede crear y cerrar un issue aislado con permisos de mínimo privilegio por job.

Por sí sola **no** demuestra:

- que exista una actualización de las fuentes arancelarias oficiales;
- que la reconciliación legal vaya a pasar ante un cambio futuro de fuentes;
- que una release de producción futura vaya a ser inmutable;
- que las atestaciones de artefactos estén configuradas y sean verificables;
- ni que todas las fuentes oficiales externas estén accesibles en este momento.

Ésas son compuertas de producción distintas y deben certificarse por separado.

## Relacionado

- [Proceso de release](release-process.md)
- [Configuración de GitHub](operations/github-settings.md)
- [Arquitectura](architecture.md)
- [Release del paquete de Python](package-release.md)
