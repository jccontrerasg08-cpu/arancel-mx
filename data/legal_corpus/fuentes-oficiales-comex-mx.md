# Fuentes oficiales Comex MX

## Regla de corroboracion

Antes de presentar un requisito legal como confirmado, valida la fuente vigente. Si no hay texto vigente o fecha aplicable en el contexto, responde como orientacion y pide validar en fuente oficial.

Prioridad de fuente:

1. DOF para texto publicado, reformas, acuerdos, NOMs, cuotas, aranceles y vigencia.
2. VUCEM/SNICE para herramientas operativas de clasificacion, NICO/LIGIE y tramites.
3. ANAM/SAT para criterios, operacion aduanera, pedimentos, reglas, aduanas y tratados publicados.
4. Camara de Diputados para leyes compiladas, solo como apoyo; si hay duda, confirma contra DOF.

## LIGIE, TIGIE, fraccion arancelaria y NICO

Fuentes base:

- DOF: https://www.dof.gob.mx/
- Clasificador arancelario VUCEM: https://www.ventanillaunica.gob.mx/Clasificador/
- SNICE: https://www.snice.gob.mx/
- Camara de Diputados, leyes federales: https://www.diputados.gob.mx/LeyesBiblio/

Uso en Comex Bot:

- Para clasificacion, pedir descripcion tecnica, funcion, composicion, presentacion, origen/destino y uso.
- No dar fraccion definitiva si solo hay descripcion comercial.
- Citar fraccion/NICO como candidato cuando venga de VUCEM/SNICE local y marcar que debe confirmarse con TIGIE/LIGIE vigente y notas aplicables.
- Para tasas, cuotas, regulaciones y unidad de medida, validar la fraccion vigente en VUCEM/SNICE/DOF antes de operar.

## NOMs, permisos y restricciones no arancelarias

Fuentes base:

- DOF: https://www.dof.gob.mx/
- SNICE: https://www.snice.gob.mx/
- VUCEM tramites y requisitos: https://www.ventanillaunica.gob.mx/
- Secretaria de Economia: https://www.gob.mx/se/

Uso en Comex Bot:

- Las NOMs dependen de fraccion, producto, uso, presentacion, fecha y regimen.
- Confirmar si aplica cumplimiento en punto de entrada, exencion, permiso previo, aviso automatico, cupo, padron sectorial, cuota compensatoria u otra regulacion.
- No inventar NOMs por familia de producto; si no estan recuperadas en el contexto, indicar que falta validar por fraccion vigente.

## Tratados, acuerdos y origen

Fuentes base:

- ANAM, tratados y acuerdos firmados con Mexico: https://www.anam.gob.mx/tratados-y-acuerdos-firmados-con-mexico/
- VUCEM, tratados de comercio exterior: https://www.ventanillaunica.gob.mx/
- DOF para decretos, acuerdos y reglas de origen: https://www.dof.gob.mx/
- Secretaria de Economia: https://www.gob.mx/se/

Uso en Comex Bot:

- Antes de sugerir preferencia arancelaria, validar pais de origen, pais de procedencia, tratado aplicable, regla de origen, prueba/certificado de origen y vigencia.
- Diferenciar tratado aplicable de documentos comerciales: factura, lista de empaque, transporte y certificado/prueba de origen.
- Si solo hay un pais y una fraccion tentativa, responder como prevalidacion, no como beneficio confirmado.

## Ley Aduanera, Reglamento, RGCE y Anexo 22

Fuentes base:

- DOF: https://www.dof.gob.mx/
- SAT: https://www.sat.gob.mx/
- ANAM normatividad: https://www.anam.gob.mx/normatividad_2022/
- Camara de Diputados, leyes federales: https://www.diputados.gob.mx/LeyesBiblio/

Uso en Comex Bot:

- Para pedimento, identificadores, claves, regimenes, infracciones o obligaciones, pedir fecha de operacion y regimen.
- Validar reglas vigentes, anexos y criterios antes de cerrar una respuesta operativa.
- Citar la fuente/seccion recuperada; si no esta en el corpus o DOF local, sugerir actualizar ETL y corroborar en DOF/SAT/ANAM.

## Actualizacion local recomendada

Comandos:

- `python comex.py etl run vucem-tigie`
- `python comex.py etl run snice-nico`
- `python comex.py etl run anam-corpus`
- `python comex.py etl run dof-comex`
- `python comex.py catalog-refresh`
- `python comex.py rag-audit`

Atajo:

- `python comex.py etl run`
- `python comex.py rag-audit`

Nota:

- `dof-comex` indexa publicaciones recientes segun `DOF_LOOKBACK_DAYS`.
- Para una reforma historica especifica, buscarla manualmente en DOF y guardar el texto relevante en este corpus.
- Para PDFs/Excel oficiales, conservar URL, fecha de consulta y fecha de publicacion.
