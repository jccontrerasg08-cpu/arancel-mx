# Proceso de publicación

`arancel-mx` usa un pipeline autónomo y fail-closed para construir y publicar snapshots oficiales. El workflow de producción es **Official data pipeline**, definido en [`.github/workflows/official-data-pipeline.yml`](../.github/workflows/official-data-pipeline.yml), y corre diariamente con cron `17 11 * * *` además de admitir `workflow_dispatch`.

Las ejecuciones que pueden mutar (cron y `publish=true`) comparten un único grupo de concurrency y nunca se solapan. Los dry runs usan un grupo propio por ref: GitHub mantiene una sola ejecución pendiente por grupo y cancela la anterior, así que compartir el grupo permitiría que un dry run manual desplazara en silencio una ejecución de producción encolada.

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

`SHA256SUMS` cubre los otros cinco assets. `official-sources.tar.gz` conserva los snapshots capturados y `source_capture.json` necesarios para auditar el build. GitHub también ofrece **Source code** (zip/tar.gz) y **Release attestation (json)**; esos archivos **no** forman parte del contrato de seis assets.

Antes de cualquier mutación de GitHub Release, `certify_bundle()` exige que el directorio contenga exactamente los six assets, valida manifest/schema/procedencia, abre el DuckDB público, comprueba el archive de fuentes (incluido el ledger Diputados) y vuelve a comprobar hashes.

### Artifact attestation

Cuando un build cambiado y validado entra realmente al job `publish`, GitHub Actions crea una sola **artifact attestation** de provenance SLSA sobre esos mismos seis archivos públicos. El paso usa la acción first-party `actions/attest`, autenticación OIDC de GitHub y sólo se ejecuta después de que `certify_bundle()` haya aceptado el artifact descargado.

Antes de ejecutar el publisher, cada subject se verifica contra este repositorio y contra el workflow firmante exacto:

```bash
gh attestation verify arancel_mx.duckdb \
  --repo jccontrerasg08-cpu/arancel-mx \
  --signer-workflow jccontrerasg08-cpu/arancel-mx/.github/workflows/official-data-pipeline.yml
```

Se aplica la misma forma de `gh attestation verify` a `arancel_mx.csv`, `arancel_mx.json`, `manifest.json`, `SHA256SUMS` y `official-sources.tar.gz`.

Las tres capas responden preguntas diferentes:

- `SHA256SUMS` comprueba consistencia local de digest de los archivos de release que cubre.
- `manifest.json` registra procedencia del dataset, fuentes, registry, validación y ejecución dentro del contrato de release.
- GitHub artifact attestation enlaza criptográficamente los digests de los subjects con la identidad del workflow de GitHub Actions que los produjo y autorizó para publicación.

La artifact attestation **is not a legal signature** sobre los documentos oficiales mexicanos. No sustituye evidencia DOF/Diputados, la procedencia de las fuentes ni la reconciliación legal bloqueante del repositorio.

Estado de A9 mientras no exista una publicación legítima posterior a su integración con verificación independiente de los seis subjects: **implemented / CI-verified; live attestation verification pending the next legitimate changed release**. La release `data-2026.08.11` fue creada antes de A9 y no constituye evidencia retroactiva de attestation.

## 8. Publicación automática e immutable release

El job `publish` sólo puede ejecutarse cuando:

1. `build-and-verify` terminó con éxito;
2. su output es exactamente `built`;
3. el ref es `refs/heads/main`;
4. la ejecución es programada o un `workflow_dispatch` confiable usa `publish=true`.

El publisher descarga por nombre exacto el artifact que el build registró (`github_artifact_name` del manifest, con la forma `arancel-mx-<run_id>-<run_attempt>` del intento que lo produjo), ejecuta de nuevo `certify_bundle()`, genera y verifica la attestation de los seis assets, y sólo entonces crea una GitHub Release en estado **draft** para el tag `data-YYYY.MM.DD`.

Ambos extremos del handoff usan el nombre registrado, no `github.run_attempt`: al re-ejecutar sólo el job fallido, `build-and-verify` no vuelve a subir el artifact, así que derivar el nombre del número de intento haría fallar la descarga y obligaría a repetir el build completo.

Los six assets se suben al draft y se verifican remotamente por tamaño y digest cuando GitHub provee digest; si no, se descargan de nuevo y se recalcula SHA256. Sólo entonces el draft se hace público. Después de publicar, la release se vuelve a consultar y verificar.

La política es **immutable**: nunca se sobrescribe un tag o release existente.

### Same-date second change

Si ocurre un segundo cambio válido el mismo día y ya existe `data-YYYY.MM.DD`, el sistema no sobreescribe esa identidad. Falla con categoría `release_tag_collision`. Este **same-date** collision bloquea publicación y se trata como alerta operativa.

## 9. Fallos, GitHub Issue y recovery

**Cualquier falla bloquea la publicación.** Los pasos principales escriben JSON de diagnóstico antes de devolver un código distinto de cero. El workflow extrae mensajes acotados y sin secretos, y luego falla explícitamente el job.

Esa extracción es una frontera de confianza: los outputs del job `build-and-verify` deciden si `publish` puede ejecutarse. `scripts/workflow_diagnostics.py` es el único código autorizado a escribir outputs del workflow. Valida `status` contra un vocabulario cerrado (`built`, `no_change`, `failed`), acota cada token y mensaje a una sola línea, y rechaza escribir cualquier línea si un valor no es seguro. Un `status` desconocido nunca se propaga: se degrada a `failed` con categoría `invalid_diagnostics`.

El job `notify` es el único con `issues: write`:

- build fallido o cancelado: crea o actualiza un **GitHub Issue** determinista por stage + failure category;
- publish fallido o cancelado, incluida una falla al crear o verificar la attestation: crea o actualiza el GitHub Issue correspondiente;
- ejecución posterior saludable: ejecuta **recovery**, comenta y cierra las alertas generadas por la automatización;
- `no_change` + publisher `skipped` cuenta explícitamente como recovery saludable.

Los Issues del usuario sin el marcador oculto de automatización nunca se cierran mediante recovery.

## 10. Límites de permisos

El workflow tiene `contents: read` globalmente. El job de build permanece read-only. Sólo `publish` recibe `contents: write`; para A9 ese mismo job recibe además `attestations: write` e `id-token: write`. Sólo `notify` recibe `issues: write`. No se usa PAT, `write-all`, `artifact-metadata: write` ni `pull_request_target`.

Ningún job de este workflow conserva la credencial de checkout: los tres usan `persist-credentials: false` y llegan a GitHub mediante variables de entorno de token explícitas. El job de build es el único que instala `.[dev]`, porque es el único que ejecuta la suite; `publish` y `notify` instalan sólo el runtime, de modo que el job que firma la attestation no carga herramientas de desarrollo.

Los invariantes estructurales de todos los workflows (acciones fijadas por SHA, escrituras siempre dentro de un job, permisos y timeout por job, credenciales de checkout explícitas, y ausencia de interpolación `${{ ... }}` dentro de scripts de shell) se verifican offline en `tests/test_workflow_hardening.py`.

Los binarios, bases DuckDB, snapshots oficiales y bundles de release no se escriben al historial Git.

## Compatibilidad del entrypoint

`scripts/build_official_dataset.py` permanece como entrypoint público de construcción. La automatización de producción vive únicamente en `.github/workflows/official-data-pipeline.yml`, por lo que no hay dos schedules de dataset ejecutándose en paralelo.

El canario [`.github/workflows/published-bundle-canary.yml`](../.github/workflows/published-bundle-canary.yml) (`47 12 * * *`) instala el paquete runtime (`-e .`, sin extras) y corre `arancel-mx data download` más `arancel-mx data verify --bundle` contra la última release pública. No captura fuentes, no publica, y no es un segundo pipeline de dataset.
