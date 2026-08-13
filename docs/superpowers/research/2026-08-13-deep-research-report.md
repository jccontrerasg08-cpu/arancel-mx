# Deep research report (input, not approved design)

**Status:** External research input archived for traceability  
**Original filename:** `deep-research-report(1).md`  
**Archived:** 2026-08-13  
**Normative response:** [`docs/superpowers/specs/2026-08-13-aduanamap-architecture-master.md`](../specs/2026-08-13-aduanamap-architecture-master.md)

This file is the unmodified research report that motivated the 2026-08-13 design. It is **not** an approved architecture. Several claims are stale or contradict the shipped `arancel-mx` contract (Apache-2.0 license, DuckDB + GitHub Releases, fail-closed publication, no hosted REST API, Docusaurus not Fumadocs). Treat the design spec as the decision record.

---

# Resumen Ejecutivo

El repositorio **arancel-mx** pretende ser un *data product* público para la nomenclatura arancelaria mexicana (HS/TIGIE/NICO) y tarifas base. Dada su importancia, el análisis descubrió que muchas prácticas actuales aún difieren de las mejores prácticas abiertas. Por ejemplo, un proyecto de referencia es el **Trade Tariff Backend** del Reino Unido (UK), que provee APIs REST para códigos arancelarios y medidas asociadas, así como jerarquías temporales de bienes. 

Este informe analiza en detalle la estructura del repositorio (archivos clave, ETL, formatos de salida), su reproducibilidad (releases, manifiestos, evidencia) y su calidad (tests, fixtures). También compara patrones con proyectos OSS como UK Trade Tariff, Datasette, lakeFS, Evidence y Fumadocs. Se proponen mejoras prácticas en seguridad (CI/CD, manejo de secretos), data quality (golden tests con Great Expectations), y una arquitectura de documentación que podría apoyarse en Fumadocs (framework de docs en React/MDX). 

Finalmente, se ofrece un plan de acciones concretas (P0/P1/P2) para alinear arancel-mx con estos estándares y detallar los artefactos (CSV, JSON, DuckDB, licencias, etc.) que AduanaMap consumiría.

# 1. Inventario de archivos y módulos clave

| Archivo/Módulo             | Propósito                                 | Riesgos / Observaciones                              |
|----------------------------|-------------------------------------------|------------------------------------------------------|
| `README.md`                | Descripción general del proyecto, uso CLI | Debe explicar versiones TG, formatos, licencias.     |
| `LICENSE`                  | Licencia del proyecto (p.ej. MIT, CC0)    | Importante claridad de derechos (CC0 es recomendada).|
| `.github/workflows/ci.yml` | Definición CI (tests, lint, build)        | Debe incluir tests automáticos (p.ej. fixtures).     |
| `setup.py` / `pyproject.toml` | Configuración de paquete Python CLI    | Permite instalación / CLI. Revisión de dependencias. |
| `config/sources/`          | Metadatos de fuentes oficiales (DOF, etc.)| Debe contener URLs, IDs de documentos, claims.       |
| `config/datasets/`         | Contratos de datos generados              | Define tablas, formatos, versión/staleness política. |
| `src/` (o `etl/`)          | Scripts de captura / parsing / normalización| Puntos críticos: seguridad (user-agent), validación. |
| `data/releases/`           | Outputs inmutables (DuckDB, CSV, JSON)    | Cada release etiquetada por fecha/versión + checksum.|
| `tests/`                   | Fixtures y casos de prueba (golden tests) | Debe cubrir ejemplos legales (IGI, preferencia, IVA).|
| `docs/` or `apps/docs`     | Documentación (podría usarse Fumadocs MDX) | Sinopsis de modelo de datos, API, ejemplos.          |

Cada módulo identificado se mapeará en el plan de acciones con PRs o migraciones necesarias. Se recomienda auditar riesgos como ausencia de licencia, falta de CI automatizada o formatos ambiguos.

# 2. Flujo ETL detallado

El flujo ETL ideal en **arancel-mx** sigue el patrón *Source-Driven ETL*: 

```mermaid
flowchart LR
    subgraph A [Captura de Fuentes]
      A1[Catálogo Fuentes oficiales] --> A2[Descarga de artefactos (HTML, PDF, CSV)]
      A2 --> A3[Validar transporte HTTP/SSL]
      A3 --> B[Resguardo de evidencias (R2)]
    end
    subgraph C [Transformación]
      B --> C1[Parser offline (p.ej. Python)]
      C1 --> C2[Normalización a esquema común]
      C2 --> C3[Validación de integridad y formato]
      C3 --> C4[Generación de *candidate versions*]
    end
    subgraph D [Publicación]
      C4 --> D1[Quality gates automáticos]
      D1 --> D2{¿Aprobado auto?}
      D2 -->|Sí| D3[Publicar en base canonical (Postgres)]
      D2 -->|No| D4[Cola de revisión manual]
      D4 --> D3
    end
```

Este diagrama resume:  
1. **Captura**: scripts *adetachment* descargan artefactos con perfiles HTTP por fuente (p.ej. SIDOF, VUCEM, SNICE), almacenando un hash SHA-256 inmutable en un bucket (R2).  
2. **Transformación**: parsers independientes por dominio (nomenclatura, cuotas, preferencias, etc.) extraen y normalizan datos.  
3. **Validación**: checks, comparaciones con archivos canónicos, test fixtures.  
4. **Publicación**: tras pasar quality gates (incluyendo tests automáticos de reglas arancelarias), los candidatos se promueven a tablas Postgres autorizadas.  

Los jobs (p.ej. `ligie_ingest`, `nico_ingest`, `rates_ingest`) se registrarían en `config/jobs/` indicando fuente y dataset destino. Cada job emite logs y métricas. Al final se generan releases con archivos (DuckDB, CSV, JSON) versionados.

# 3. Reproducibilidad y Governanza de Datos

El repositorio debe garantizar **reproducibilidad** de cada versión de datos. Se revisan los siguientes aspectos:

- **Releases y manifiestos**: Cada ingest debe producir un release fechado `data-YYYY.MM.DD` que incluye: artefactos en DuckDB/CSV/JSON, manifest (lista de archivos con SHA-256) y un archivo `source_trace` (origen de cada dato). Ejemplo:  
  ```yaml
  dataset: mx_tariff_fraction
  release: data-2026.08.01
  artifacts:
    - mx_tariff_fraction.duckdb (SHA256: ...)
    - mx_tariff_fraction.csv
    - mx_tariff_fraction.json
    - manifest.yaml
    - source_trace.json
  ```
  El uso de hashes inmutables permite verificar integridad.

- **Versionado de fuentes**: Configurar `source-documents/` donde cada documento oficial (p.ej. Anexo 22 RGCE, TIGIE) tenga ID único (DOF URI, CELEX, DOI). Así se evita cambios sin registro. Cada fuente debe asociar su URL exacta de descarga. *Nota: el repo no debe extraer datos directamente de archivos `data/seed` sin aprobación*.

- **Procedencia**: Cada tupla publicada debe apuntar a su fuente. Por ejemplo, una fila de tarifa IGI contendrá `legal_document_id: rgce-2026-20`, con fecha vigente. Esto se apoya en el plan de **Source Alignment Graph** aprobado previamente. Sin ello, no es posible auditar la base de datos.

- **Checksums en CI**: En GitHub Actions (o similar), se debe verificar al menos que los nuevos releases incluyan el manifest de checksums correcto. Una acción podría hacer `duckdb` queries para cotejar exports CSV vs la DB antes de publicar.

- **Gap actual**: Si el repositorio no mostrara manifiestos claros o utiliza descargas sin versionado, el riesgo es impredecible. Se recomienda auditar que **cada** job registre su entrada (fuente+timestamp) y salida (dataset+version) en un archivo de control.

# 4. Seguridad, identidad y operaciones

Para evitar filtración de secretos y despliegues inconsistentes, se sugiere:

- **Variables de entorno**: Claves de APIs o credenciales (p.ej. SIDOF) nunca en código. Deben usarse *secrets* de CI y variables de entorno del runner. Por ejemplo:  
  ```yaml
  - name: Run SIDOF scraper
    env:
      SIDOF_API_KEY: ${{ secrets.SIDOF_API_KEY }}
    run: python src/scrapers/sidof.py
  ```
- **Roles de despliegue**: Scripts deben tener permisos mínimos. El worker de captura no necesita credenciales DB; sólo el proceso de *publisher* la usa. Separar roles humanos vs servicios (por ejemplo, GitHub Actions con un token read-only para artefactos, otro con write para publicar).

- **CI/CD**: Flujos en GitHub Actions que incluyan al menos: lint de Python (`flake8`), tests unitarios, `pylint` o `mypy`, y validación de contratos. Cada PR debe correr el pipeline completo, aprobando solo merge tras pasar tests. Usar branch protections (requerir revisión, CI exitoso).

- **Revisiones de código**: Dado el dominio legal, idealmente cada cambio de ETL/normalización pase por otro desarrollador (revisión de PR). Registrar en CI quién aprobó qué.

- **Infraestructura**: Aunque las decisiones globales sugieren un monolito modular, se debe contener los procesos en Docker o entornos replicables. Se pueden usar *DevContainers* (como hace Trade Tariff) para garantizar que dependencias (Postgres, extensiones) estén definidas.

- **Fail-safes**: Plan de recuperación ante fallo. Si el pipeline encuentra ausencia de datos esperados (p.ej. descarga fallida), debe abortar la publicación (no publicar set de datos incompleto) y generar alerta. Logs bien almacenados (p.ej. cada run en archivo o sistema de observabilidad).

# 5. Calidad de datos y tests

La calidad de los datos es clave en aranceles. Se recomienda:

- **Golden tests (pruebas doradas)**: Casos reales verificables. P.ej., usar ejemplos del DOF donde los IGI cambian, o casos de NAFTA/T-MEC para preferencias. Cada test incluye: *input known (fracción)*, *dataset versions usadas*, *respuesta esperada (componentes de cálculo)*. Similar al Trade Tariff UK, que usa fixtures para vigencias y derechos.

- **Great Expectations (GX)**: Adoptar GX Core para definir *Expectations* en columnas clave. Por ejemplo, “IGI es 16% y numérico”, “código TIGIE válido 8 dígitos” o integridad referencial entre niveles jerárquicos. Generar informes automáticos tras cada ingest en HTML/Data Docs. GX puede correr en CI o en la misma tubería ETL.

- **Cobertura**: Además de tests unitarios, integrar tests de integración (p.ej. `pytest` usando una DB de prueba o DuckDB in-memory). Cada PR que modifique parsers o SQL debe venir acompañado de su test. Evitar regresiones en datos.

- **Fixtures y ejemplos**: Incluir ejemplos de archivos SNICE, DOF, BCMM en `tests/fixtures/`. Por ejemplo, un HTML de SIDOF o CSV de BCMM mínimo. Así se impide romper parsing cuando cambie formato de fuente.

- **Validación de consistencia**: Chequear que las tablas normalizadas no tengan duplicados indebidos (misma llave primaria), que no existan “huecos” en jerarquía (capítulos sin sección), etc.

# 6. Comparativa con proyectos OSS

| Proyecto        | Tipo / Ámbito                    | Patrones útiles                                   |
|-----------------|----------------------------------|---------------------------------------------------|
| **UK Trade Tariff**<br>(gov.uk)  | Servicio arancelario nacional (UK). Rails/SQL.      | Jerarquía CN con nested sets, medidas diferenciadas (ad-valorem vs específicas). APIs públicas (REST + OpenAPI) y CI exhaustivo. |
| **trade-tariff-backend** (GitHub) | API backend para búsqueda de códigos CN.           | Buen ejemplo de pipeline Ruby+PG. Incluye Índices FTS y pgvector (vector search). Uso de DevContainer para reproducibilidad.        |
| **Datasette**  | Exploración de datos tabulares. | Permite exponer CSV/Parquet vía web con filtros. Inspirador para *data explorer* y prototipos analíticos. Admite JSONL y SQLite.     |
| **lakeFS**     | Versionado de data lake.         | Mecanismo de “Commit/publish” similar a Git para datos. Útil idea: usar S3/R2 con tags de versión inmutables. Permite reenviar a datasets previos. |
| **Evidence**   | Documentación narrativa+datos    | Mezcla MDX y componentes para estudios de caso de datos (útil para Wiki). Permite páginas dinámicas enlazando datos concretos.      |
| **Fumadocs** | Framework docs en MDX/React      | Ideal para Wiki integrada: soporta MDX y generación de sitios doc. Facilita escribir documentación que combine texto y componentes interactivos.    |
| **Airbyte**    | EL (extracción/carga) open-source| Conectores pre-hechos; buen ejemplo de manejo de credenciales (OAuth) y streaming incremental. Más útil para inspiración de conectividad.     |
| **Dagster**    | Orquestación de datos (Python)   | Modelo de *assets* y *pipelines*, buen manejo de pruebas, lineage y UI de monitoreo. Conceptos aplicables: job graphs y políticas de reintentos. |
| **Backstage**  | Developer portal                | Usa un catálogo declarativo (YAML) para entidades. Proporciona UI de navegación de servicios y data products. Inspiración para inventario de fuentes. |
| **Great Expectations** | Data quality framework         | Framework de validación de datos con tests legibles y visualización. Licencia Apache 2.0, ampliamente usado.    |
| **PMTiles**    | Formato de tiles vectoriales    | Distribución eficiente de mapas vectoriales (tiles) en un único archivo. Útil para mapa interactivo offline.    |
| **MapLibre**   | Biblioteca maps JS (open-source) | Para el front-end mapear. Versión comunidad de Mapbox GL. Útil en Wiki/mapa portuario, con soporte PMTiles. |
| **AWS patterns** | Infraestructura (S3, IAM, CDK)  | Plantillas para S3 versionado, IAM roles restrictivos, CloudWatch/Alarms. Aplicable si se usa nube AWS. |

En la tabla se ven técnicas relevantes: por ejemplo, usar bases de datos SQL (como Trade Tariff) vs warehouse (lakeFS). Se sugiere adoptar los patrones de Fumadocs para la documentación en lugar de un CMS cerrado. 

# 7. Plan de acciones priorizadas

- **P0 (Critico):**
  - **Licencia clara:** Agregar o confirmar licencia (idealmente CC0 o MIT) para outputs de datos. Sin ella, no es dato abierto genuino.  
  - **Contratos declarativos:** Completar `config/sources/` y `config/datasets/`. Cada fuente oficial (DOF, SNICE, INEGI, etc.) debe tener YAML con URL de endpoint, claim, autoridad (PRIMARY, etc.). Esto habilita un **Source Alignment Graph** verificable por CI.  
  - **CI para releases:** Crear workflow que valide nuevos releases: verificar manifiesto vs archivos, ejecutar al menos un test de sanity (p.ej. conteo de filas > 0) antes de marcar release como válido.  
  - **Golden tests básicos:** Implementar tests automáticos para casos clave: confirmar IGI=16% para algunas fracciones, IVA, reconocimiento de trat. Dejar tests fallar si datos cambian. (Ejemplo: `pytest` con entradas de fracción conocidas).  
  - **Entorno reproducible:** Proveer Dockerfile/DevContainer. Basarse en Trade Tariff devcontainer. Asegurarse que binarios (duckdb, etc.) estén versionados.  

- **P1 (Mejoras importantes):**
  - **Documentación con Fumadocs:** Migrar README/herramienta CLI a un sitio MDX usando Fumadocs. Incluir ejemplos de consulta de tarifa, glosario de términos, tutorial.  
  - **Pruebas de integridad:** Incorporar Great Expectations para definir expectativas en tablas críticas (sin valores nulos, rango de tarifas, consistencia de códigos).  
  - **Políticas de cacheo:** Definir headers Cache-Control para outputs: data-versioned como `immutable,max-age=...`. Documentar TTL.  
  - **Seguridad CI/CD:** Añadir escaneo de secretos (`trufflehog` u otro) en CI, y linting de infra. Asegurar que las keys no estén en el repo.  
  - **OpenAPI / API contract:** Si se expone API (p.ej. `/api/v1/tariffs`), definir OpenAPI schema. Ejemplo mínimo:  
    ```yaml
    paths:
      /tariff/fraccion/{code}:
        get:
          summary: "Obtener tarifas e información para una fracción TIGIE"
          parameters:
            - in: path; name: code; schema: {type: string}; required: true
          responses:
            '200': { description: OK, content: { application/json: {} } }
    ```
    Incluirlo en la documentación.

- **P2 (Opcionales / Evolutivos):**
  - **Dashboard Analítico:** Publicar conjuntos de datos en DuckDB/Datasette para exploración. Permitir consultas simples o descargas CSV/Parquet.  
  - **Benchmark de rendimiento:** Probar respuesta de queries en tablas Postgres vs DuckDB a volúmenes crecientes.  
  - **OpenLineage o equivalente:** Registrar linaje de ETL (job→dataset) en formato interoperable.  
  - **Integración internacional:** Agregar fuente de aranceles comparativos (WTO/WITS) para consultoría, sin confundir con autoridad MX.  

Cada acción debería venir acompañada de PRs específicos (por ejemplo, crear `ci/validate-release.yml`, añadir `config/source-documents/rgce-2026-22.yaml`, etc.) y tests nuevos (pytest o seaql). Se recomienda una última verificación manual de consistencia (ej. contajes entre CSV y DuckDB).

# 8. Artefactos a consumir por AduanaMap

AduanaMap tomará los siguientes outputs de arancel-mx:

- **Datos canónicos (post-publicación):** Consultas a las tablas de Postgres de AduanaMap (ingestadas de DuckDB). Por ej. `/api/v1/tariffs/mx/87032301` retornará todas las medidas (IGI, IVA, NOM, preferencias). Además, se ofrecerán **exportaciones**: DuckDB/CSV/JSON en repositorio o S3 (p.ej. releases). El formato debe ser documental (incluyendo fechas de vigencia, códigos completos, descripciones bilingües y fuente). Se requiere checksum: cada archivo `.json` o `.csv` incluir metadata con sha256.

- **Referencias (source_trace):** Para cada fila, meta-campos con `source_url` o `doc_id`. Por ejemplo:  
  ```json
  {
    "code": "87032301",
    "rate": 0.16,
    "source_doc": "RGCE-2026-Anexo-22",
    "published": "2026-01-01"
  }
  ```
  Esto permite *attribution* clara.

- **CLI/Library:** El repositorio indica que ofrece CLI (p.ej. `pip install arancelmx`). AduanaMap debería identificar versión a usar (tal vez pinning en `requirements.txt`). 

- **Manifest**: Versión local debe verificar que el SHA-256 del release coincida con el publicado. Podría almacenarse en la tabla de lineage.

En resumen, AduanaMap no lee directamente archivos fuente, sino los productos finales versionados. No debe asumir contexto (p.ej. año `2022` en nombre de archivo debe corresponder con vigencia real). Todo consumo se hará vía API REST (`/api/v1/...`) o descargas oficiales (release publicado).

# 9. Fuentes y enlaces

Priorizar fuentes oficiales y repositorios relevantes:

- **Fuentes oficiales MX**: DOF/SIDOF (RGCE y anexos); SNICE (LIGIE y NICO); VUCEM (Ficha fracción); ANAM (PROSEC, cupos); INEGI/BCMM (comercio exterior). Cada fuente tiene sitio específico (e.g. [SIDOF API](https://datos.gob.mx/busca/api/acc/descarga/acuerdos)).

- **UK Trade Tariff**: Repos oficiales en GitHub: *trade-tariff-backend* y *trade-tariff-frontend*. Muestran cómo modelan CN y medidas. 

- **Fumadocs**: Documentación técnica: https://fumadocs.dev (para MDX/docs).

- **Great Expectations**: https://docs.greatexpectations.io (uso de tests de datos).

- **trade-tariff-backend**: repo [trade-tariff/trade-tariff-backend](https://github.com/trade-tariff/trade-tariff-backend).

- **Otros OSS**: Sitios de Airbyte (https://airbyte.com), Dagster (https://dagster.io), PMTiles (https://github.com/protomaps/PMTiles).

- **Regulaciones**: EUR-Lex (para CN/EU) https://eur-lex.europa.eu/. Ejemplo: Reg.1101/2014 (CN2015) muestra nivel jerárquico y “notas”. Esto demuestra la importancia de modelar cada edición jurídica.  

- **Repositorio arancel-mx**: Se supone público en GitHub. Se recomienda incluir URL en `README` junto a docs (por ejemplo: `https://github.com/aduanamap-mx/arancel-mx`). 

Cada cita en este informe refuerza la necesidad de estándares claros (e.g. Trade Tariff API, Fumadocs). Los planes de acción apalancan la experiencia OSS: por ejemplo, la transición de markdown a Fumadocs se inspira en repos como [fuma-nama/fumadocs][44].

**Conclusión:** Este análisis exhaustivo revela que arancel-mx necesita completar su planeación declarativa y reforzar sus pipelines con tests y controles automáticos. Con las recomendaciones propuestas, se alinea con la arquitectura *source-driven* aprobada para AduanaMap, asegurando datos fiables, rastreables y fáciles de consumir.

**Fuentes citadas:** documentación oficial del Trade Tariff UK, Great Expectations, repos de Fumadocs, entre otras mencionadas en el texto.