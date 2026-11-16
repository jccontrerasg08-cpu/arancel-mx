# Decisión 0003: NOM por fracción desde el Anexo 2.4.1 de las reglas de comercio exterior

- **Estado:** propuesta (pendiente de revisión del propietario)
- **Fecha:** 2026-11-13
- **Responsable:** @jccontrerasg08-cpu

## Contexto

El Anexo 2.4.1 del «Acuerdo por el que la Secretaría de Economía emite reglas y criterios de carácter general en materia de comercio exterior» lista las fracciones sujetas a Normas Oficiales Mexicanas (NOM) en la importación y la exportación. Hoy el dataset no lo incluye. Es la información que más pide quien consulta una fracción («¿qué NOM me aplica?»).

El anexo se publica como tabla dentro de un PDF de unas 980 páginas (edición del 2 de abril de 2026, biblioteca de SNICE; las páginas 481–953 son el anexo). Tiene cinco numerales con efecto legal distinto, y cada uno limita la aplicación con acotaciones («Únicamente:», «Excepto:»):

| Numeral | Significado | Regla |
|---|---|---|
| 1 | Importación sujeta a NOM | 2.4.3 |
| 2 | Importación sujeta a NOM sin exención | 2.4.3 y 2.4.11 |
| 3 | NOM de información comercial y sanitaria (la NOM está en el título de cada sección I–XIV) | 2.4.8 |
| 4 | Exportación sujeta a NOM | 2.4.9 |
| 5 | NOM de emergencia (hoy sin filas) | 2.4.3 |

## Decisión

1. **Fuente.** El PDF oficial de SNICE se registra en `source_registry.json` con URL y SHA-256 (edición vigente al capturar; la URL lleva fecha y cambia con cada edición). Se captura como cualquier otra fuente: sin hash registrado no se publica.
2. **Lector con falla cerrada** (`arancel_mx.parsers.nom_annex`). Lee en el orden del documento y usa coordenadas sólo para la columna (el límite de la última columna sale de las líneas verticales de cada tabla). Si encuentra texto que no es fracción en la columna de fracción, una fila sin fracción, una NOM ilegible o una sección del numeral 3 sin NOM en el título, **falla**; no adivina.
3. **Se conserva el numeral y la acotación en cada registro.** Una NOM con «Únicamente: …» no aplica a toda la fracción; perder el límite daría una respuesta falsa. El texto de la acotación se guarda literal.
4. **Se recupera, no se clasifica.** El dataset dice qué fracción aparece en qué numeral con qué NOM. No decide si un producto concreto está sujeto: la interfaz lo dice («señala qué revisar, no determina»).
5. **El anexo no corrige el arancel.** Las descripciones y NICO del anexo sólo sirven para validar la lectura contra el dataset. Las diferencias (NICO que el anexo lista y el arancel no tiene; redacción distinta) se reportan en un informe de validación y no se aplican al arancel.
6. **Validación de la lectura.** Medida sobre la edición del 2 de abril de 2026: 473 páginas leídas, 3,084 de 3,085 descripciones coinciden exactamente con la oficial; las diferencias de NICO (7 códigos ausentes del arancel, 17 redacciones distintas) quedan en el informe.
7. **Publicación por etapas**, cada una en su PR: (a) lector, pruebas y esta decisión; (b) captura y tabla DuckDB (`storage_compatibility_version` v1.0.0, tabla nueva y aditiva); (c) archivo por capítulo en la API estática (`regulations/{hs2}.json`) con contrato documentado y procedencia; (d) bloque en la ficha de la fracción con aviso y pruebas e2e.

## Consecuencias

- Es aditivo: no cambia tablas, archivos ni contratos existentes.
- Cada edición nueva del anexo exige regenerar y revisar el informe de validación; un cambio de estructura hace fallar la captura en lugar de publicar datos dudosos.
- Se reporta la cobertura: fracciones con NOM y filas del anexo que no se asocian a una fracción vigente.
