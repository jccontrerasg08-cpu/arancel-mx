# Fuentes oficiales

`arancel-mx` sólo incorpora al build oficial documentos descubiertos mediante un registro versionado y adaptadores de dominio permitidos. La existencia de un snapshot en una página oficial no basta por sí sola para hacerlo publicable: la identidad, procedencia y reconciliación legal deben superar los gates del pipeline.

## Dominios y funciones

- `diputados.gob.mx`: **registered ledger** de la LIGIE, texto vigente, reformas y documentos asociados.
- `dof.gob.mx`: evidencia primaria de publicación, modificación y vigencia jurídica aplicable.
- `snice.gob.mx`: datasets estructurados de LIGIE, NICO, notas, indicadores y publicaciones relacionadas de la Secretaría de Economía.
- `ventanillaunica.gob.mx`: **cross-check operativo independiente en caracterización**. VUCEM no forma parte del `source_registry`, no es `authoritative_for_tariff` y no es `publication_gate` durante esta fase.

La separación de funciones es intencional. Una fuente oficial puede ser útil para estructura, descubrimiento o contraste sin convertirse automáticamente en la autoridad jurídica o arancelaria para todos los campos.

## Registro versionado

`src/arancel_mx/sources/source_registry.json` define por conjunto la clave, `registry_version`, página canónica, papel de la fuente, autoridad jurídica, autoridad de descubrimiento, perfiles esperados y reglas de clasificación.

El registro funciona como allowlist y como parte de la procedencia reproducible. Cambiarlo modifica qué documentos pueden entrar al pipeline y por eso debe llegar como cambio revisable, con tests/fixtures offline.

VUCEM **no se añade al registro por existir un patrón de URL utilizable**. Antes de cualquier propuesta de incorporación debe completarse una caracterización separada de 100+ fracciones, revisar cobertura, variantes de estructura, correspondencia con el dataset canónico y evidencia de update lag. Consulta [`vucem-characterization.md`](vucem-characterization.md).

## Lista permitida y descubrimiento

Los adaptadores productivos aceptan únicamente hosts oficiales registrados. Redirecciones fuera de política, extensiones inesperadas, páginas auxiliares, cero candidatos o múltiples candidatos igualmente válidos fallan cerrados en vez de seleccionar una fuente por heurística débil.

Cada source role tiene expectativas explícitas. Las páginas de propuestas o indicadores pueden servir como contexto/observación, pero no sustituyen automáticamente la evidencia legal aplicable.

La herramienta de caracterización VUCEM usa su propio boundary de investigación y no alimenta el build oficial. Sus resultados se consideran diagnósticos hasta que una propuesta futura, separada y revisada cambie explícitamente ese contrato.

## Identidad de captura

Cada descarga del pipeline oficial conserva como mínimo la URL final, SHA256, tamaño, tipo de medio, procedencia y `retrieved_at`.

`retrieved_at` es la hora real de recuperación HTTP del snapshot, no la hora de generación del dataset ni una fecha jurídica de entrada en vigor. El manifest también contiene `generated_at` para representar la ejecución que produjo el candidato/release; ambos campos son semánticamente distintos.

Un parseo sólo puede reutilizarse cuando la identidad capturada y las versiones relevantes de parser/esquema/registro siguen siendo compatibles.

## Diputados ledger + DOF reconciliation

El ledger **registered** de la Cámara de Diputados es el ancla para saber qué documentos legales deben ser explicables por la construcción. El pipeline realiza **reconciliation** de ese ledger con evidencia del **DOF** y con las fuentes registradas de SNICE.

La reconciliación es un **blocking gate** antes de publicación. Entre otros casos, la construcción queda bloqueada si una entrada legal esperada carece de evidencia DOF suficiente, si las identidades documentales no concuerdan o si existe una **discrepancy** material que no puede explicarse con las reglas registradas.

La prioridad no se resuelve silenciosamente: la publicación jurídica y el texto legal gobiernan la vigencia; los datasets operativos aportan estructura utilizable. Una discrepancia se conserva en diagnósticos y bloquea **publication**.

Esto no convierte al repositorio en una fuente de asesoría jurídica. El sistema verifica consistencia entre evidencia observada y reglas registradas; la validez jurídica final depende de las publicaciones oficiales aplicables.

## VUCEM como cross-check pre-registry

El Clasificador Arancelario de VUCEM se estudia mediante `scripts/characterize_vucem.py` usando el patrón conocido de páginas individuales. El reporte conserva explícitamente:

```text
source_role = independent_operational_cross_check
authoritative_for_tariff = false
publication_gate = false
```

La muestra se toma de filas `fraccion8` del CSV canónico y se distribuye entre capítulos. La herramienta registra cobertura, errores, presencia de código, correspondencia descriptiva y `schema_fingerprint` de la estructura HTML.

`registry_review_ready=true` sólo indica que existen al menos 100 recuperaciones exitosas para iniciar revisión humana. **No habilita por sí mismo una entrada en `source_registry` ni cambia la jerarquía de autoridad.** El update lag requiere observaciones repetidas alrededor de cambios reales confirmados por las fuentes registradas.

## Cambios y no-op

Después de capturar y reconciliar las fuentes productivas, su identidad se compara con el último `manifest.json` publicado. Si no cambió, el pipeline devuelve `no_change`, termina en verde y no crea una nueva release. Si cambió, sólo avanza si todos los gates legales, de parser y de validación pasan.

Los cambios observados exclusivamente por la caracterización VUCEM no alteran este resultado durante la fase pre-registry.

## Evidencia preservada

Una release válida incluye `official-sources.tar.gz`, que conserva los bytes oficiales capturados y `source_capture.json`. Los hashes permiten reconstruir exactamente qué snapshots fueron observados en ese build aunque la página oficial cambie después.

Los reportes de caracterización VUCEM son artefactos de investigación separados y no se incluyen automáticamente en el contrato de seis assets de una release productiva.

## Fixtures offline

Las pruebas de PR usan fragmentos mínimos y sanitizados en `tests/fixtures/` y no dependen de que DOF, Diputados, SNICE o VUCEM estén disponibles en ese momento. Cada cambio de parser, reconciliación o source registry debe incluir un fixture reproducible o una construcción sintética equivalente.
