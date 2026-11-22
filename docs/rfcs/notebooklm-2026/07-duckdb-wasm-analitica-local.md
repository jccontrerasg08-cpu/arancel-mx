# RFC: DuckDB-WASM local opcional

> Propuesta únicamente de diseño. Prioridad P2; base documental: Gemini Notebook 2026-11-21 y [auditoría de fuentes](../../research/notebooklm-source-audit-2026-11-21.md).

## Existente / no duplicar

El navegador hoy consume API GET-only /data/v1 y Github Releases canónicas. Gemini promete 0 ms de latencia, afirmación imposible de garantizar; no hay integración WASM desplegada.

## Objetivo y alcance

Crear modo SQL avanzado de solo lectura en un Web Worker opt-in, con datos de release fijada y verificable, límites de recursos, fallback a API y pruebas multiplataforma.

## Arquitectura técnica, UX y contratos

- ADR de formatos: comparar conversión DuckDB contra CSV/Parquet/Arrow compatibles con WASM, con fixture pequeña y métricas.
- Verifier de manifest/SHA256 antes de rotular consultas como release_verified; no descargar por defecto el dataset de ~decenas de MB.
- Web Worker con aislamiento, límites de memoria/filas/tiempo, cancelación y bloqueo de SQL que trate recursos fuera de la fuente local; ninguna ejecución en servidor.
- UI progresiva para opt-in, progreso bytes, fallos y límites; fallback a /data/v1; privacidad: ningún historial remoto.
- CSP, crossOriginIsolated cuando aplique, compatibilidad Chromium/Firefox/WebKit y móvil, bundle size, cache por release, TTL/evicción y modo offline verificable.
- Comparativas ejecutables con CLI/Python y mediciones reales cold/warm; no anunciar 0 ms.

## Esquema de ejemplo (no endpoint ni release implementados)

~~~json
{
  "tag": "data-YYYY.MM.DD",
  "mode": "local-opt-in",
  "engine": "duckdb-wasm",
  "verified": false,
  "worker_status": "unsupported|downloading|verifying|ready|failed",
  "limits": {
    "max_rows": 1000,
    "timeout_ms": 30000
  },
  "fallback": "/data/v1"
}
~~~

**Metadatos comunes:** source_url, fecha oficial de publicación, fecha efectiva comprobada si existe, retrieved_at, dataset_version/tag, instrumento, hash SHA-256 real, estado de fuente y distinción entre datos oficiales/declarados/derivados. Nunca inventar ausencias.

## Pruebas/criterios de aceptación

- [ ] Dataset manipulado o hash incorrecto bloquea etiqueta verificada.
- [ ] Mismo fixture produce mismos resultados de lookup que CLI cuando ordenada.
- [ ] Navegador incompatible y memoria insuficiente conservan funcionamiento del buscador.
- [ ] No accesos a red desde consultas ni subida de datos de usuario.
- [ ] Presupuesto de bytes, latencia y RAM documentado y medido.
- [ ] Mantener /data/v1 y las seis piezas canónicas, salvo ADR aprobado por separado.
- [ ] CI reproducible, fallback, límites, rollback, i18n español/inglés y documentación de accesibilidad y desempeño.

## Entregas técnicas sugeridas

1. ADR de cobertura, formatos y compatibilidad con el repositorio actual.
2. PoC offline con fixtures oficiales y umbrales medibles.
3. Integración opt-in tras aprobación del propietario y revisión CI.
4. Pruebas multiplataforma y documentación de uso/errores.

## Pendiente de investigación

Decidir formato interoperable y presupuesto real antes de SDK/producción.

## Fuentes del NotebookLM y fuentes primarias

- Notebook entradas 2,10: DuckDB/CLI/Python y DuckDB-WASM
- https://github.com/jccontrerasg08-cpu/arancel-mx/releases
- https://duckdb.org/docs/stable/clients/wasm/overview

**Inventario:** [42 entradas identificadas](../../research/notebooklm-source-inventory-2026-11-21.json). Respuestas de Gemini no son hechos verificados y materiales Studio no fueron inspeccionados.

## Límite de este PR

El PR contiene sólo especificación, no implementa funciones ni agrega assets a releases. La publicación en GitHub sólo activa revisiones/CI y potencial preview, sin despliegue funcional.
