# Verificar una release

La verificación debe poder hacerse como consumidor externo, sin confiar en un checkout editable del repositorio.

## 1. Confirma los seis assets

Una release de datos válida debe contener exactamente:

```text
arancel_mx.duckdb
arancel_mx.csv
arancel_mx.json
manifest.json
SHA256SUMS
official-sources.tar.gz
```

## 2. Verifica SHA256SUMS

En sistemas con `sha256sum`:

```bash
sha256sum -c SHA256SUMS
```

Todos los archivos listados deben validar. Un asset faltante, adicional al contrato, o con digest distinto requiere investigación antes de consumir la release.

## 3. Revisa manifest.json

Comprueba al menos:

```text
schema_version
dataset_version
generated_at
registry_version
registry_sha256
git_commit_sha
github_run_id
github_run_attempt
github_workflow_ref
github_artifact_name
source_identity
reconciliation
```

La reconciliación publicable y la identidad de las fuentes deben corresponder al bundle que estás verificando.

## 4. Abre DuckDB como consumidor

Ejemplo:

```sql
SELECT COUNT(*) FROM arancel_mx;
SELECT level, COUNT(*)
FROM arancel_mx
GROUP BY level
ORDER BY level;
```

Compara una muestra por `record_id` entre DuckDB, CSV y JSON si necesitas una auditoría independiente adicional.

## 5. Revisa las fuentes preservadas

`official-sources.tar.gz` conserva documentos capturados y metadata de captura. Los hashes del archive deben concordar con la identidad registrada en el manifest/capturas.

## 6. Attestations de GitHub

Las releases producidas por el workflow después de integrar la capa A9 pueden incluir provenance verificable mediante GitHub artifact attestations. Para un asset que sí tenga esa attestation:

```bash
gh attestation verify arancel_mx.duckdb \
  --repo jccontrerasg08-cpu/arancel-mx \
  --signer-workflow jccontrerasg08-cpu/arancel-mx/.github/workflows/official-data-pipeline.yml
```

Repite para cada subject publicado. Una attestation demuestra procedencia de build/workflow, no validez jurídica del contenido.

No atribuyas attestations retroactivamente a releases creadas antes de que el mecanismo estuviera integrado.
