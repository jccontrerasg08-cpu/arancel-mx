# Dataset público

Una release válida de `arancel-mx` contiene exactamente seis assets:

```text
arancel_mx.duckdb
arancel_mx.csv
arancel_mx.json
manifest.json
SHA256SUMS
official-sources.tar.gz
```

No cuentes los archivos de source code que GitHub añade automáticamente a cada release.

## Niveles

Los registros canónicos se organizan en:

```text
hs2
hs4
hs6
fraccion8
nico10
```

Las filas descriptivas HS no reciben tarifas heredadas artificialmente. Las tarifas pertenecen a los niveles y periodos donde existe evidencia para ellas.

## CSV

`arancel_mx.csv` es útil para pandas, R, hojas de cálculo y cargas ETL. Los códigos deben tratarse como texto para conservar ceros iniciales.

```python
import pandas as pd

df = pd.read_csv("arancel_mx.csv", dtype={"code": "string"})
print(df.groupby("level").size())
```

## JSON

`arancel_mx.json` representa los mismos registros lógicos públicos y es apropiado para consumidores que prefieren objetos/documentos.

## DuckDB

`arancel_mx.duckdb` es la materialización analítica canónica distribuible. La vista pública `arancel_mx` permite consultas como:

```sql
SELECT level, COUNT(*)
FROM arancel_mx
GROUP BY level
ORDER BY level;
```

El DuckDB público no contiene todo el warehouse operativo. Consulta [`data-model.md`](data-model.md).

## Manifest, checksums y fuentes

- `manifest.json` fija versión, conteos, procedencia y metadata de construcción.
- `SHA256SUMS` permite verificar los otros cinco assets.
- `official-sources.tar.gz` conserva los bytes oficiales capturados y `source_capture.json` para auditoría.

Consulta [`verify-release.md`](verify-release.md) antes de integrar una release en otro sistema.
