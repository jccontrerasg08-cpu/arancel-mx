# Decisión 0004: el Anexo 2.4.1 es una fuente auxiliar, con canario diario

- **Estado:** propuesta (pendiente de revisión del propietario)
- **Fecha:** 2026-11-19
- **Responsable:** @jccontrerasg08-cpu
- **Modifica:** el punto «fuente obligatoria» de la [decisión 0003](0003-nom-por-fraccion-anexo-2-4-1.md). El lector sigue fallando cerrado ante lo ambiguo; lo que cambia es qué hace el release diario cuando el anexo falla.

## Contexto

La 0003 hizo del anexo una fuente obligatoria: si SNICE cambiaba el archivo o su formato, el pipeline fallaba. Eso protege contra publicar NOM dudosas, pero también frena la actualización diaria del arancel por un archivo auxiliar, justo cuando más gente usa el sitio.

## Decisión

1. **El anexo no frena el arancel.** Si no se descubre, no se descarga o no pasa la validación de estructura, el release se construye igual sin filas de NOM y lo registra: `release_metadata.nom_annex = {"status": "unavailable", "reason": …}` (y `available` con conteos cuando sí se lee). No se publican NOM a medias: o se lee entero y con forma de anexo, o no se publica ninguna.
2. **Una falla del anexo no reemplaza un release bueno por uno peor.** Si el anexo no se puede leer y ninguna otra fuente cambió (ni el registro de tasas), el pipeline termina en `no_change` y conserva el release anterior, que sí tiene NOM. Si el arancel sí cambió, se publica con `unavailable`: la actualización del arancel pesa más que la NOM del día.
3. **La interfaz no calla.** `regulations/{hs2}.json` lleva `annex.status` (`available`, `unavailable` o `not_included` para releases anteriores). La ficha dice «no aparece en el Anexo 2.4.1 tal como se leyó en esta release» cuando está disponible y no hay filas, y «los datos de NOM no están disponibles en esta release» cuando no lo está; en releases sin el anexo no muestra nada.
4. **Forma conocida y verificada.** `validate_annex_structure` exige la forma del anexo (numerales 1 y 3 presentes, al menos 1,500 registros, 1,200 fracciones y 8 secciones del numeral 3; la edición del 2 de abril de 2026 tiene 3,085, 2,530 y 14). Son pisos para detectar un anexo truncado o mal leído, no para tolerar cambios.
5. **Canario diario** (`.github/workflows/nom-annex-canary.yml`, 09:41 UTC, antes del pipeline de las 11:17): corre el mismo descubrimiento, captura y lector (`scripts/check_nom_annex.py`) sin publicar nada. Si falla, el workflow queda en rojo y GitHub avisa por correo con un día de ventaja para actuar. Se puede lanzar a mano (`workflow_dispatch`).

## Consecuencias

- Un cambio de formato en SNICE ya no detiene la actualización diaria; se entera uno por el canario y, mientras se arregla el lector, el sitio muestra el aviso en lugar de callar.
- Se acepta que, con el arancel cambiando y el anexo roto, un release salga sin NOM por unos días. Es visible, está marcado y es reversible al corregir el lector.
- El lector sigue siendo la única puerta: ninguna fila de NOM entra al release sin pasar la validación.

## Limitación conocida y opciones (pendiente de decisión del propietario)

Si el anexo no se puede leer **el mismo día en que cambia otra fuente** (una edición nueva de LIGIE o NICO, o el registro de tasas), el release sale sin NOM aunque el anterior sí las tuviera, y la ficha muestra el aviso de «no disponible» hasta que el anexo vuelva a leerse. Opciones:

1. **Aceptarlo** (lo implementado). Simple y visible; el costo es que la ficha pierde las NOM por unos días en ese caso. El canario avisa con un día de ventaja.
2. **Arrastrar las NOM del release anterior** cuando el anexo falle: el pipeline descargaría el DuckDB anterior (≈38 MB), copiaría sus filas de `nom_requirement` con su fuente original y lo marcaría `carried_forward` con la fecha de origen. La ficha seguiría mostrando NOM, indicando de qué edición vienen. Es más robusto, pero añade una descarga y un nuevo estado a la superficie pública.
3. **Retener el release** hasta que el anexo se lea. Descartada: frena la actualización del arancel.

Recomendación: la opción 2 si se esperan muchas visitas y se quiere que la NOM no desaparezca nunca; requiere validar el cambio en el contrato público (`annex.status = carried_forward`).
