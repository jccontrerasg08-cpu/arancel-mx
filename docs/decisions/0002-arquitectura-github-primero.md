# Decisión 0002: GitHub como origen y servidor de datos; Vercel sólo para el frontend

- **Estado:** aceptada
- **Fecha:** 2026-10-16
- **Responsable:** @jccontrerasg08-cpu
- **Revisión:** aprobada por el propietario el 2026-10-16 («approve everything … not everything in vercel, just the frontend»)
- **Reemplaza:** la ubicación de la capa de vigilancia de la [decisión 0001](0001-vigilancia-dof-sidof.md); el resto de 0001 sigue vigente.

## Contexto

Hoy la superficie pública depende de cinco plataformas:

| Pieza | Dónde vive hoy |
|---|---|
| Sitio y explorador | Vercel, estático (`website/`) |
| API `/v1` | Funciones Python de Vercel (`api/operational.py`) sobre Neon Postgres |
| Sincronización de datos a Neon | Vercel Cron semanal (`api/sync_operational.py`) |
| API de respaldo | Railway (FastAPI) y FastAPI Cloud |
| Construcción, certificación y releases | GitHub Actions y GitHub Releases |

Las funciones de Vercel tienen límites de duración, invocaciones y cron (en Hobby, una ejecución diaria con margen de una hora y sin reintentos). Neon y Railway añaden credenciales, costos y fallas posibles sin aportar datos que no estén ya en la release inmutable de GitHub.

Una medición sobre `data-2026.09.14` (26,641 registros vigentes) mostró que:
- generar un archivo por código y por ruta (`lookup`, `ficha`, `parent`, `children`, `provenance`) produce unos 133,000 archivos y 139 MB, y tarda alrededor de una hora;
- en cambio, todos los registros de un capítulo comparten el prefijo HS2, de modo que `lookup`, `ficha`, `parent` y `children` se pueden resolver desde un solo archivo por capítulo.

La búsqueda actual (`consumer.query.search`) ya recorre en Python todos los registros vigentes, así que puede reproducirse en el navegador sobre un índice compacto.

## Decisión

1. **GitHub guarda todo y sirve los datos.**
   - Las **releases inmutables** siguen siendo la fuente de verdad: DuckDB, CSV, JSON, manifest y `SHA256SUMS`.
   - **GitHub Pages** publica, por cada release certificada, una API estática de solo lectura generada con los mismos modelos de respuesta de `/v1`:
     - `static/v1/meta.json`, `sections.json` y `chapters.json`;
     - por capítulo HS2, `records/{hs2}.json`, `provenance/{hs2}.json` y `national-notes/{hs2}.json`;
     - `search-index.json` y un `manifest.json` con el SHA-256 de cada archivo.
   - Pages responde con CORS abierto, por lo que el frontend y terceros pueden consumirla directamente.
2. **GitHub Actions hace todo el cómputo, sin flujos nuevos.**
   - El pipeline oficial pasa a correr a diario. Su primer paso consulta SIDOF (`arancel_mx.sources.sidof`) y el libro de fracciones de SNICE y termina en segundos si no hay nada nuevo.
   - Si encuentra un instrumento candidato, abre un issue: esa es la confirmación humana.
   - Si cambió la fuente, construye, certifica, publica la release y despliega Pages.
   - El workflow semanal desaparece porque queda absorbido por el diario.
3. **Vercel sirve sólo el frontend estático.** El explorador lee la API estática con un cliente JavaScript que reproduce `lookup`, `ficha`, `parent`, `children`, `provenance` y la búsqueda, verificado contra fixtures generados en Python.
4. **Se retiran Neon, Railway, FastAPI Cloud y las funciones y el cron de Vercel**, siguiendo la [política de compatibilidad](../compatibility.md) para `/v1`:
   - Las rutas dinámicas `/v1/*` siguen funcionando durante la ventana anunciada y responden con los encabezados `Deprecation`, `Sunset` y `Link` hacia el reemplazo estático.
   - Fecha de retiro propuesta: **2027-01-31**.
   - Después de esa fecha, Vercel deja de desplegar funciones.
   - El servidor FastAPI sigue en el paquete (`arancel_mx.api`) para quien quiera alojarlo por su cuenta sobre una release.

**Criterio observable:**
- el sitio en producción funciona con las funciones de Vercel desactivadas;
- cada archivo de la API estática coincide con el SHA-256 de su manifest;
- las respuestas estáticas son idénticas a las de `/v1` para un conjunto fijo de códigos y consultas.

## Alternativas

- **Mantener `/v1` dinámico en Vercel.** Conserva límites, Neon y el cron frágil que motivan este cambio.
- **Un archivo por código y ruta en Pages.** Funciona, pero son unos 133,000 archivos, 139 MB y una hora de generación por release.
- **DuckDB-WASM leyendo la release directamente.** Es atractivo, pero las descargas de GitHub Releases no envían CORS y el motor pesa varios MB en el navegador.
- **Cloudflare (Workers, R2 y Pages).** Añade otra plataforma; el objetivo es reducirlas.

## Compatibilidad

- **Biblioteca, CLI y dataset:** sin cambios. Se añade el comando `arancel-mx static-api build`.
- **HTTP `/v1`:** con deprecación anunciada y reemplazo documentado; sin retiro antes de 2027-01-31.
- **Configuración que hace el propietario:** activar GitHub Pages con origen «GitHub Actions» en la configuración del repositorio y, al terminar la ventana, eliminar las variables de Neon y los proyectos de Railway y FastAPI Cloud.

## Consecuencias y seguimiento

1. Exportador `arancel_mx.static_api` con pruebas de paridad contra los modelos de `/v1`.
2. Cliente estático del frontend con fixtures de paridad generados en Python.
3. Despliegue a Pages dentro del pipeline oficial y vigilancia diaria SIDOF/SNICE con early exit.
4. Encabezados de deprecación en `/v1`, entrada de changelog y guías actualizadas.
5. Tras el 2027-01-31: retirar `api/`, `crons`, Neon, Railway y FastAPI Cloud.
