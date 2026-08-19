# Mapa de cobertura oficial de comercio exterior

> [Centro de documentación](../README.md) · [Fuentes y reconciliación](../sources.md) · [Catálogo estructurado](external-trade-source-catalog.json)

Este mapa amplía la orientación pública de `arancel-mx` para las categorías habituales de comercio exterior sin convertir el proyecto en un portal transaccional ni reproducir contenidos de terceros. El dataset conserva su función central: publicar LIGIE, NICO, tasas, vigencia, jerarquía y procedencia mediante releases verificables. Las demás categorías se expresan como **referencias oficiales de primer nivel**, con una frontera explícita entre consulta documental y determinación de obligaciones.

El catálogo legible por máquina asociado es [`external-trade-source-catalog.json`](external-trade-source-catalog.json). Su uso es de navegación y procedencia; no se incorpora al `source_registry.json`, no altera el build de releases y no debe confundirse con datos canonizados.

## Cobertura por categoría

| Categoría de consulta | Estado en `arancel-mx` | Punto de verificación oficial | Límite de producto |
|---|---|---|---|
| Fracción, HS y tasa IGI/IGE | **Incluida en release verificable** | [LIGIE — SNICE][1] y evidencia legal registrada | Una coincidencia de búsqueda no sustituye la clasificación de mercancía. |
| NICO | **Incluido en release verificable** | [NICO — SNICE][2] | Sólo se muestra el NICO presente en la misma release y vinculado con su fracción. |
| Notas nacionales | **Incluidas en release verificable** | [Notas nacionales — SNICE][3] | No sustituyen reglas generales, complementarias ni una interpretación legal. |
| Indicadores arancelarios | **Referencia oficial** | [Indicadores arancelarios — SNICE][4] | No se publican como datos de release sin fuente, esquema, fixture y validación específicos. |
| Marco aduanero | **Referencia oficial** | [Ley Aduanera — Cámara de Diputados][5] | No determina regímenes, requisitos, sanciones u obligaciones de un caso. |
| Aranceles, origen y RRNA | **Referencia oficial** | [Ley de Comercio Exterior — Cámara de Diputados][6] | Una fracción por sí sola no demuestra permisos, cupos, cuotas ni origen preferencial. |
| Reglas operativas vigentes | **Referencia oficial** | [RGCE 2026 — SAT][7] | Deben verificarse la versión, regla y anexo aplicables; no se genera un pedimento. |
| Tratados y acuerdos | **Referencia oficial** | [Tratados y acuerdos — Secretaría de Economía][8] | No se asigna tasa preferencial ni se verifica origen; cada beneficio depende de condiciones documentales y normativas. |
| Avisos, permisos, cupos, origen, cuotas y NOMs | **Referencia oficial** | [Medidas no arancelarias — SNICE][9] | No se declara cumplimiento regulatorio por código ni por descripción de producto. |
| Trámites y consultas oficiales | **Servicio externo transaccional** | [VUCEM][10] | Las operaciones y la información transaccional se realizan sólo en la plataforma oficial. |
| Padrón de importadores y exportadores | **Referencia oficial** | [SAT — Padrón][11] | No se consulta, valida ni almacena estatus de contribuyentes. |
| IMMEX, PROSEC y DRAWBACK | **Referencia oficial** | [Programas de fomento — SNICE][12] | No se infiere elegibilidad de un programa a partir de una fracción arancelaria. |

La Ley de Comercio Exterior identifica que la autoridad puede establecer reglas de origen, permisos, cupos, marcado de país de origen, cuotas compensatorias y otras medidas; asimismo, prevé que las RRNA se identifiquen por fracciones y se publiquen en los instrumentos aplicables.[6] Esa relación explica por qué el código arancelario es un punto de partida útil, pero no una respuesta suficiente sobre el cumplimiento de una operación.

La Secretaría de Economía mantiene el inventario de tratados y acuerdos, mientras que VUCEM concentra trámites y consultas operativas de varias autoridades.[8] [10] Por ello, `arancel-mx` ofrece enlaces de verificación en vez de deducir elegibilidad, simular preferencias o solicitar credenciales y documentos del usuario.

## Cobertura funcional y límites verificables

**No es un simulador de costos.** El cálculo de CIF, arancel preferencial, DTA, IVA, IEPS u otros componentes depende de hechos de la operación, régimen, origen, valor, vigencia, anexos y requisitos que no pertenecen al contrato de datos LIGIE/NICO. Tampoco es un generador de pedimentos, un verificador de T-MEC, un consultor RRNA ni un asistente de clasificación.

La arquitectura conserva tres niveles que no deben mezclarse:

| Nivel | Qué contiene | Cómo se verifica |
|---|---|---|
| Dataset canónico | LIGIE, NICO, tasas, jerarquía, vigencia, procedencia y notas nacionales publicables | Release, `manifest.json`, checksums, evidencia capturada y pruebas del pipeline. |
| Referencias oficiales | Leyes, RGCE, tratados, RRNA, programas y portales de consulta | URL oficial, función de fuente y fecha de consulta documental. |
| Servicios transaccionales | Trámites, expedientes, permisos, pedimentos y consultas con autenticación | Exclusivamente la autoridad o plataforma oficial correspondiente. |

## Ruta de consulta responsable

La consulta empieza con la release verificable de `arancel-mx` para ubicar el código, su jerarquía, sus tasas publicadas, vigencia registrada y notas nacionales. Después se abre el recurso oficial asociado a la pregunta: la Ley Aduanera y las RGCE para marco operativo; la Ley de Comercio Exterior y SNICE para medidas no arancelarias; la Secretaría de Economía para tratados; y VUCEM o SAT cuando la necesidad consiste en un trámite o padrón.

> Este mapa no ofrece asesoría legal, fiscal, aduanera ni de clasificación. Toda determinación debe contrastarse con la publicación oficial aplicable y, cuando corresponda, con profesionales habilitados.

## Referencias

[1]: https://www.snice.gob.mx/cs/avi/snice/ligie.info22.html "SNICE — LIGIE"
[2]: https://www.snice.gob.mx/cs/avi/snice/ligie.nico2022.html "SNICE — NICO"
[3]: https://www.snice.gob.mx/cs/avi/snice/ligie.notasnac22.html "SNICE — Notas nacionales"
[4]: https://www.snice.gob.mx/cs/avi/snice/ligie.indicaranc22.html "SNICE — Estudios e indicadores arancelarios"
[5]: https://www.diputados.gob.mx/LeyesBiblio/pdf/LAdua.pdf "Cámara de Diputados — Ley Aduanera"
[6]: https://www.diputados.gob.mx/LeyesBiblio/pdf/LCE.pdf "Cámara de Diputados — Ley de Comercio Exterior"
[7]: https://www.sat.gob.mx/minisitio/NormatividadRMFyRGCE/documentos2026/rgce/rgce/ReglasGeneralesComercioExteriorpara2026.pdf "SAT — RGCE 2026"
[8]: https://www.gob.mx/se/acciones-y-programas/comercio-exterior-paises-con-tratados-y-acuerdos-firmados-con-mexico "Secretaría de Economía — Tratados y acuerdos"
[9]: https://www.snice.gob.mx/cs/avi/snice/home.html "SNICE — Medidas no arancelarias"
[10]: https://www.ventanillaunica.gob.mx/vucem/index.html "VUCEM — Ventanilla Única de Comercio Exterior"
[11]: https://www.sat.gob.mx/minisitio/PadronImportadoresExportadores/index.html "SAT — Padrón de Importadores y Exportadores"
[12]: https://www.snice.gob.mx/cs/avi/snice/programasdefom.immex.html "SNICE — IMMEX"
