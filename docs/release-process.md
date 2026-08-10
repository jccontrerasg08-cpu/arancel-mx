# Proceso de publicación

## 1. Captura y construcción

Captura documentos permitidos, verifica su identidad y ejecuta parsers offline. Materializa el candidato en una base DuckDB separada; no modifiques una versión publicada durante la construcción.

La construcción end-to-end desde las fuentes registradas se ejecuta con:

```bash
python scripts/build_official_dataset.py \
  --work-dir data/embedded/official-build \
  --output-dir out/release \
  --effective-as-of 2026-08-10 \
  --dataset-version 2026.08.10
```

El orquestador descubre los snapshots oficiales vigentes, captura sus bytes con SHA256, resuelve perfiles conocidos, construye la jerarquía HS2 -> HS4 -> HS6 -> fracción8 -> NICO10 y falla si encuentra ambigüedad, procedencia incompleta o un padre faltante.

## 2. Conciliación

Compara el ledger de la Cámara de Diputados con evidencia del DOF y documentos operativos de SNICE. Las propuestas, indicadores, documentos faltantes y discrepancias permanecen explícitos.

## 3. Validación

La construcción rechaza duplicados, jerarquías inválidas, intervalos invertidos o superpuestos, procedencia incompleta, tasas incompatibles, padres faltantes y metadatos públicos incompletos.

El candidato no se exporta si la vista canónica no supera sus validaciones. La release pública requiere `validation_status == "passed"`, conteo positivo y presencia de fracciones arancelarias y NICO.

## 4. Contrato de artefactos

Una construcción oficial verificada produce exactamente:

```text
release/
├── arancel_mx.duckdb
├── arancel_mx.csv
├── arancel_mx.json
├── manifest.json
├── SHA256SUMS
└── official-sources.tar.gz
```

`arancel_mx.csv`, `arancel_mx.json` y la vista `arancel_mx` dentro de `arancel_mx.duckdb` comparten el contrato canónico. El archivo `manifest.json` conserva versión, esquema, fecha efectiva, conteo, resultado de validación, documentos fuente y SHA256 de los artefactos.

## 5. Checksums y archivo de fuentes

`python -m arancel_mx release` verifica `manifest.json` y `SHA256SUMS`, vuelve a calcular cada hash y crea `official-sources.tar.gz`. El archivo sólo admite nombres simples declarados en `source_capture.json`; rutas absolutas, duplicadas o con traversal son rechazadas.

Cada archivo DuckDB se verifica contra el SHA256 declarado para esa construcción. La reproducibilidad lógica se valida mediante el contenido canónico y sus hashes de registro, sin asumir que dos archivos físicos DuckDB creados en ejecuciones separadas sean byte a byte idénticos.

## 6. Build official dataset en GitHub Actions

El workflow **Build official dataset** está definido en [`.github/workflows/build-official-dataset.yml`](../.github/workflows/build-official-dataset.yml).

El workflow puede ejecutarse mediante `workflow_dispatch` y también tiene una ejecución semanal. Usa permisos `contents: read`, ejecuta primero `python -m pytest -q`, construye el dataset con `scripts/build_official_dataset.py`, valida el `manifest.json` y sólo después sube `out/release/` como artifact de GitHub Actions.

Los artefactos generados, bases DuckDB y documentos oficiales descargados permanecen fuera del historial Git. Las rutas de trabajo y salida están cubiertas por las reglas del repositorio para datos generados.

## 7. Puntero ligero

El comando de preparación de release puede producir un directorio `latest` con manifiesto, checksums e instrucciones de descarga. Los binarios, bases y documentos originales permanecen fuera del historial Git.

## 8. Aprobación manual de publicación

Ni el script ni el workflow crean tags, hacen push o publican GitHub Releases. Después de pruebas, revisión de procedencia y verificación independiente, una persona autorizada decide manualmente si crea un tag como `data-YYYY.MM.DD` y adjunta los seis artefactos verificados.

La publicación es supervisada y una versión existente nunca se sobrescribe silenciosamente. La automatización actual termina en un artifact verificado de GitHub Actions; la promoción a GitHub Releases sigue siendo un paso manual.
