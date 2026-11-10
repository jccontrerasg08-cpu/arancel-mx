# Estado de las reformas arancelarias 2026

Este documento resume el alcance de las modificaciones a la Tarifa (LIGIE/TIGIE) que entraron en vigor en 2026 y cómo se reflejan en `arancel-mx`.

## Instrumentos principales

| Instrumento | Publicación DOF | Vigencia | Alcance aproximado |
|---|---|---|---|
| Reforma LIGIE (Congreso) | 29 de diciembre de 2025 | 1 de enero de 2026 | ~1.463 fracciones (tasas 5 %–50 %) |
| Decreto de modificaciones | 23 de abril de 2026 | 24 de abril de 2026 | ~185 fracciones (tasas 5 %–35 %) |

Las cifras exactas y la lista de fracciones afectadas viven en el inventario de instrumentos y en la release verificada. Consulta siempre el DOF y el SNICE como fuentes primarias.

## Cómo comprobarlo en arancel-mx

```bash
# Descarga y verifica la release actual
arancel-mx data download
arancel-mx data verify

# Busca una fracción y revisa su tasa e historia
arancel-mx ficha 85171301
arancel-mx provenance 85171301

# Cobertura NICO (lag upstream conocido)
arancel-mx data nico-coverage
```

La página de cambios del hub (`/changes`) lista los instrumentos del DOF que tocan la Tarifa. Cada publicación incluye enlace al DOF y las fracciones afectadas.

## Notas importantes

- `arancel-mx` no interpreta ni clasifica. Reproduce la Tarifa verificada con procedencia.
- El lag de NICO (fuente oficial aún en material de abril 2024 para algunas fracciones nuevas) se documenta explícitamente; no se inventan códigos.
- Cita siempre el tag `data-YYYY.MM.DD` y el SHA-256 de la release.

**Última revisión de este documento:** 2026-11-09  
**Dataset de referencia:** data-2026.11.09
