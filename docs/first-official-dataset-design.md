# Primer dataset oficial consolidado de `arancel-mx`

Fecha: 2026-08-10
Estado: diseño aprobado para implementación

## Objetivo

Construir y validar el primer dataset público consolidado de `arancel-mx` usando únicamente fuentes oficiales de México y la arquitectura canónica ya existente en el repositorio.

La salida reproducible debe contener:

- `arancel_mx.duckdb`
- `arancel_mx.csv`
- `arancel_mx.json`
- `manifest.json`
- `SHA256SUMS`
- `official-sources.tar.gz`

Los binarios y documentos oficiales capturados no se guardarán dentro del historial Git. La ejecución CI generará el dataset como artifact verificable y una publicación posterior podrá adjuntarlo a un GitHub Release explícito.

## Principios

1. Solo fuentes registradas en `src/arancel_mx/sources/source_registry.json`.
2. Cada documento descargado conserva URL, autoridad, fecha de observación/recuperación, tamaño y SHA256.
3. Ninguna fila canónica se publica sin procedencia.
4. El dataset no se publica si falla una validación estructural, jerárquica, temporal o de procedencia.
5. CSV, JSON y DuckDB deben contener el mismo contrato de columnas, orden lógico, conteo y hashes de registros.
6. La construcción debe ser repetible sin depender de datos privados ni credenciales.
7. Una ejecución nueva nunca sobrescribe silenciosamente una versión publicada.

## Estado actual reutilizable

El repositorio ya tiene las piezas principales:

- `source_registry.json` con Diputados, SNICE LIGIE, SNICE NICO, propuestas NICO, notas nacionales e indicadores ponderados;
- descubrimiento de documentos oficiales SNICE;
- captura determinista con SHA256;
- parsers XLS/XLSX/PDF;
- normalización de códigos y tasas;
- esquema DuckDB para fuentes, HS, fracciones, NICO, tasas, notas, propuestas, indicadores y procedencia;
- `materialize_arancel(...)` para consolidación transaccional;
- validaciones del dataset canónico;
- exportación determinista a CSV, JSON y DuckDB;
- manifiesto y `SHA256SUMS`;
- empaquetado determinista de fuentes oficiales.

Lo que falta es un orquestador end-to-end que conecte descubrimiento, descarga, identificación de perfiles, parseo, construcción jerárquica y materialización.

## Alcance de la primera versión

La primera versión pública debe materializar la capa arancelaria central:

- snapshot oficial de fracciones LIGIE;
- snapshot oficial de NICO;
- tasas IGI/IGE y unidad cuando estén presentes en el dataset oficial estructurado;
- jerarquía HS2 -> HS4 -> HS6 -> fracción8 -> NICO10;
- metadatos y procedencia de cada documento utilizado;
- base DuckDB canónica y exportaciones equivalentes.

Las familias de propuestas NICO, notas nacionales e indicadores ponderados siguen formando parte del esquema público, pero no bloquearán el primer release canónico si sus extractores no están todavía estabilizados. Se incorporarán incrementalmente sin cambiar el contrato base `arancel_mx`.

## Fuentes

La selección de fuentes no se codifica dos veces. El orquestador lee el registro versionado y usa las fuentes marcadas como oficiales.

Para la primera materialización:

- `ligie`: SNICE, dataset estructurado autoritativo para tarifa y fracciones;
- `nico`: SNICE, dataset estructurado autoritativo para NICO;
- `diputados_ligie`: Cámara de Diputados, referencia consolidada y apoyo de descubrimiento/reconciliación;
- DOF: autoridad de publicación legal declarada por el registro.

El dataset no inferirá reformas desde texto libre si no existe evidencia suficiente para reconciliarlas de forma verificable.

## Enfoque elegido

### Pipeline reproducible + GitHub Actions artifact + release explícito

No se commiteará `arancel_mx.duckdb` directamente al repositorio. La base se construirá en CI o localmente y se publicará como artifact verificable.

Ventajas:

- historial Git ligero;
- artefactos reconstruibles;
- hashes verificables;
- procedencia conservada;
- separación entre código y datos generados;
- publicación final controlada.

## Arquitectura

```text
source_registry.json
        |
        v
Official source discovery
        |
        v
Download + capture
URL + authority + timestamps + SHA256
        |
        v
Document/workbook probe
        |
        v
Registered parser profile
        |
        v
Normalized staging rows
        |
        +------------------+
        |                  |
        v                  v
LIGIE fractions/rates     NICO rows
        |                  |
        +--------+---------+
                 |
                 v
       derive HS2/HS4/HS6
                 |
                 v
       materialize_arancel
                 |
                 v
          candidate DuckDB
                 |
                 v
        canonical validation
                 |
                 v
       export_arancel_release
                 |
       +---------+---------+
       |         |         |
       v         v         v
      CSV       JSON     DuckDB
       \         |         /
        +---- manifest ----+
                 |
                 v
            SHA256SUMS
                 |
                 v
      official-sources.tar.gz
                 |
                 v
        Actions artifact
```

## Componentes nuevos

### `src/arancel_mx/pipeline/official_dataset.py`

Orquestador de una ejecución completa. Responsabilidades:

- cargar el source registry;
- descubrir documentos oficiales;
- seleccionar los snapshots relevantes;
- descargar/capturar documentos;
- generar metadatos `source_document`;
- resolver perfiles de workbook;
- parsear LIGIE y NICO;
- derivar jerarquía HS;
- separar clasificación y tasas;
- llamar `materialize_arancel`;
- exportar release;
- preparar archivo de fuentes.

No contendrá lógica específica de formato de una hoja; esa lógica permanece en parsers/perfiles.

### `src/arancel_mx/parsers/profiles.py`

Registro explícito de perfiles conocidos para workbooks oficiales. Cada perfil define:

- familia de documento;
- patrón de identificación;
- hoja;
- fila de encabezado;
- columnas oficiales -> campos lógicos;
- reglas de forward-fill si existen;
- versión del perfil.

Si un workbook oficial cambia de estructura y no coincide con un perfil registrado, la construcción falla de forma clara en lugar de adivinar columnas.

### `src/arancel_mx/pipeline/hierarchy.py`

Deriva niveles HS faltantes a partir de las fracciones oficiales y mantiene una descripción verificable por prefijo cuando la fuente disponible permite reconstruirla sin inventar contenido.

Si no hay descripción oficial suficiente para un nivel padre requerido por las validaciones, el pipeline debe obtenerla de la fuente consolidada registrada o fallar. No se generarán descripciones legales ficticias.

### `src/arancel_mx/sources/http.py`

Cliente de descarga pequeño y testeable:

- timeout;
- User-Agent identificable;
- `raise_for_status`;
- límite razonable de tamaño;
- validación de host contra el registry;
- captura de `Content-Type`;
- bytes exactos para SHA256.

### `scripts/build_official_dataset.py`

Entrada reproducible para CI y uso local. Debe aceptar como mínimo:

- `--work-dir`
- `--output-dir`
- `--effective-as-of`
- `--dataset-version`

La versión por defecto en CI puede derivarse de la fecha de la ejecución, pero siempre queda registrada en `dataset_release` y `manifest.json`.

## Selección de snapshots

Cuando una página oficial exponga múltiples documentos históricos, el pipeline no usará simplemente el primer enlace.

Regla:

1. descubrir todos los candidatos de la familia;
2. identificar el snapshot vigente mediante metadatos de la página/nombre de archivo y reglas registradas;
3. capturar el documento seleccionado;
4. registrar también el contexto de descubrimiento necesario para reproducir la selección;
5. fallar si hay ambigüedad entre múltiples candidatos aparentemente vigentes.

## Transformación LIGIE

El parser normaliza cada fracción oficial a `fraccion8`.

Para cada fracción se conserva, cuando exista en la fuente:

- descripción;
- unidad;
- IGI texto/tipo/valor;
- IGE texto/tipo/valor;
- versión LIGIE;
- vigencia;
- documento fuente.

Las tasas pertenecen al nivel `fraccion8`. Los NICO heredan los valores arancelarios de su fracción padre mediante la consolidación existente.

## Transformación NICO

Cada fila NICO produce:

- `fraccion8`;
- `nico2`;
- `nico10`;
- descripción oficial;
- versión LIGIE/NICO aplicable;
- documento fuente;
- vigencia cuando pueda determinarse de forma verificable.

Un NICO sin fracción padre válida hace fallar la construcción canónica.

## Jerarquía HS

La salida pública requiere padres HS2, HS4 y HS6 válidos para las fracciones vigentes.

La construcción utilizará los códigos oficiales para formar la relación jerárquica por prefijo, pero las descripciones de los niveles HS se extraerán de una fuente oficial/consolidada cuando estén disponibles. No se presentará el prefijo numérico como si fuera una descripción legal.

## Procedencia

Cada `source_document` debe incluir:

- `source_document_id` estable;
- autoridad;
- publication venue;
- título;
- URL;
- media type;
- SHA256;
- ruta local de trabajo;
- fecha publicada si está disponible;
- fecha efectiva si está disponible;
- observed_at;
- retrieved_at.

La ruta local se elimina del manifiesto público, como ya hace el exportador.

## Versionado

Primera convención:

```text
dataset_version = YYYY.MM.DD
schema_version = 1
```

Si se reconstruye el mismo día con exactamente las mismas fuentes y lógica, los artefactos lógicos deben ser equivalentes. Si cambia una fuente oficial, el manifest deja evidencia mediante SHA256.

Las correcciones que cambien datos publicados deberán producir una nueva versión en lugar de sobrescribir una existente.

## Errores y cuarentena

La primera versión prioriza fail-closed.

Debe fallar ante:

- workbook desconocido;
- columnas obligatorias ausentes;
- códigos de longitud inválida;
- duplicados incompatibles;
- NICO sin fracción;
- fracción sin jerarquía HS válida;
- fuente fuera de los hosts permitidos;
- hash/captura inconsistente;
- procedencia incompleta;
- tasas incompatibles;
- intervalos invertidos o superpuestos;
- diferencias entre CSV/JSON/DuckDB.

`arancel_quarantine` puede registrar filas rechazadas durante análisis, pero una release pública no se marca como `passed` si las anomalías afectan el contrato canónico.

## GitHub Actions

Crear `.github/workflows/build-official-dataset.yml`.

Triggers iniciales:

- `workflow_dispatch`;
- calendario semanal para detectar cambios y validar que las fuentes siguen siendo parseables.

Pasos:

1. checkout;
2. Python 3.11;
3. instalar `.[dev]`;
4. ejecutar tests;
5. ejecutar `scripts/build_official_dataset.py`;
6. verificar `manifest.json` y `SHA256SUMS`;
7. subir como artifact el directorio de release y el archivo de fuentes.

El workflow programado no crea automáticamente un GitHub Release en la primera iteración. La publicación debe ser explícita hasta estabilizar la ingestión real.

## Publicación posterior

Una vez verificado un artifact real, un segundo paso puede crear:

```text
tag: data-YYYY.MM.DD
```

y adjuntar los seis artefactos públicos.

Ese paso queda fuera del primer cambio hasta que exista por lo menos una construcción real exitosa con datos oficiales vigentes.

## Tests

Agregar pruebas para:

- selección de snapshot;
- rechazo de hosts no registrados;
- resolución de perfiles;
- parsing de fixtures LIGIE;
- parsing de fixtures NICO;
- derivación de jerarquía;
- creación de `source_document`;
- integración end-to-end offline usando fixtures;
- determinismo de dos construcciones con las mismas entradas;
- equivalencia CSV/JSON/DuckDB;
- ausencia de secretos/rutas locales en manifest público;
- workflow YAML y artifact contract.

Los tests de red no se ejecutan dentro de la suite normal. CI separa el test offline de la construcción real con fuentes oficiales.

## Criterios de aceptación

El cambio se considera funcional cuando una ejecución real produce:

```text
out/release/
├── arancel_mx.duckdb
├── arancel_mx.csv
├── arancel_mx.json
├── manifest.json
├── SHA256SUMS
└── official-sources.tar.gz
```

Y además:

- `validation_status == "passed"`;
- `row_count > 0`;
- existen registros `fraccion8`;
- existen registros `nico10`;
- cada NICO vigente tiene fracción padre;
- cada fracción vigente tiene HS6 -> HS4 -> HS2;
- cada registro tiene al menos una fuente;
- `source_documents` del manifest tiene URL y SHA256;
- CSV, JSON y DuckDB tienen el mismo conteo y contrato canónico;
- `verify_release(...)` pasa;
- `verify_sources(...)` pasa;
- la suite offline completa sigue verde.

## Fuera de alcance de esta primera implementación

- API web;
- UI de consulta;
- búsqueda semántica;
- RAG;
- datos de balanza comercial de Banxico;
- pedimentos;
- regulaciones no arancelarias completas;
- publicación automática no supervisada a GitHub Releases;
- clasificación arancelaria asistida por IA.

Este trabajo se limita al núcleo público y reproducible de datos LIGIE/NICO.