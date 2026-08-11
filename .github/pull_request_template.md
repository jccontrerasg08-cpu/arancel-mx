## Resumen

Describe el problema, el alcance arancelario y la solución propuesta.

## Tipo de cambio

- [ ] Fuente o captura oficial
- [ ] Parser o fixture
- [ ] Modelo, almacenamiento o pipeline
- [ ] Release o CLI
- [ ] Documentación, seguridad o mantenimiento

## Double check pre-PR

- [ ] Comparé la rama contra el `main` protegido actual y registré el SHA base relevante.
- [ ] Releí la spec/issue/plan aplicable y los contratos actuales del repositorio antes de cambiar comportamiento.
- [ ] Revalidé en documentación primaria cualquier API, Action, versión, setting o supuesto upstream que pueda haber cambiado.
- [ ] Revisé el diff completo contra `main` y no incluí archivos fuera de alcance.
- [ ] No incluí credenciales, datos personales, `.env`, bases locales, datasets generados, descargas ni directorios de build.

## Verificación

- [ ] Agregué o actualicé pruebas que cubren el cambio, o documenté por qué el cambio es exclusivamente documental.
- [ ] Ejecuté `python -m pytest -q`.
- [ ] Ejecuté `python -m build`.
- [ ] Ejecuté `git diff --check`.
- [ ] Documenté autoridad, URL, hash y papel de cualquier fuente nueva.
- [ ] Conservé compatibilidad del modelo o documenté el cambio de esquema.
- [ ] Si modifiqué Actions, mantuve permisos mínimos y acciones fijadas por SHA.
- [ ] Si modifiqué fuentes/reconciliación, agregué fixtures o pruebas offline del fallo esperado.
- [ ] Si modifiqué el contrato de release, actualicé esquema/manifiesto/documentación.
- [ ] Si cambié dependencias del build oficial, actualicé `requirements/production-build.txt` en el mismo PR.

## Mutaciones live y cleanup

Completa esta sección si el PR toca workflows o helpers con permisos de escritura en GitHub.

- [ ] La mutación live sólo se ejecutará desde `main` confiable después del merge, nunca desde la rama del PR.
- [ ] El namespace temporal no puede colisionar con `data-*` ni `[DATA ALERT]`.
- [ ] El cleanup es fail-closed y verifica por API la ausencia del recurso temporal.
- [ ] Registré evidencia del cleanup final de release/tag/Issue cuando aplica.
- [ ] Verifiqué que la release pública y los tags de producción no fueron modificados por la certificación.

Consulta [`docs/production-certification.md`](../docs/production-certification.md) para el runbook del boundary de certificación.

## Evidencia

Incluye resultados de pruebas, fixtures sanitizados, runs de Actions relevantes y decisiones de procedencia.
