# Proceso de publicación

## 1. Captura y construcción

Captura documentos permitidos, verifica su identidad y ejecuta parsers offline. Materializa el candidato en una base DuckDB separada; no modifiques una versión publicada durante la construcción.

## 2. Conciliación

Compara el ledger de la Cámara de Diputados con evidencia del DOF y documentos operativos de SNICE. Las propuestas, indicadores, documentos faltantes y discrepancias permanecen explícitos.

## 3. Validación

La construcción rechaza duplicados, jerarquías inválidas, intervalos invertidos o superpuestos, procedencia incompleta, tasas incompatibles, padres faltantes y metadatos públicos incompletos.

## 4. Exportación determinista

`python -m arancel_mx build` exporta CSV, JSON y DuckDB desde una base validada. El manifiesto contiene versión, esquema, fecha efectiva, conteo, resultado de validación y hashes de artefactos.

## 5. Checksums y archivo de fuentes

`python -m arancel_mx release` verifica `manifest.json` y `SHA256SUMS`, vuelve a calcular cada hash y crea `official-sources.tar.gz`. El archivo sólo admite nombres simples declarados en `source_capture.json`; rutas absolutas, duplicadas o con traversal son rechazadas.

## 6. Puntero ligero

El comando prepara un directorio `latest` con manifiesto, checksums e instrucciones de descarga. Los binarios, bases y documentos originales permanecen fuera del historial Git.

## 7. Aprobación de publicación

El paquete no publica en GitHub ni hace push. Después de pruebas, revisión de procedencia y verificación independiente, una persona autorizada decide si crea el tag y adjunta los artefactos. Una versión existente nunca se sobrescribe.

