# Visión del proyecto

`arancel-mx` es la capa pública y reusable de datos arancelarios mexicanos del proyecto: observa fuentes oficiales, conserva evidencia, normaliza LIGIE/NICO y publica artefactos verificables que otras herramientas pueden consumir sin rehacer el pipeline.

**[Hub público](https://arancel-mx.vercel.app/)** · **[Documentación API](https://arancel-mx.vercel.app/documentation)** · **[Última release](https://github.com/jccontrerasg08-cpu/arancel-mx/releases/latest)** · **[Centro de documentación](README.md)**

## El problema que resuelve

Un XLSX, PDF o página oficial aislada no responde por sí solo preguntas esenciales para una capa de datos reusable: qué fuente se observó, cuándo se capturó, qué versión era aplicable, cómo se relaciona con otras publicaciones, qué transformación produjo cada fila y qué bytes terminaron publicados.

`arancel-mx` separa ese problema del resto de una aplicación de comercio exterior. Su trabajo es producir una representación técnica consistente y auditable; dashboards, ETL, RAG, automatizaciones o sistemas de consulta quedan libres para consumirla sin duplicar parsers ni crear una copia divergente de LIGIE/NICO.

## Qué posee el proyecto

La frontera del proyecto incluye:

- registro y captura de fuentes declaradas;
- identidad de fuente, URL, tiempo de captura y SHA256;
- reconciliación y gates fail-closed;
- parseo y normalización de HS, fracción mexicana y NICO;
- DuckDB canónico y exportaciones CSV/JSON;
- manifest, checksums y archivo de fuentes capturadas;
- CLI y API Python para consumidores;
- API HTTP pública GET-only/read-only;
- releases de dataset inmutables y verificables.

No intenta sustituir un sistema integral de comercio exterior, un motor de cumplimiento ni una resolución de clasificación arancelaria. Tampoco convierte una búsqueda o sugerencia en asesoría legal.

## Del documento a la release

```text
Diputados / DOF / SNICE / fuentes registradas
                     ↓
             source registry
                     ↓
          captura + identidad + SHA256
                     ↓
          reconciliación y validación
                     ↓
             normalización canónica
                     ↓
                 DuckDB
             ↙       ↓       ↘
           CSV      JSON    manifest
                     ↓
       bundle verificable + checksums
                     ↓
        GitHub Release data-YYYY.MM.DD
```

La publicación es fail-closed: una discrepancia relevante, un parser ambiguo o una validación fallida bloquea la publicación en lugar de producir datos silenciosamente corregidos.

## Superficies de consumo

Una misma release puede consumirse de varias formas, según la tarea:

| Intención | Superficie |
|---|---|
| Explorar sin instalar nada | [Hub web de Vercel](https://arancel-mx.vercel.app/) |
| SQL, BI, notebooks y ETL | DuckDB / CSV / JSON de GitHub Releases |
| Consultas de terminal | CLI `arancel-mx` |
| Integración dentro de Python | `Dataset` y tipos públicos |
| Servicios y UIs | HTTP `/v1`, GET-only/read-only |
| Auditoría | `manifest.json`, `SHA256SUMS`, procedencia y fuentes capturadas |

La versión del paquete Python y la identidad del dataset son conceptos distintos. El paquete evoluciona con versiones PEP 440; los datos se identifican mediante releases inmutables `data-YYYY.MM.DD`.

## Central Hub en Vercel

El dominio público principal es `https://arancel-mx.vercel.app/`. La superficie combina dos piezas sin cambiar la fuente canónica de datos:

```text
GitHub Release verificada
          ↓
sincronización operacional idempotente
          ↓
        Neon
          ↓
Vercel: metadatos, búsqueda, ficha, evidencia activa y documentación local
```

`/v1/meta`, `/v1/search`, `/v1/suggest`, `/v1/ficha/{code}`, la jerarquía, `provenance`, notas nacionales y `/readyz` se resuelven mediante una proyección operacional read-only sincronizada desde releases verificadas. `/documentation` presenta el hub local de rutas y límites; las rutas `/v1/*` no promovidas se resuelven localmente sin proxy externo. **Neon y Vercel son superficies de servicio, no sustituyen la release verificable como fuente de verdad.**

Para consumidores, esto permite usar un solo origen público:

```bash
export ARANCEL_MX_API_URL="https://arancel-mx.vercel.app"
curl "$ARANCEL_MX_API_URL/readyz"
curl "$ARANCEL_MX_API_URL/v1/meta"
curl "$ARANCEL_MX_API_URL/v1/lookup/8517130100"
```

## Modelo de confianza

El proyecto prefiere evidencia verificable sobre claims de frescura. Una release puede relacionarse con:

- la identidad y URL de sus fuentes;
- hashes de los bytes capturados;
- `retrieved_at`;
- evidencia de reconciliación;
- commit y ejecución de GitHub Actions;
- manifest de release;
- checksums de los assets publicados.

Por eso, “última release” significa la última publicación que pasó los gates definidos, no una promesa de que toda publicación jurídica externa haya sido interpretada automáticamente.

## Dónde profundizar

- [Inicio rápido](consumer-quickstart.md): instalar, descargar, verificar y consultar.
- [Consumo externo](external-consumption.md): archivos, Python y HTTP.
- [Modelo de datos](data-model.md): tablas y semántica de release.
- [Roles de fuentes oficiales](official-source-roles.md): autoridad y función de cada fuente.
- [Fuentes y reconciliación](sources.md): cadena de confianza y gates.
- [Proceso de release](release-process.md): automatización y publicación.
- [Marca y presentación](brand.md): cómo contar el proyecto sin exagerar capacidades.
- [Centro de documentación](README.md): índice completo por intención.
