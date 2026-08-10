# Proceso de publicación

`arancel-mx` usa un pipeline autónomo y fail-closed para construir y publicar snapshots oficiales. El workflow de producción es **Official data pipeline**, definido en [`.github/workflows/official-data-pipeline.yml`](../.github/workflows/official-data-pipeline.yml), y corre diariamente con cron `17 11 * * *` además de admitir `workflow_dispatch`.

> La publicación automatizada sólo debe activarse en producción después de habilitar release immutability y las protecciones de `main`. El modo manual `workflow_dispatch` usa `publish=false` por defecto para permitir un dry-run sin mutaciones.

## 1. Tests y entorno reproducible

Antes de acceder a fuentes externas, el job `build-and-verify` instala el entorno con `requirements/production-build.txt` y ejecuta `python -m pytest -q`. El check estable para merges es `CI / test`.

La compatibilidad pública del paquete sigue declarada en `pyproject.toml`; el build oficial, en cambio, usa versiones exactas para que una ejecución programada no cambie silenciosamente de dependencias.

## 2. Captura de fuentes oficiales

La construcción end-to-end de dataset oficial puede ejecutarse con `scripts/build_official_dataset.py`; el workflow de producción usa `scripts/run_official_pipeline.py` para añadir comparación con la release anterior y diagnósticos estructurados.

Cada snapshot registrado se descarga y se conserva con identidad de fuente, SHA256 y `retrieved_at`. **`retrieved_at` significa actual fetch time**, es decir, la hora real de la captura HTTP. No se sustituye por `generated_at`.

`generated_at` identifica cuándo se generó el candidato/release. Ambos tiempos se conservan por separado para evitar atribuir al documento una hora de recuperación que no tuvo.

## 3. Reconciliación legal como gate

El ledger registrado de la Cámara de Diputados se reconcilia contra evidencia DOF y las fuentes operativas registradas de SNICE antes de publicar. Una discrepancia legal, evidencia DOF faltante, ambigüedad de snapshot, fallo de parser, checksum inconsistente o validación inválida bloquea el pipeline.

La reconciliación no convierte una observación técnica en una opinión jurídica. El proyecto conserva evidencia y detecta inconsistencias; **no constituye asesoría legal**.

## 4. Parseo, normalización y validación

Los bytes capturados se procesan con parsers offline. El candidato se materializa en DuckDB y se valida antes de exportar. Entre los gates se encuentran:

- jerarquía HS2 → HS4 → HS6 → fracción8 → NICO10;
- ausencia de duplicados y padres faltantes;
- intervalos temporales coherentes;
- tarifas y metadatos públicos válidos;
- procedencia completa;
- reconciliación legal publicable.

Si cualquiera de estos gates falla, no existe camino hacia el job publisher.

## 5. `no_change` y detección de cambios

El pipeline descarga el `manifest.json` de la última release válida y compara la identidad registrada de las fuentes.

- Si la identidad no cambió, el resultado es `no_change`: la ejecución termina en verde, el publisher queda `skipped` y no se crea tag ni release.
- Si hubo un cambio y todos los gates pasan, el resultado es `built`: se genera el bundle verificado y puede continuar a publicación.
- Si falla cualquier gate, el resultado es `failed`: publicación bloqueada y diagnóstico disponible para el notifier.

## 6. Manifest schema v2 y procedencia

`manifest.json` usa `schema_version: "2"`, también referido como **schema v2**. Además de versión, conteos, hashes y fuentes, el manifest conserva procedencia de la ejecución, incluyendo commit, registry y GitHub Actions.

Campos relevantes incluyen `generated_at`, `registry_version`, `registry_sha256`, `git_commit_sha`, `github_run_id`, `github_run_attempt`, `github_workflow_ref` y `github_artifact_name`.

## 7. Contrato exacto de publicación

Una construcción válida produce exactamente **six assets** públicos:

```text
release/
├── arancel_mx.duckdb
├── arancel_mx.csv
├── arancel_mx.json
├── manifest.json
├── SHA256SUMS
└── official-sources.tar.gz
```

Los cinco archivos distintos de `SHA256SUMS` deben estar cubiertos por checksums. `official-sources.tar.gz` conserva los snapshots capturados y `source_capture.json` necesarios para auditar el build.

Antes de cualquier mutación de GitHub Release, `verify_publication_bundle()` exige que el directorio contenga exactamente los six assets, valida manifest/schema/procedencia y vuelve a comprobar hashes.

## 8. Publicación automática e immutable release

El job `publish` sólo puede ejecutarse cuando:

1. `build-and-verify` terminó con éxito;
2. su output es exactamente `built`;
3. el ref es `refs/heads/main`;
4. la ejecución es programada o un `workflow_dispatch` confiable usa `publish=true`.

El publisher descarga por nombre exacto el artifact `arancel-mx-${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}`, ejecuta de nuevo `verify_publication_bundle()` y crea una GitHub Release en estado **draft** para el tag `data-YYYY.MM.DD`.

Los six assets se suben al draft y se verifican remotamente por tamaño y digest cuando GitHub provee digest; si no, se descargan de nuevo y se recalcula SHA256. Sólo entonces el draft se hace público. Después de publicar, la release se vuelve a consultar y verificar.

La política es **immutable**: nunca se sobrescribe un tag o release existente.

### Same-date second change

Si ocurre un segundo cambio válido el mismo día y ya existe `data-YYYY.MM.DD`, el sistema no sobreescribe esa identidad. Falla con categoría `release_tag_collision`. Este **same-date** collision bloquea publicación y se trata como alerta operativa.

## 9. Fallos, GitHub Issue y recovery

Los pasos principales escriben JSON de diagnóstico antes de devolver un código distinto de cero. El workflow extrae mensajes acotados y sin secretos, y luego falla explícitamente el job.

El job `notify` es el único con `issues: write`:

- build fallido: crea o actualiza un **GitHub Issue** determinista por stage + failure category;
- publish fallido: crea o actualiza el GitHub Issue correspondiente;
- ejecución posterior saludable: ejecuta **recovery**, comenta y cierra las alertas generadas por la automatización;
- `no_change` + publisher `skipped` cuenta explícitamente como recovery saludable.

Los Issues del usuario sin el marcador oculto de automatización nunca se cierran mediante recovery.

## 10. Límites de permisos

El workflow tiene `contents: read` globalmente. El job de build permanece read-only; sólo `publish` recibe `contents: write`; sólo `notify` recibe `issues: write`. No se usa PAT, `write-all` ni `pull_request_target`.

Los binarios, bases DuckDB, snapshots oficiales y bundles de release no se escriben al historial Git.

## Compatibilidad y workflow retirado

`scripts/build_official_dataset.py` permanece como entrypoint público de construcción. El workflow anterior `.github/workflows/build-official-dataset.yml` está retirado y fue reemplazado por `.github/workflows/official-data-pipeline.yml`; no debe volver a programarse en paralelo.
