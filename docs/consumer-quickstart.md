# Inicio rápido para consumidores

Esta página ayuda a elegir el punto de entrada más pequeño para consumir una release verificable de `arancel-mx`. El **hub público** es [`https://arancel-mx.vercel.app/`](https://arancel-mx.vercel.app/); usa la documentación detallada para contratos completos, formatos y límites.

`arancel-mx` recupera y estructura datos. No clasifica mercancías ni constituye asesoría legal.

| Necesidad | Punto de entrada recomendado |
|---|---|
| Buscar sin instalar nada | [Hub web](https://arancel-mx.vercel.app/) |
| Validar instalación y release | CLI: `arancel-mx doctor` |
| Consultar una fila o su jerarquía | CLI o `Dataset.version(...)` |
| Analizar localmente muchas filas | `arancel_mx.duckdb` de una release verificada |
| Integrar un servicio o UI | API HTTP GET-only/read-only bajo `https://arancel-mx.vercel.app` |

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

El origen público canónico es el mismo dominio del hub:

```bash
export ARANCEL_MX_API_URL="https://arancel-mx.vercel.app"
curl "$ARANCEL_MX_API_URL/readyz"
curl "$ARANCEL_MX_API_URL/v1/meta"
curl "$ARANCEL_MX_API_URL/v1/search?q=telefonos&limit=5"
curl "$ARANCEL_MX_API_URL/v1/lookup/8517130100"
```

Abre [`https://arancel-mx.vercel.app/documentation`](https://arancel-mx.vercel.app/documentation) para el hub local de rutas y límites públicos.

La superficie pública mantiene una única frontera read-only: rutas `/v1` promovidas y `/readyz` se resuelven en la capa operacional de Vercel respaldada por Neon y sincronizada desde releases verificadas. Las rutas no promovidas se resuelven localmente sin proxy externo. La release verificable sigue siendo la fuente de verdad; Vercel y Neon son superficies de consumo.

La API es GET-only y read-only. `/v1/meta` separa la versión de API, la versión del paquete y la identidad del dataset servido; `/readyz` refleja la disponibilidad de esa release operacional activa.

## Continuar

- [Consumo externo](external-consumption.md): contratos completos de archivos, Python, HTTP, integridad y despliegue.
- [CLI de consumo](consumer-cli.md): comandos, caché, formatos y modo offline.
- [Roles de fuentes oficiales](official-source-roles.md): qué función cumple cada publicación.
- [Guía NICO y LIGIE](nico-ligie-guide.md): HS6, fracción mexicana y NICO.
- [Centro de documentación](README.md): todas las rutas por intención.
