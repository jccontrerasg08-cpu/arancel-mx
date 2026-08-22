# Observabilidad de la superficie pública

La sonda pública mide únicamente rutas read-only promovidas por Vercel. No publica datos, no sincroniza fuentes, no modifica releases y no convierte una medición puntual en un acuerdo de nivel de servicio.

## Ejecutar una comprobación de contrato

```bash
python scripts/check_public_service.py
```

La comprobación valida metadatos, jerarquía de una ficha, procedencia, notas nacionales y una sugerencia retrieve-only. Las rutas no promovidas no se usan como fallback ni como proxy externo.

## Medir una muestra de latencia

```bash
python scripts/check_public_service.py --latency-samples 3
```

Cada muestra consulta por `GET` las rutas `/v1/meta`, `/v1/search?q=reproductores&limit=1` y `/v1/suggest?q=reproductores&limit=1`. El comando imprime ruta, código HTTP y duración por operación. Sus resultados sirven para comparar cambios o decidir una investigación de base de datos; no bloquean CI ni activan cachés, índices o cambios de ranking.

## Interpretación responsable

Se deben separar arranque frío, red, carga de la función y consulta. Una diferencia de latencia no se corrige con un cambio de SQL o de caché sin una línea base repetible y el plan de consulta de la base de datos operativa. La búsqueda y sugerencias permanecen retrieve-only y no son clasificación de mercancías ni asesoría legal.

## Próxima decisión de automatización

La sonda puede ejecutarse manualmente cuando se revisa una release, o programarse semanalmente como observación no bloqueante. Antes de programarla deben acordarse cadencia, conservación de resultados y canal de revisión; no se deben abrir alertas ni mutar datos por una muestra aislada.
