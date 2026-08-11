# Primeros pasos

`arancel-mx` publica una capa de datos reproducible y auditable para LIGIE, fracciones arancelarias mexicanas y NICO. Puedes usar los artefactos de datos sin instalar Python, o instalar el proyecto cuando necesites el CLI o desarrollar sobre el pipeline.

> [!IMPORTANT]
> `arancel-mx` es una herramienta técnica y de datos. **No constituye asesoría legal.** Para decisiones de clasificación, cumplimiento, importación o exportación consulta las publicaciones oficiales aplicables.

## Consumir los datos sin instalar

La ruta más corta para un analista es usar una GitHub Release `data-YYYY.MM.DD`. Cada release válida contiene exactamente:

```text
arancel_mx.duckdb
arancel_mx.csv
arancel_mx.json
manifest.json
SHA256SUMS
official-sources.tar.gz
```

Elige CSV para herramientas tabulares, JSON para pipelines/documentos y DuckDB para consultas analíticas locales. Antes de confiar en una descarga, sigue [`verify-release.md`](verify-release.md).

## Instalar el CLI desde un checkout

Mientras el paquete no se publique en PyPI, la ruta soportada desde código fuente es:

```bash
git clone https://github.com/jccontrerasg08-cpu/arancel-mx.git
cd arancel-mx
python -m venv .venv
# macOS/Linux
source .venv/bin/activate
# PowerShell: .\.venv\Scripts\Activate.ps1
python -m pip install .
python -m arancel_mx --help
arancel-mx --help
```

`pip install .` instala las dependencias declaradas para consumidores. El proyecto requiere Python 3.11 o superior.

## Desarrollo reproducible

Para contribuir o reproducir el entorno revisado de CI/producción usa las versiones exactas del constraints file:

```bash
python -m pip install pip==26.2.1
python -m pip install -c requirements/production-build.txt -e ".[dev]"
python -m pytest -q
python -m build
```

La distinción es intencional:

```text
consumidor          -> rangos compatibles en pyproject.toml
CI / producción     -> pins exactos en requirements/production-build.txt
```

## Qué leer después

- [`cli.md`](cli.md): comandos públicos actuales.
- [`dataset.md`](dataset.md): artefactos y formas de consumo.
- [`hs-mx-nico.md`](hs-mx-nico.md): jerarquía HS2 → HS4 → HS6 → MX8 → NICO10.
- [`sources.md`](sources.md): fuentes oficiales y su función.
- [`provenance.md`](provenance.md): trazabilidad documental.
- [`verify-release.md`](verify-release.md): verificación independiente de una release.
- [`../SUPPORT.md`](../SUPPORT.md): cómo pedir soporte o reportar un problema.
