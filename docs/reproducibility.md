# Reproducibilidad

El proyecto distingue compatibilidad de consumidores de reproducibilidad de producción.

## Dependencias

`pyproject.toml` usa rangos compatibles para no imponer a cada consumidor un entorno idéntico:

```text
duckdb>=1.1
pandas>=2.0
...
```

Los builds oficiales y CI usan `requirements/production-build.txt`, donde el entorno completo está fijado con versiones exactas.

```bash
python -m pip install pip==26.2.1
python -m pip install -c requirements/production-build.txt -e ".[dev]"
```

La regla es:

```text
consumer compatibility -> ranges
production reproducibility -> exact pins
```

## Determinismo lógico

CSV, JSON y DuckDB deben representar los mismos registros lógicos públicos. Los artefactos de texto que forman parte del contrato determinista se comparan por contenido/hash cuando corresponde.

Un archivo físico DuckDB no se declara necesariamente byte-idéntico entre construcciones independientes. Se prueba su contenido lógico y su compatibilidad mínima por separado.

## No-op

Si la identidad registrada de las fuentes no cambió respecto de la última release, el resultado correcto es `no_change`. El pipeline no crea una release diaria redundante.

## Supply chain

Los workflows externos están fijados a SHA completo, la instalación productiva usa pins revisados y los assets publicados se verifican antes y después de la mutación de GitHub Release. Consulta [`release-process.md`](release-process.md) y [`verify-release.md`](verify-release.md).
