<div align="center">

<img src="docs/assets/arancel-mx-banner.svg" alt="arancel.mx - datos arancelarios abiertos de México" width="100%" />

# arancel-mx

## Datos arancelarios de México, verificables y listos para usar

`arancel-mx` convierte publicaciones oficiales de LIGIE/NICO en una capa de datos abierta, reproducible y fácil de consumir desde archivos, DuckDB, CLI, Python o HTTP.

<p>
  <strong>Español</strong> · <a href="./README.en.md">English</a>
</p>

[![CI](https://github.com/jccontrerasg08-cpu/arancel-mx/actions/workflows/ci.yml/badge.svg)](https://github.com/jccontrerasg08-cpu/arancel-mx/actions)
[![Python](https://img.shields.io/badge/python-3.11%2B-blue?logo=python&style=flat-square)](https://www.python.org)
[![License](https://img.shields.io/badge/license-Apache--2.0-blue.svg)](LICENSE)
[![DuckDB](https://img.shields.io/badge/DuckDB-embedded-FFF000?logo=duckdb&logoColor=000)](https://duckdb.org/)

**[Abrir hub](https://arancel-mx.vercel.app/)** · **[API / OpenAPI](https://arancel-mx.vercel.app/docs)** · **[Últimos datos](https://github.com/jccontrerasg08-cpu/arancel-mx/releases/latest)** · **[Documentación](docs/README.md)**

</div>

**Por qué existe.** Los datos arancelarios mexicanos aparecen en fuentes, páginas y documentos con roles distintos. Consumirlos bien exige conservar procedencia, vigencia, jerarquía, evidencia, hashes y una identidad reproducible del dataset. `arancel-mx` concentra ese trabajo para que una aplicación no tenga que reconstruir su propia versión de LIGIE/NICO.

La experiencia interactiva vive en **[arancel-mx.vercel.app](https://arancel-mx.vercel.app/)**. GitHub conserva el código, las releases verificables y la documentación profunda.

## Qué puedes hacer

| Quiero... | Superficie | Empieza aquí |
|---|---|---|
| Buscar una fracción, HS o NICO desde el navegador | **Hub web** | [arancel-mx.vercel.app](https://arancel-mx.vercel.app/) |
| Analizar muchas filas con SQL, BI, notebooks o ETL | **Datos / DuckDB** | `arancel-mx data download` |
| Consultar códigos y fichas rápidamente | **CLI** | `arancel-mx lookup 01012101` |
| Integrar datos en una aplicación | **Python** | `from arancel_mx import Dataset` |
| Consumir una interfaz GET-only/read-only | **HTTP / API** | `GET /v1/meta`, `/v1/search`, `/v1/lookup/...` |
| Comprobar cómo se produjo un resultado | **Auditoría y reproducción** | `manifest.json`, `SHA256SUMS`, `provenance`, `data verify` |

La **API HTTP pública** es **GET-only**, **read-only** y funciona **sin API key**. El contrato interactivo vive en `/docs`; `/readyz` reporta readiness y `/v1/meta` identifica el dataset servido.

El paquete Python y el dataset se versionan por separado. Una versión del paquete no fija los datos: las releases del dataset usan tags inmutables `data-YYYY.MM.DD`.

**Descargas directas:** [DuckDB](https://github.com/jccontrerasg08-cpu/arancel-mx/releases/latest/download/arancel_mx.duckdb) · [CSV](https://github.com/jccontrerasg08-cpu/arancel-mx/releases/latest/download/arancel_mx.csv) · [JSON](https://github.com/jccontrerasg08-cpu/arancel-mx/releases/latest/download/arancel_mx.json) · [Manifest](https://github.com/jccontrerasg08-cpu/arancel-mx/releases/latest/download/manifest.json) · [SHA256SUMS](https://github.com/jccontrerasg08-cpu/arancel-mx/releases/latest/download/SHA256SUMS)

## Empieza en 60 segundos

```bash
pip install arancel-mx
arancel-mx doctor
arancel-mx data download
arancel-mx lookup 01012101
arancel-mx data verify
```

O usa el mismo front door HTTP público:

```bash
curl "https://arancel-mx.vercel.app/v1/meta"
curl "https://arancel-mx.vercel.app/v1/search?q=telefonos&limit=5"
curl "https://arancel-mx.vercel.app/v1/lookup/8517130100"
```

Para formatos, caché, modo offline y selección explícita de dataset, sigue el [inicio rápido](docs/consumer-quickstart.md) y la [referencia CLI](docs/consumer-cli.md).

## Por qué confiar

La confianza no depende de que el README diga “está actualizado”. Cada publicación válida conserva una cadena verificable desde las fuentes observadas hasta los bytes publicados:

```text
fuentes oficiales
      ↓
captura + identidad + SHA256
      ↓
reconciliación y validación
      ↓
DuckDB canónico + CSV + JSON
      ↓
manifest + checksums + fuentes capturadas
      ↓
GitHub Release inmutable
```

<p align="center">
  <img src="docs/assets/pipeline.svg" alt="Pipeline de fuentes oficiales a una release verificable" width="900" />
</p>

El hub de Vercel es una **superficie de consumo**. `/v1/meta` y `/v1/search` usan la capa operacional read-only sincronizada con releases verificadas; el resto de la API pública se presenta bajo el mismo dominio mediante el runtime FastAPI. La **release verificada sigue siendo la fuente de verdad**.

Profundiza en [roles de fuentes oficiales](docs/official-source-roles.md), [fuentes y reconciliación](docs/sources.md), [modelo de datos](docs/data-model.md) y [proceso de release](docs/release-process.md).

## Documentación

| Necesidad | Documento |
|---|---|
| Instalar, descargar y consultar | [Inicio rápido](docs/consumer-quickstart.md) · [CLI](docs/consumer-cli.md) |
| Integrar archivos, Python o HTTP | [Consumo externo](docs/external-consumption.md) |
| Entender HS → fracción MX → NICO | [Guía NICO/LIGIE](docs/nico-ligie-guide.md) |
| Entender procedencia y promoción de fuentes | [Roles oficiales](docs/official-source-roles.md) · [Fuentes](docs/sources.md) · [Promoción SNICE_DOCS](docs/source-promotion.md) |
| Consultar el contexto oficial de comercio exterior sin mezclarlo con la tarifa | [Mapa de cobertura oficial de comercio exterior](docs/research/external-trade-coverage-map.md) |
| Entender el proyecto y sus fronteras | [Visión del proyecto](docs/project-overview.md) |
| Navegar toda la documentación | **[Centro de documentación](docs/README.md)** |

## Alcance

`arancel-mx` es una capa técnica y pública de datos para LIGIE/NICO, procedencia y consumo reproducible. No pretende ser un sistema completo de comercio exterior. **No clasifica mercancías. No constituye asesoría legal.**

El código se distribuye bajo [Apache-2.0](LICENSE). Para colaborar consulta [CONTRIBUTING.md](CONTRIBUTING.md), [SECURITY.md](SECURITY.md), [CODE_OF_CONDUCT.md](CODE_OF_CONDUCT.md) y [TERMS.md](TERMS.md).

**[Hub](https://arancel-mx.vercel.app/)** · **[API](https://arancel-mx.vercel.app/docs)** · **[Releases](https://github.com/jccontrerasg08-cpu/arancel-mx/releases/latest)** · **[Docs](docs/README.md)** · **[English](README.en.md)**
