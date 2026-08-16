# Fuentes oficiales y qué herramienta usar

`arancel-mx` ayuda a **consultar, verificar y reproducir** una captura versionada de datos LIGIE/NICO. No sustituye la determinación de una autoridad competente, no es asesoría legal y no clasifica mercancías. Una persona responsable debe revisar la evidencia aplicable a su operación.

> La finalidad de esta guía es separar el rol de las fuentes oficiales del rol técnico de una release verificable. Una misma consulta puede requerir ambas cosas.

| Necesidad | Fuente o herramienta principal | Rol de `arancel-mx` |
|---|---|---|
| Confirmar el texto jurídico publicado | [DOF](https://www.dof.gob.mx/) y la publicación concreta aplicable | Preserva la procedencia de los documentos capturados; no reemplaza el texto oficial. |
| Entender la LIGIE, NICO, cambios y archivos de referencia | [SNICE](https://www.snice.gob.mx/cs/avi/snice/ligie.info22.html) | Expone una captura reproducible con identidad de fuente y una release inmutable. |
| Realizar una consulta oficial interactiva de fracciones | [VUCEM — Buscador de fracciones](https://www.ventanillaunica.gob.mx/vucem/Clasificador.html) | Permite recuperar registros, jerarquía, notas y procedencia desde artefactos verificables. |
| Integrar datos en Python, CLI, DuckDB o HTTP | La release `data-YYYY.MM.DD` de este proyecto | Verifica manifiesto, SHA-256 y estructura antes de servir resultados. |

## Ruta de decisión

Primero, si necesitas confirmar una norma, fecha de vigencia, publicación o consecuencia jurídica concreta, empieza por el **DOF** y el instrumento oficial aplicable. SNICE ofrece materiales de orientación, descargas y páginas canónicas útiles para localizar el contexto LIGIE/NICO. VUCEM es el destino oficial para una búsqueda interactiva de fracciones.

Después, si necesitas una integración repetible o una auditoría técnica, fija una release de datos de `arancel-mx`. No uses una rama de Git ni una descarga sin identidad como si fueran una versión de datos. Descarga la release exacta, verifica `SHA256SUMS` y consulta el `manifest.json` antes de integrar los artefactos.

```bash
arancel-mx doctor --dataset data-2026.08.15
arancel-mx data download --dataset data-2026.08.15
arancel-mx data verify --dataset data-2026.08.15
arancel-mx provenance 01012101 --dataset data-2026.08.15
```

La fecha anterior es un ejemplo de formato. Para una integración nueva, identifica la release publicada que corresponde a tu proceso y conserva esa identidad junto con tu resultado.

## Qué significa una respuesta del proyecto

Las respuestas de `lookup`, `ficha`, `search`, `suggest`, `national_notes` y `provenance` son recuperación de evidencia dentro de un dataset verificado. En particular, `search` y `suggest` son retrieve-only: no clasifica mercancías ni afirma una fracción jurídicamente correcta. Las Notas Nacionales se recuperan con su procedencia, pero su aplicación debe evaluarse frente a la fuente oficial y el caso concreto.

## Referencias

[1]: https://www.dof.gob.mx/ "Diario Oficial de la Federación"
[2]: https://www.snice.gob.mx/cs/avi/snice/ligie.info22.html "SNICE — LIGIE: Acerca de"
[3]: https://www.ventanillaunica.gob.mx/vucem/Clasificador.html "VUCEM — Buscador de fracciones arancelarias"
