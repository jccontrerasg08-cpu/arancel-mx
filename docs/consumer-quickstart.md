# Inicio rápido para consumidores

Esta página ayuda a elegir el punto de entrada más pequeño para consumir una release verificable de `arancel-mx`. Usa la documentación detallada para contratos completos, formatos y límites. El proyecto recupera datos; no es asesoría legal y no clasifica mercancías.

| Necesidad | Punto de entrada recomendado |
|---|---|
| Validar una instalación y release | CLI: `arancel-mx doctor` |
| Consultar una fila o su jerarquía | CLI o `Dataset.version(...)` |
| Analizar localmente muchas filas | `arancel_mx.duckdb` de una release verificada |
| Integrar una aplicación ya desplegada | API HTTP GET-only, empezando con `/v1/meta` |

## 1. Instalar y verificar

```bash
python -m pip install arancel-mx
arancel-mx doctor --dataset data-2026.08.15
arancel-mx data download --dataset data-2026.08.15
arancel-mx data verify --dataset data-2026.08.15
```

El identificador anterior es un ejemplo. Fija la release aprobada por tu proceso y conserva `SHA256SUMS` y `manifest.json` junto con cualquier resultado derivado.

## 2. Consultar desde la CLI

```bash
arancel-mx lookup 01012101 --dataset data-2026.08.15 --format json
arancel-mx ficha 01012101 --dataset data-2026.08.15
arancel-mx provenance 01012101 --dataset data-2026.08.15
```

Si el proceso debe funcionar sin red, descarga y verifica la release antes de ejecutar comandos con `--offline`. Consulta la referencia completa en [`docs/consumer-cli.md`](consumer-cli.md).

## 3. Consultar desde Python

```python
from arancel_mx import Dataset

catalog = Dataset.version("data-2026.08.15")
record = catalog.lookup("01012101")
print(record.code, record.description)
```

`Dataset.version` fija una release inmutable. `Dataset.open` sirve para archivos locales, pero una apertura estructuralmente válida no implica la misma procedencia verificada de una release pública.

## 4. Consumir la API HTTP pública

Cuando exista un origen HTTP desplegado y verificado para tu entorno, empieza por sus identidades y estado:

```bash
curl "$ARANCEL_MX_API_URL/healthz"
curl "$ARANCEL_MX_API_URL/readyz"
curl "$ARANCEL_MX_API_URL/v1/meta"
```

La API es GET-only y read-only. `/v1/meta` separa la versión de API, versión del paquete y versión del dataset. Revisa `/docs` y `/openapi.json` en el mismo origen para el contrato interactivo. La URL del despliegue, los límites de servicio y la disponibilidad deben proceder de la documentación del entorno que lo opere.

## Continuar

Lee [`docs/official-source-roles.md`](official-source-roles.md) antes de usar un resultado para una decisión de comercio exterior. Para interpretar la jerarquía HS6, fracción de 8 dígitos y NICO de 2 dígitos, consulta [`docs/nico-ligie-guide.md`](nico-ligie-guide.md). Para contratos de artefactos, procedencia y autoingesta, consulta [`docs/external-consumption.md`](external-consumption.md).
