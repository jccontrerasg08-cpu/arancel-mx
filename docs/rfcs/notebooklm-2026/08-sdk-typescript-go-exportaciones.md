# RFC: SDK TypeScript/Go y Parquet, SQLite, JSON-LD

> Propuesta únicamente de diseño. Prioridad P2; base documental: Gemini Notebook 2026-11-21 y [auditoría de fuentes](../../research/notebooklm-source-audit-2026-11-21.md).

## Existente / no duplicar

Existe SDK Python/CLI y contrato de exactamente seis assets en la release, con SHA256SUMS; no existen npm/Go ni exportaciones adicionales certificadas. Evitar tocar el source_registry oficial.

## Objetivo y alcance

Crear clientes verificables TS/Go y derivados analíticos opcionales que reutilicen el contrato estático y no rompan la release o versión de los datos.

## Arquitectura técnica, UX y contratos

- Especificar funciones compartidas list/pin/download/verify/lookup/search/notes/provenance/cache, con tags inmutables.
- TS para Node/ESM, navegadores sobre /data/v1, tipos estáticos, integridad y manejo de 404/offline; sin volver a /v1 dinámico.
- Go: proponer módulo separado o anidado clients/go, dado que la raíz es paquete Python; fijar ruta real de módulo mediante ADR.
- Parquet, SQLite, JSON-LD como archivos DERIVADOS laterales con sha, esquema, tipos, nullability, orden, URIs y procedencia, sin modificar silenciosamente lista de seis assets obligatorios.
- Pruebas de paridad con Python y fixtures de tasas específicas/textos, unicode, zero/null; fail-closed en datos o hashes inválidos.
- Versionar SDK semver separado de data-YYYY.MM.DD; documentar compatibilidad y política de soporte, offline/cache y supply chain/SBOM.
- Evaluar publicación en npm y Go proxy como gate independiente con credenciales y aprobación; esta propuesta no publica nada.

## Esquema de ejemplo (no endpoint ni release implementados)

~~~json
{
  "client_contract": {
    "release": "data-YYYY.MM.DD",
    "verified": true,
    "api": "/data/v1",
    "methods": [
      "list",
      "download",
      "verify",
      "lookup",
      "search",
      "notes",
      "provenance"
    ]
  },
  "derived_formats": [
    "parquet",
    "sqlite",
    "jsonld"
  ],
  "status": "optional_not_part_of_six_canonical_assets"
}
~~~

**Metadatos comunes:** source_url, fecha oficial de publicación, fecha efectiva comprobada si existe, retrieved_at, dataset_version/tag, instrumento, hash SHA-256 real, estado de fuente y distinción entre datos oficiales/declarados/derivados. Nunca inventar ausencias.

## Pruebas/criterios de aceptación

- [ ] Hash inválido no promueve caché ni etiqueta verified.
- [ ] Paridad fixture TS/Go/Python y regresiones de contrato.
- [ ] SQLite y Parquet conservan texto tasa, nulos y fechas; JSON-LD validado.
- [ ] Packaging reproducible y pruebas en node/browser/go.
- [ ] No usar npm install arancel-mx ni go get hasta publicar artefactos reales.
- [ ] Mantener /data/v1 y las seis piezas canónicas, salvo ADR aprobado por separado.
- [ ] CI reproducible, fallback, límites, rollback, i18n español/inglés y documentación de accesibilidad y desempeño.

## Entregas técnicas sugeridas

1. ADR de cobertura, formatos y compatibilidad con el repositorio actual.
2. PoC offline con fixtures oficiales y umbrales medibles.
3. Integración opt-in tras aprobación del propietario y revisión CI.
4. Pruebas multiplataforma y documentación de uso/errores.

## Pendiente de investigación

Los bots de cambios DOF y releases ya existen; extender sin duplicar. Contratos de assets requieren ADR.

## Fuentes del NotebookLM y fuentes primarias

- Notebook entradas 2,10: npm, Go, DuckDB/CSV/JSON, Parquet, SQLite, JSON-LD y Data Bots.
- https://github.com/jccontrerasg08-cpu/arancel-mx
- https://github.com/jccontrerasg08-cpu/arancel-mx/releases

**Inventario:** [42 entradas identificadas](../../research/notebooklm-source-inventory-2026-11-21.json). Respuestas de Gemini no son hechos verificados y materiales Studio no fueron inspeccionados.

## Límite de este PR

El PR contiene sólo especificación, no implementa funciones ni agrega assets a releases. La publicación en GitHub sólo activa revisiones/CI y potencial preview, sin despliegue funcional.
