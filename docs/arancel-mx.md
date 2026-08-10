# arancel-mx: operación y trazabilidad

`arancel-mx` mantiene TIGIE, fracciones de ocho dígitos y NICO de diez dígitos como datos legales versionados. La Cámara de Diputados es el ledger oficial accesible para descubrir el texto vigente, reformas, decretos y documentos complementarios; el DOF aporta la evidencia de publicación y vigencia; SNICE aporta los XLSX operativos. Una diferencia entre esas fuentes bloquea la publicación.

## Separación de dominios

- `arancel_mx` contiene exclusivamente la clasificación y tarifas canónicas con historia temporal y procedencia.
- las Notas Nacionales se almacenan en tablas/vistas legales separadas y participan en la interpretación, no como tasas inventadas;
- las propuestas NICO nunca se mezclan con el NICO vigente;
- los indicadores ponderados viven en el espacio analítico y no alteran la tarifa legal.

## Actualización diaria

El workflow `.github/workflows/arancel-mx-daily.yml` se ejecuta diariamente y también admite ejecución manual. `python comex.py arancel-check` compara sin escribir, salvo que se indique `--report-path`. `python comex.py arancel-update` calcula eventos, elimina trabajos duplicados, ejecuta la unión necesaria y publica una sola vez. `python comex.py arancel-status` muestra el último ledger validado.

La detección compara fechas, estructura documental, URLs y hashes disponibles. Los eventos desconocidos, la falta de evidencia DOF, una cuarentena bloqueante, pruebas fallidas, rutas fuera de la lista permitida o un cambio concurrente de `origin/main` conservan intacta la última versión válida.

## Captura y reproducción

Cada descarga se guarda bajo fecha, fuente y función documental con SHA-256 y manifiesto compacto. Si cambian los bytes el mismo día se conserva una segunda captura con sufijo de hash. Un parseo sólo se reutiliza cuando coinciden `source_sha256`, `parser_version`, `schema_version` y `registry_version`. Los XLSX retienen valor original, hoja y fila; no se rellenan códigos completos y sólo se permite completar con cero el componente NICO registrado de dos posiciones.

La distribución embebida está en `data/embedded/latest/`. Se puede consultar sin red:

```sql
SELECT code, description, igi_text, effective_from
FROM 'data/embedded/latest/arancel_mx.duckdb'.arancel_mx
WHERE code = '01012101';
```

El manifiesto incluye versión, fecha efectiva, conteo, estado de validación y hashes. El archivo DuckDB debe permanecer por debajo de 95 MiB.

## Recuperación

Cuando una ejecución se bloquea, revise `data/arancel_mx/update_summary.json`, la cuarentena y la conciliación DOF/SNICE. Actualice el registro de fuentes sólo mediante un cambio revisado y versionado. Tras resolver la discrepancia, ejecute `arancel-check`, luego `arancel-update`, todas las pruebas y finalmente el publicador. Nunca se fuerza un push ni se sustituye una versión válida con un candidato fallido.
