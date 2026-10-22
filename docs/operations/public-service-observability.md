# Observabilidad del servicio público

Este documento explica cómo comprobar que el sitio público sirve la API estática de datos de la última release verificada y cómo medir su latencia. Está dirigido a mantenedores que revisan una release o investigan una falla del sitio. La sonda es de sólo lectura: no publica datos, no sincroniza fuentes, no modifica releases y no convierte una medición puntual en un acuerdo de nivel de servicio.

## Qué comprueba

`scripts/check_public_service.py` consulta por `GET`, contra `https://arancel-mx.vercel.app` por defecto, los archivos de la API estática que Vercel reescribe hacia GitHub Pages:

| Archivo | Condición |
|---|---|
| `https://arancel-mx.vercel.app/data/v1/meta.json` | Responde `application/json`, declara `dataset_tag` y `dataset_version`, y `release_verified` es `true`. |
| `https://arancel-mx.vercel.app/data/v1/manifest.json` | Declara el mismo `dataset_tag` que `meta.json` y lista `records/85.json` entre sus archivos. |
| `https://arancel-mx.vercel.app/data/v1/records/85.json` | Es una lista no vacía de registros del capítulo 85, cada uno con `code`, y su `dataset_version` coincide con `meta.json`. |
| `https://arancel-mx.vercel.app/data/v1/search-index.json` | Contiene `entries` no vacías para la búsqueda retrieve-only. |

Cualquier condición incumplida termina con un error y código distinto de cero. La sonda no usa rutas alternativas como fallback.

## Ejecutar una comprobación de contrato

```bash
python scripts/check_public_service.py
```

Opciones:

- `--base-url URL` apunta la sonda a otro despliegue, por ejemplo un servidor FastAPI local (`http://127.0.0.1:8000`), que sirve el mismo árbol en `/data/v1`.
- `--timeout SEGUNDOS` fija el tiempo máximo por petición (20 por defecto).

El canario diario [`published-bundle-canary.yml`](../../.github/workflows/published-bundle-canary.yml) ejecuta `python scripts/check_public_service.py --timeout 20` después de descargar y verificar el bundle publicado.

## Medir una muestra de latencia

```bash
python scripts/check_public_service.py --latency-samples 3
```

Cada muestra consulta `/data/v1/meta.json`, `/data/v1/search-index.json` y `/data/v1/records/85.json`. El comando imprime ruta, código HTTP y duración por petición. Los resultados sirven para comparar cambios o decidir una investigación; no bloquean CI ni activan cachés o cambios de ranking.

## Interpretación responsable

Separa red, caché del CDN y tamaño del archivo antes de atribuir una diferencia de latencia. `search-index.json` es el archivo más grande del árbol y domina la primera búsqueda en el navegador. Una diferencia aislada no justifica cambiar el formato del árbol sin una línea base repetible. La búsqueda y las sugerencias son retrieve-only: no clasifican mercancías ni constituyen asesoría legal.

## Relacionado

- [Arquitectura](../architecture.md#archivos-de-la-api-estática)
- [Proceso de release](../release-process.md#9-api-estática-en-github-pages)
- [Consumo externo](../external-consumption.md)
- [Configuración de GitHub](github-settings.md#7-github-pages)
