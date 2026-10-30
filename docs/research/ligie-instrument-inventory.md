# Inventario de instrumentos de la LIGIE 2022 (compuerta 1)

Este documento registra cada instrumento del DOF que creó o modificó la LIGIE 2022 y el Acuerdo NICO, y lo contrasta con el dataset publicado. Es la base de la compuerta 1 del [programa de profundidad](../depth-program.md) y es para quien construya el motor de reproducción o revise la vigilancia del DOF.

## Alcance y nivel de verificación

- **Observado:** 2026-10-16
- **Registro primario:** Cámara de Diputados, [índice de reformas de la LIGIE 2022](https://www.diputados.gob.mx/LeyesBiblio/ref/ligie_2022.htm). Última reforma a la ley: DOF 2025-12-29. Último cambio a la Tarifa: DOF 2026-10-13.
- **Copia legible por máquina:** [`ligie-instrument-inventory.json`](ligie-instrument-inventory.json)
- **Nivel de verificación: texto leído, sin verificación de bytes.** El texto de cada instrumento se leyó en la copia en PDF de la publicación del DOF que ofrece la Cámara de Diputados, mediante un servicio externo de descarga, porque el sandbox de la sesión no alcanza los hosts oficiales. Los hashes SHA-256 y las copias originales del DOF siguen pendientes (ver «Pendientes»).

Este inventario reemplaza la lista semilla anterior, basada en búsquedas. Esa lista tenía cinco errores, todos corregidos aquí:

- 2023-12-27 y 2025-12-31 son decretos de exención de la canasta básica, no reformas a la Tarifa.
- 2023-06-23 es el decreto del maíz blanco.
- 2024-08-26 es una modificación al PROSEC y no está en el registro de la LIGIE.
- 2025-12-29 es una reforma de ley del Congreso, no un decreto del Ejecutivo.
- Faltaba la reforma de ley del 2025-07-21.

## Instrumentos

La edición sale del encabezado de la primera página (VES = vespertina, MAT = matutina). Dentro de cada sección, los instrumentos siguen el orden del registro.

| ID | Fecha DOF | Ed. | Instrumento | Entrada en vigor | Fin | Filas |
|---|---|---|---|---|---|---|
| orig | 2022-06-07 | | Expedición de la LIGIE 2022 | 10 días hábiles después del aviso de preparación del SAT (fecha por confirmar) | | base |
| ref01 | 2025-07-21 | MAT | Reforma de ley: fracciones de totoaba, nota 4 del capítulo 03 | 180 días después (≈2026-01-17) | | 11 códigos |
| ref02 | 2025-12-29 | MAT | Reforma de ley: tasas de la Tarifa | 2026-01-01 | permanente | 1,463 |
| tarifa01 | 2022-11-18 | VES | Exenciones temporales a la importación | con la LIGIE | 2023-05-17, abrogado por tarifa03 | 72 |
| tarifa02 | 2022-11-18 | VES | Tarifa + automotriz, IMMEX, frontera, Chetumal, PROSEC, vehículos usados, cupos | con la LIGIE | escalonado/parcial | grande |
| tarifa02 mod01 | 2024-04-22 | MAT | Modifica el artículo Décimo Cuarto (cupos) de tarifa02 | 2024-04-23 | | |
| tarifa02 mod02 | 2026-03-26 | MAT | Agrega los rieles 7302.10.02 a los cupos, Ex. dentro de cupo | 2026-03-26 | | 1 |
| tarifa03 | 2023-01-06 | VES | Decreto de exención de la canasta básica | 2023-01-07 | prorrogado al 2026-12-31 | 133 |
| tarifa04 | 2023-01-16 | VES | Exportación de maíz blanco 50 % | 2023-01-17 | 2023-06-30, abrogado por tarifa06 | 1 |
| tarifa05 | 2023-05-18 | VES | Canasta básica: agrega tilapia, retira trigo | 2023-05-18 | | 6 |
| tarifa06 | 2023-06-23 | VES | Maíz blanco 50 % importación / 50 % exportación | 2023-06-24 | 2023-12-31 | 1 |
| tarifa07 | 2023-08-15 | VES | Tasas temporales en 392 fracciones | 2023-08-16 | abrogado por tarifa09 | 392 |
| tarifa08 | 2023-12-27 | MAT | Canasta básica prorrogada al 2024-12-31 | 2023-12-28 | | 0 |
| tarifa09 | 2024-04-22 | VES | Tasas temporales en 544 fracciones (5–50 %) | 2024-04-23 | 2026-04-23 | 544 |
| tarifa10 | 2024-05-08 | VES | Retira el aluminio de tarifa09; sulfato de amonio 35 % | 2024-05-09 | | 3 |
| tarifa11 | 2024-12-19 | VES | 35 % prendas de vestir / 15 % textiles; anexos IMMEX | 2024-12-20 | 2026-04-23 | 155 |
| tarifa12 | 2024-12-31 | VES | Cambios a la canasta básica, prorrogada al 2025-12-31 | 2025-01-01 | | 35 |
| tarifa13 | 2025-11-10 | VES | Azúcar 156 % / 210.44 % | 2025-11-11 | permanente | 8 |
| tarifa14 | 2025-12-31 | MAT | Retiros de la canasta básica, prorrogada al 2026-12-31 | 2025-12-31 (art. 1 desde el 2026-01-01) | | 33 |
| tarifa15 | 2026-04-23 | VES | 185 fracciones al 5–35 % + PROSEC | 2026-04-24 | permanente | 185 |
| tarifa16 | 2026-10-13 | MAT | 9803.00.01 partes para ensamble automotriz → Ex. | 2026-10-14 | 2031-10-14 (cinco años) | 1 |
| acuerdo01 | 2022-07-14 | | Tablas de correlación TIGIE 2020–2022 | | | sin leer |
| acuerdo02 | 2022-08-22 | MAT | NICO y tablas de correlación | con la LIGIE | | 12,455 pares |
| acuerdo02 mod01 | 2023-06-30 | MAT | NICO: +53, −18 | | | |
| acuerdo02 mod02 | 2024-03-22 | MAT | NICO: +6, −3 | 2024-03-22 | | |
| acuerdo03 | 2022-12-02 | | Notas Nacionales | | | sin leer |

«Filas» cuenta las filas arancelarias que recuperó el parser local. Coinciden con los conteos que cada decreto declara sobre sí mismo (544, 155, 1,463, 185).

## Verificaciones contra el dataset publicado `data-2026.09.14`

| Verificación | Resultado |
|---|---|
| Tasa vigente de cada fracción fijada por tarifa10, tarifa13, ref02, ref01 y tarifa15, aplicadas en orden de entrada en vigor | **1,667 / 1,667 coinciden** (IGI e IGE) |
| NICO creados por acuerdo02 mod01/mod02 presentes | 59 / 59 |
| NICO suprimidos por acuerdo02 mod01/mod02 ausentes | 21 / 21 |
| Tasas temporales (tarifa09 menos 2 retiradas, más tarifa11) que vencieron el 2026-04-23 sin renovación | **0 de 697**: todas fueron renovadas por ref02 o tarifa15. La lectura anterior de «reversión automática», tomada de comentarios secundarios, no tiene sustento en los textos. |
| Cambios de tasa de tarifa15 frente a la tasa que reemplazó | 0 de 180 fracciones coincidentes; 5 fijadas por primera vez, todas coinciden |
| 9803.00.01 después de tarifa16 (en vigor desde el 2026-10-14) | **Desactualizada**: el dataset y la API en vivo muestran IGI 10; el decreto fija Ex. El pipeline lee las tasas del libro de SNICE, así que el dataset sólo cambia cuando SNICE lo vuelve a publicar; el pipeline no lee decretos. |
| Fracciones sin ningún NICO | 49. 43 son fracciones de importación prohibida que tampoco tienen NICO en acuerdo02 (consistente). **6 son las fracciones de totoaba creadas por ref01** (0302.89.02, 0302.99.04, 0303.89.02, 0303.99.04, 0304.89.01, 0304.89.02); ningún instrumento NICO del registro las cubre. |
| Campos de vigencia en el dataset | `effective_from`, `effective_to`, `rate_effective_*` y `published_at` están vacíos en las 26,641 filas vigentes; `validity_basis` es `observed_snapshot`. Ésta es la brecha que cierra el frente de trabajo A. |
| Texto de la descripción | 0304.89.02 dice «manejo **intesivo**» en el dataset; el texto del DOF dice «manejo intensivo». Primera entrada del registro de discrepancias. |

## Qué cambia en el plan

- **Tipos de operación que necesita el motor de reproducción (A2)**, todos observados en instrumentos reales:
  - `modify_rate`, `create`, `temporary_rate` con fecha de fin fija o con duración, `staged_rate` (desgravación escalonada del acero en tarifa02), `abrogation`, `derogation` de artículos de otro decreto (tarifa07 → tarifa02);
  - `remove_from_decree` (tarifa10 → tarifa09), `extend_validity` (canasta básica), `quota_rate` (artículo Décimo Cuarto de tarifa02) y, para NICO, `create`/`suppress`/`annotation`;
  - entrada en vigor por fecha fija, por el día de la publicación o el siguiente, por una duración («180 días») o por un evento externo (el aviso de preparación del SAT).
- **Los programas sectoriales viajan con la Tarifa.** tarifa02, tarifa07, tarifa09, tarifa11 y tarifa15 también modifican el PROSEC o el IMMEX, y las exenciones de la canasta básica forman su propia cadena de decretos. D2 debería seguir justo después del núcleo.
- **Las tasas de cupo están separadas de las tasas generales.** 7302.10.02 muestra al mismo tiempo 20 % (general) y Ex. (dentro de cupo). El modelo necesita una capa de medidas separada (D3), no una sobrescritura.

## Pendientes

1. **Captura de bytes y SHA-256:** obtener el archivo Word y el PDF de la edición firmada de cada instrumento mediante los servicios de SIDOF (`/documentos/doc/{codNota}`, `/documentos/pdf/{codDiario}`; ver la [decisión 0001](../decisions/0001-vigilancia-dof-sidof.md)), o ejecutar `scripts/capture_instrument_research.py` localmente para las copias de la Cámara de Diputados.
2. ~~**Fecha de entrada en vigor de la LIGIE 2022.**~~ Resuelto (2026-10-30): **2022-12-12**. La Cuarta Resolución de Modificaciones a las RGCE para 2022 (DOF 2022-12-05), artículo segundo, determinó que los sistemas estaban listos; la Secretaría de Economía lo cita en el DOF (nota 5684463, punto 15). La Tarifa original y las demás se leyeron completas desde los PDF capturados por GitHub Actions (8,177 fracciones en el texto original).
3. **Tasa de exportación del maíz blanco 1005.90.04:** confirmado como discrepancia (2026-10-30). La Tarifa original fija IGI 20 / IGE Ex.; tarifa04 (IGE 50) venció el 2023-06-30 y tarifa06 (IGI 50 / IGE 50) el 2023-12-31, y ningún instrumento posterior del registro vuelve a fijar el 50 % de exportación. SNICE sigue publicando IGE 50. La release conserva el valor de SNICE, deja la fracción sin vigencia y la reporta en `manifest.rate_validity.discrepancies`. **Resuelto (2026-10-30):** se corrige a IGE Ex. desde el 2024-01-01 con `src/arancel_mx/sources/rate_corrections.json` (ver `docs/data-model.md`). El transitorio Primero de tarifa06 confirma el vencimiento: «estará vigente hasta el 31 de diciembre de 2023». tarifa08 (DOF 2023-12-27) sólo modifica el decreto de la canasta básica, del que tarifa06 ya había eliminado esta fracción.
4. **NICO de la totoaba:** buscar en el DOF una modificación de NICO posterior al 2024-03-22 que el registro no liste.
5. **acuerdo01 y acuerdo03** (tablas de correlación, Notas Nacionales): aún sin leer.
6. **Conteo de días de ref01:** confirmar el 2026-01-17 conforme a la regla de cómputo aplicable.

## Relacionado

- [Programa de profundidad](../depth-program.md)
- [Decisión 0001](../decisions/0001-vigilancia-dof-sidof.md)
- [Fuentes y reconciliación](../sources.md)
- [Modelo de datos](../data-model.md)
