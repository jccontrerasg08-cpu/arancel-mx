# Fuentes oficiales

`arancel-mx` sólo incorpora al build oficial documentos descubiertos mediante un registro versionado y adaptadores de dominio permitidos. La existencia de un snapshot en una página oficial no basta por sí sola para hacerlo publicable: la identidad, procedencia y reconciliación legal deben superar los gates del pipeline.

## Dominios y funciones

- `diputados.gob.mx`: **registered ledger** de la LIGIE, texto vigente, reformas y documentos asociados.
- `dof.gob.mx`: evidencia DOF de publicación, modificación y vigencia.
- `snice.gob.mx`: libros operativos de LIGIE, NICO, notas, indicadores y publicaciones relacionadas de la Secretaría de Economía.

## Registro versionado

`src/arancel_mx/sources/source_registry.json` define por conjunto la clave, `registry_version`, página canónica, papel de la fuente, autoridad jurídica, autoridad de descubrimiento, fecha efectiva, perfiles esperados y reglas de clasificación.

El registro funciona como allowlist y como parte de la procedencia reproducible. Cambiarlo modifica qué documentos pueden entrar al pipeline y por eso debe llegar como cambio revisable, con tests/fixtures offline.

## Lista permitida y descubrimiento

Los adaptadores aceptan únicamente hosts oficiales registrados. Redirecciones fuera de política, extensiones inesperadas, páginas auxiliares, cero candidatos o múltiples candidatos igualmente válidos fallan cerrados en vez de seleccionar una fuente por heurística débil.

Cada source role tiene expectativas explícitas. Las páginas de propuestas o indicadores pueden servir como contexto/observación, pero no sustituyen automáticamente la evidencia legal aplicable.

## Identidad de captura

Cada descarga conserva como mínimo la URL final, SHA256, tamaño, tipo de medio, procedencia y `retrieved_at`.

`retrieved_at` es la hora real de recuperación HTTP del snapshot, no la hora de generación del dataset. El manifest también contiene `generated_at` para representar la ejecución que produjo el candidato/release; ambos campos son semánticamente distintos.

Un parseo sólo puede reutilizarse cuando la identidad capturada y las versiones relevantes de parser/esquema/registro siguen siendo compatibles.

## Diputados ledger + DOF reconciliation

El ledger **registered** de la Cámara de Diputados es el ancla para saber qué documentos legales deben ser explicables por la construcción. El pipeline realiza **reconciliation** de ese ledger con evidencia del **DOF** y con las fuentes registradas de SNICE.

La reconciliación es un **blocking gate** antes de publicación. Entre otros casos, la construcción queda bloqueada si una entrada legal esperada carece de evidencia DOF suficiente, si las identidades documentales no concuerdan o si existe una **discrepancy** material que no puede explicarse con las reglas registradas.

La prioridad no se resuelve silenciosamente: la publicación jurídica y el texto legal gobiernan la vigencia; los libros operativos aportan estructura utilizable. Una discrepancia se conserva en diagnósticos y bloquea **publication**.

Esto no convierte al repositorio en una fuente de asesoría jurídica. El sistema verifica consistencia entre evidencia observada y reglas registradas; la validez jurídica final depende de las publicaciones oficiales aplicables.

## Cambios y no-op

Después de capturar y reconciliar, la identidad de las fuentes se compara con el último `manifest.json` publicado. Si no cambió, el pipeline devuelve `no_change`, termina en verde y no crea una nueva release. Si cambió, sólo avanza si todos los gates legales, de parser y de validación pasan.

## Evidencia preservada

Una release válida incluye `official-sources.tar.gz`, que conserva los bytes oficiales capturados y `source_capture.json`. Los hashes permiten reconstruir exactamente qué snapshots fueron observados en ese build aunque la página oficial cambie después.

## Fixtures offline

Las pruebas de PR usan fragmentos mínimos y sanitizados en `tests/fixtures/` y no dependen de que DOF, Diputados o SNICE estén disponibles en ese momento. Cada cambio de parser, reconciliación o source registry debe incluir un fixture reproducible o una construcción sintética equivalente.
