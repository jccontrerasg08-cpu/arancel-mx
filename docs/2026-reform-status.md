# Estado de las reformas arancelarias 2026

Resumen de los instrumentos de tasa general que el registro empaquetado
[`legal_instruments.json`](../src/arancel_mx/sources/legal_instruments.json)
(`version: 2026-10-30`) usa para fechar el IGI/IGE. Las cifras de filas son
el número de fracciones en ese instrumento, no una estimación.

La release verificada sigue siendo la fuente de las tasas vigentes. Este
documento no sustituye al DOF ni al SNICE.

## Instrumentos con efecto en 2026

| Id | DOF | Entrada en vigor | Fin | Filas | Qué es |
|---|---|---|---|---:|---|
| `ref02` | 2025-12-29 | 2026-01-01 | — | 1,463 | Reforma de diversas fracciones de la Tarifa de la LIGIE |
| `ref01` | 2025-07-21 | 2026-01-17 | — | 11 | Reforma LIGIE (totoaba). El NICO oficial puede no traer descendientes de estas fracciones |
| `tarifa15` | 2026-04-23 | 2026-04-24 | — | 185 | Modificación de la Tarifa y del Decreto PROSEC |
| `tarifa16` | 2026-10-13 | 2026-10-14 | 2031-10-14 | 1 | Tasa temporal de `9803.00.01` (partes para ensamble automotriz) |

Tasas temporales que el registro da por terminadas el 2026-04-23:

| Id | DOF | Entrada en vigor | Fin | Filas |
|---|---|---|---|---:|
| `tarifa09` | 2024-04-22 | 2024-04-23 | 2026-04-23 | 544 |
| `tarifa11` | 2024-12-19 | 2024-12-20 | 2026-04-23 | 155 |

`tests/docs/test_2026_reform_status.py` falla si esos identificadores, fechas
o conteos dejan de coincidir con el registro.

## Cómo comprobar una fracción

```bash
arancel-mx data download
arancel-mx data verify
arancel-mx ficha 85171301
arancel-mx provenance 85171301
```

`ficha` muestra el IGI/IGE oficial del dataset verificado. No calcula un
arancel preferencial ni decide si una mercancía califica.

La página de cambios del hub (`/changes`) lista instrumentos del DOF. Cada
publicación enlaza la edición y las fracciones que el registro asocia.

## Qué no hace este documento

- No interpreta reglas de origen ni tratados.
- No rellena NICO que la fuente oficial no publicó.
- No afirma que cada fila de un instrumento sea un alza de tasa: una fila es
  una fracción mencionada por ese instrumento.
