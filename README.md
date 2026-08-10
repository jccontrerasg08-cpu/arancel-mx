# arancel-mx

Herramientas abiertas para consultar y analizar comercio exterior de México,
incluyendo LIGIE, fracciones arancelarias, NICO, series del Banco de México y
fuentes públicas de ANAM, DOF, SNICE y VUCEM.

El repositorio contiene una aplicación Dash, utilidades de línea de comandos,
validaciones y trazabilidad de fuentes. El código se publica bajo
[Apache-2.0](LICENSE); los datos y componentes de terceros conservan sus
propios términos, descritos en [NOTICE](NOTICE).

> Este proyecto es independiente y no está afiliado ni respaldado por una autoridad mexicana. Su contenido es informativo y no constituye asesoría legal, aduanera, fiscal ni profesional. Confirma siempre los datos contra la publicación oficial aplicable.

## Inicio rápido

Requiere Python 3.12 o posterior.

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --requirement requirements.txt
Copy-Item .env.example .env
.\.venv\Scripts\python.exe run.py
```

En Linux o macOS:

```bash
python3 -m venv .venv
.venv/bin/python -m pip install --requirement requirements.txt
cp .env.example .env
.venv/bin/python run.py
```

Abre `http://localhost:8050`. La copia incluida de
`data/comercio_exterior.json` permite iniciar sin credenciales. Las funciones
que consultan APIs externas permanecen opcionales y muestran un estado limitado
cuando no están configuradas.

## Credenciales opcionales

`.env.example` contiene únicamente marcadores. Copia el archivo como `.env` y
configura tus propias credenciales localmente:

```dotenv
BANXICO_TOKEN=PASTE_YOUR_BANXICO_TOKEN_HERE
GROQ_API_KEY=PASTE_YOUR_GROQ_API_KEY_HERE
```

`.env` y `token.txt` están ignorados por Git. No incluyas tokens en commits,
issues, capturas de pantalla ni argumentos de línea de comandos.

## Comandos principales

```bash
# Ejecutar pruebas
python -m pytest -p no:cacheprovider -q

# Inicializar el warehouse local ignorado por Git
python comex.py init-db
python comex.py warehouse-refresh
python comex.py warehouse-status

# Actualizar el caché público de series de Banxico
python banxico_sie.py

# Consultar y preparar fuentes públicas
python comex.py etl run snice-nico
python comex.py etl run vucem-tigie
python comex.py etl run dof-comex
python comex.py etl status

# Consultar el corpus legal incluido
python comex.py legal-corpus-status
python comex.py legal-corpus-search "Anexo 22 identificador NOM"

# Health check con la aplicación activa
curl http://localhost:8050/healthz
```

## Arancel MX canónico

El pipeline normaliza fuentes oficiales en registros trazables por código HS,
fracción de ocho dígitos y NICO. Los manifiestos registran autoridad, URL,
fecha de observación y SHA-256 de cada fuente.

Las bases DuckDB, descargas originales y demás datos generados no se guardan en
el historial Git. Se crean localmente o se distribuyen como activos versionados
en GitHub Releases, acompañados por manifiesto y checksums. Esto evita inflar el
repositorio y permite verificar cada publicación.

Ejemplo de consulta después de instalar una base publicada:

```sql
SELECT code, description, unit_code, igi_text, ige_text
FROM arancel_mx
WHERE code = '84181001';
```

## Estructura

```text
src/comex/          ETL, DuckDB, catálogos, trazabilidad y búsquedas
src/charts/         Gráficas Plotly
src/components/     Componentes Dash
src/data_service.py Acceso SQL, API y caché JSON
data/legal_corpus/  Guías y referencias públicas
tests/              Pruebas y fixtures deterministas
```

Los directorios `data/raw/`, `data/state/`, `data/alerts/`, las bases DuckDB y
los archivos de configuración personal son locales y están ignorados.

## Fuentes

- Banco de México: series del SIE.
- Cámara de Diputados: texto vigente de la LIGIE.
- Diario Oficial de la Federación: publicación y efectos jurídicos.
- SNICE y VUCEM: catálogos operativos LIGIE/NICO.
- SAT y ANAM: información pública de aduanas y recaudación.
- World Bank/WITS: contexto HS internacional; no es autoridad jurídica mexicana.

La procedencia detallada de las fuentes arancelarias está en
[`data/arancel_mx/source_registry.json`](data/arancel_mx/source_registry.json) y
[`docs/arancel-mx.md`](docs/arancel-mx.md).

## Contribuir y reportar problemas

Lee [CONTRIBUTING.md](CONTRIBUTING.md) antes de abrir un pull request. Los
cambios de datos o activos deben incluir procedencia y términos de
redistribución verificables.

Usa los formularios de Issues para errores y propuestas. Para vulnerabilidades,
sigue [SECURITY.md](SECURITY.md) y no publiques detalles sensibles en un issue.

Este repositorio público acepta forks y pull requests, pero no tiene acceso de
escritura ni sincronización automática con ningún repositorio privado.

## Licencia

Código propio: [Apache-2.0](LICENSE). Consulta [NOTICE](NOTICE) para atribuciones
y materiales de terceros.
