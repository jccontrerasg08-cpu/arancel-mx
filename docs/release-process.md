# Proceso de publicación

`arancel-mx` usa un pipeline autónomo y fail-closed para construir y publicar snapshots oficiales. El workflow de producción es **Official data pipeline**, definido en [`.github/workflows/official-data-pipeline.yml`](https://github.com/jccontrerasg08-cpu/arancel-mx/blob/main/.github/workflows/official-data-pipeline.yml), y corre diariamente con cron `17 11 * * *` además de admitir `workflow_dispatch`.

> La publicación automatizada sólo debe activarse en producción después de habilitar release immutability y las protecciones de `main`. El modo manual `workflow_dispatch` usa `publish=false` por defecto para permitir un dry-run sin mutaciones.

## 1. Tests y entorno reproducible

Antes de acceder a fuentes externas, `build-and-verify` instala el entorno con `requirements/production-build.txt` y ejecuta `python -m pytest -q`. El check estable para merges es `CI / test`.

La compatibilidad pública del paquete sigue declarada en `pyproject.toml`; el build oficial usa versiones exactas para que una ejecución programada no cambie silenciosamente de dependencias.

## 2. Captura de fuentes oficiales

La construcción end-to-end puede ejecutarse con `scripts/build_official_dataset.py`; producción usa `scripts/run_official_pipeline.py` para añadir comparación contra la release anterior y diagnósticos estructurados.

Cada snapshot registrado conserva identidad de fuente, SHA256 y `retrieved_at`. **`retrieved_at` significa actual fetch time**, es decir, la hora real de captura HTTP. `generated_at` identifica cuándo se generó el candidato/release. Ambos tiempos se conservan por separado.

## 3. Reconciliación legal como gate

El ledger registrado de la Cámara de Diputados se reconcilia contra evidencia DOF y fuentes operativas registradas de SNICE antes de publicar. Una discrepancia legal, evidencia DOF faltante, ambigüedad de snapshot, fallo de parser, checksum inconsistente o validación inválida bloquea el pipeline.

La reconciliación conserva evidencia y detecta inconsistencias; **no constituye asesoría legal**.

## 4. Parseo, normalización y validación

Los bytes capturados se procesan con parsers offline. El candidato se materializa en DuckDB y se valida antes de exportar. Los gates incluyen:

- jerarquía HS2 → HS4 → HS6 → fracción8 → NICO10;
- ausencia de duplicados y padres faltantes;
- intervalos temporales coherentes;
- tarifas y metadatos públicos válidos;
- procedencia completa;
- reconciliación legal publicable.

Si cualquiera falla, no existe camino hacia el job publisher.

## 5. `no_change` y detección de cambios

El pipeline descarga el `manifest.json` de la última release válida y compara la identidad registrada de las fuentes.

- Sin cambios: `no_change`, ejecución verde, publisher `skipped`, sin tag ni release.
- Cambio con todos los gates verdes: `built`, se genera el bundle verificado.
- Cualquier gate fallido: `failed`, publicación bloqueada y diagnóstico disponible para el notifier.

## 6. Manifest schema v2 y procedencia

`manifest.json` usa `schema_version: "2"`, también llamado **schema v2**. Conserva versión, conteos, hashes, fuentes y procedencia de ejecución.

Campos relevantes:

```text
generated_at
registry_version
registry_sha256
git_commit_sha
github_run_id
github_run_attempt
github_workflow_ref
github_artifact_name
```

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

Los cinco archivos distintos de `SHA256SUMS` deben estar cubiertos por checksums. `official-sources.tar.gz` conserva snapshots y `source_capture.json` necesarios para auditar el build.

Antes de cualquier mutación de GitHub Release, `verify_publication_bundle()` exige exactamente los six assets y valida manifest/schema/procedencia y hashes.

### Artifact attestation

Cuando un build cambiado y validado entra realmente a `publish`, GitHub Actions crea una **artifact attestation** de provenance SLSA sobre esos seis archivos usando `actions/attest` y OIDC.

Antes de ejecutar el publisher, cada subject se verifica contra el repositorio y el workflow firmante exacto:

```bash
gh attestation verify arancel_mx.duckdb \
  --repo jccontrerasg08-cpu/arancel-mx \
  --signer-workflow jccontrerasg08-cpu/arancel-mx/.github/workflows/official-data-pipeline.yml
```

La misma forma de `gh attestation verify` se aplica a `arancel_mx.csv`, `arancel_mx.json`, `manifest.json`, `SHA256SUMS` y `official-sources.tar.gz`.

Las capas responden preguntas distintas:

- `SHA256SUMS` comprueba digests locales de los archivos de release.
- `manifest.json` registra procedencia del dataset, fuentes, registry, validación y ejecución.
- La artifact attestation enlaza criptográficamente los digests con la identidad del workflow de GitHub Actions.

La artifact attestation **is not a legal signature** sobre documentos oficiales mexicanos. No sustituye evidencia DOF/Diputados, procedencia de fuentes ni reconciliación legal bloqueante.

Estado A9 hasta que exista una publicación legítima posterior con verificación independiente: **implemented / CI-verified; live attestation verification pending the next legitimate changed release**. `data-2026.08.11` fue creada antes de A9 y no es evidencia retroactiva.

## 8. Publicación automática e immutable release

`publish` sólo puede ejecutarse cuando:

1. `build-and-verify` terminó con éxito;
2. su output es `built`;
3. el ref es `refs/heads/main`;
4. la ejecución es programada o `workflow_dispatch` confiable usa `publish=true`.

El publisher descarga el artifact exacto `arancel-mx-${GITHUB_RUN_ID}-${GITHUB_RUN_ATTEMPT}`, ejecuta de nuevo `verify_publication_bundle()`, genera/verifica la attestation de los six assets y sólo entonces crea una GitHub Release **draft** para `data-YYYY.MM.DD`.

Los assets del draft se verifican remotamente por tamaño y digest cuando GitHub lo provee; en caso contrario se descargan otra vez y se recalcula SHA256. Sólo después el draft se hace público y se vuelve a consultar.

La política es **immutable**: nunca se sobrescribe un tag o release existente.

### Same-date second change

Si ocurre un segundo cambio válido el mismo día y ya existe `data-YYYY.MM.DD`, el sistema falla con `release_tag_collision`. Este **same-date** collision bloquea publicación y genera una alerta operativa.

## 9. Fallos, GitHub Issue y recovery

**Cualquier falla bloquea la publicación.** Los pasos principales escriben JSON de diagnóstico acotado antes de devolver código distinto de cero.

`notify` es el único job con `issues: write`:

- build fallido: crea o actualiza un **GitHub Issue** determinista por stage + failure category;
- publish fallido, incluida falla de attestation: crea o actualiza el Issue correspondiente;
- ejecución posterior saludable: ejecuta **recovery**, comenta y cierra alertas de automatización;
- `no_change` + publisher `skipped` cuenta explícitamente como recovery saludable.

Issues del usuario sin el marcador oculto de automatización nunca se cierran mediante recovery.

## 10. Límites de permisos

El workflow tiene `contents: read` globalmente. Build permanece read-only. Sólo `publish` recibe `contents: write`; A9 añade en ese job `attestations: write` e `id-token: write`. Sólo `notify` recibe `issues: write`. No se usa PAT, `write-all`, `artifact-metadata: write` ni `pull_request_target`.

Los binarios, bases DuckDB, snapshots y bundles de release no se escriben al historial Git.

## Compatibilidad del entrypoint

`scripts/build_official_dataset.py` permanece como entrypoint público. La automatización productiva vive únicamente en `.github/workflows/official-data-pipeline.yml`, evitando schedules paralelos para el mismo dataset.
