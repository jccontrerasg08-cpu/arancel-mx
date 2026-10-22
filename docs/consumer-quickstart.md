# Inicio rápido para consumidores

Esta página ayuda a elegir el punto de entrada más pequeño para consumir una release verificable de `arancel-mx`. El **hub público** es [`https://arancel-mx.vercel.app/`](https://arancel-mx.vercel.app/); usa la documentación detallada para contratos completos, formatos y límites.

`arancel-mx` recupera y estructura datos. No clasifica mercancías ni constituye asesoría legal.

| Necesidad | Punto de entrada recomendado |
|---|---|
| Buscar sin instalar nada | [Hub web](https://arancel-mx.vercel.app/) |
| Validar instalación y release | CLI: `arancel-mx doctor` |
| Consultar una fila o su jerarquía | CLI o `Dataset.version(...)` |
| Analizar localmente muchas filas | `arancel_mx.duckdb` de una release verificada |
| Integrar un servicio o UI | API estática GET-only/read-only bajo `https://arancel-mx.vercel.app/data/v1` |

## 1. Instalar y verificar

```bash
python -m pip install arancel-mx
arancel-mx doctor --dataset data-YYYY.MM.DD
arancel-mx data download --dataset data-YYYY.MM.DD
arancel-mx data verify --dataset data-YYYY.MM.DD
```

`data-YYYY.MM.DD` representa una release exacta. Fija la aprobada por tu proceso y conserva `SHA256SUMS` y `manifest.json` junto con cualquier resultado derivado.

## 2. Consultar desde la CLI

```bash
arancel-mx lookup 01012101 --dataset data-YYYY.MM.DD --format json
arancel-mx ficha 01012101 --dataset data-YYYY.MM.DD
arancel-mx provenance 01012101 --dataset data-YYYY.MM.DD
```

Si el proceso debe funcionar sin red, descarga y verifica la release antes de ejecutar comandos con `--offline`. La referencia completa está en [CLI de consumo](consumer-cli.md).

## 3. Consultar desde Python

```python
from arancel_mx import Dataset

catalog = Dataset.version("data-YYYY.MM.DD")
record = catalog.lookup("01012101")
print(record.code, record.description)
```

`Dataset.version` fija una release inmutable. `Dataset.open` sirve para archivos locales, pero una apertura estructuralmente válida no implica la misma procedencia verificable de una release pública.

## 4. Consumir la API HTTP pública

Cada release verificada se publica también como archivos JSON estáticos en GitHub Pages, servidos desde el mismo dominio del hub:

```bash
export ARANCEL_MX_API_URL="https://arancel-mx.vercel.app"
curl "$ARANCEL_MX_API_URL/data/v1/meta.json"
curl "$ARANCEL_MX_API_URL/data/v1/records/85.json"
curl "$ARANCEL_MX_API_URL/data/v1/search-index.json"
```

`meta.json` identifica la release servida, `records/{hs2}.json` contiene todos los registros de un capítulo y `manifest.json` permite verificar cada archivo por SHA-256. Abre [`https://arancel-mx.vercel.app/documentation`](https://arancel-mx.vercel.app/documentation) para el hub de rutas y límites públicos.

Si necesitas rutas dinámicas como `/v1/meta`, `/v1/lookup/{code}` o `/readyz`, ejecuta el servidor incluido en el paquete sobre una release fijada:

```bash
ARANCEL_MX_API_DATASET=data-YYYY.MM.DD uvicorn arancel_mx.api.app:app
```

Las rutas `/v1` alojadas en `arancel-mx.vercel.app` están deprecadas y se retiran el 2027-01-31 ([guía de retiro](operations/v1-sunset.md)). La release verificable sigue siendo la fuente de verdad; cualquier API es una vista de ella.

## Continuar

- [Consumo externo](external-consumption.md): contratos completos de archivos, Python, HTTP, integridad y despliegue.
- [CLI de consumo](consumer-cli.md): comandos, caché, formatos y modo offline.
- [Roles de fuentes oficiales](official-source-roles.md): qué función cumple cada publicación.
- [Guía NICO y LIGIE](nico-ligie-guide.md): HS6, fracción mexicana y NICO.
- [Arquitectura](architecture.md): cómo se publica y se sirve cada release.
- [Centro de documentación](README.md): todas las rutas por intención.
