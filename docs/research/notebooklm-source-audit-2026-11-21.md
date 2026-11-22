# Auditoría de fuentes de Gemini Notebook y retroalimentación para arancel-mx

**Corte documental:** 2026-11-21 · **Repositorio:** `jccontrerasg08-cpu/arancel-mx` · **Inventario:** [JSON](notebooklm-source-inventory-2026-11-21.json).

## Alcance y metodología

La interfaz indicaba **41 fuentes**, mientras la lectura de su panel devolvió **42 entradas visibles** (**41 títulos distintos**). La URL de `LSH.pdf` se repite; esta diferencia debe reconciliarse desde NotebookLM. Se identificaron **26 entradas de PDF legislativo**, además de referencias estadísticas, SNICE, páginas del propio proyecto y recursos educativos. Para fuentes cuyo enlace original no se mostró, el catálogo registra URL pública *sugerida* o deja el campo vacío; no inventa el vínculo importado.

Se cotejaron las **fuentes críticas** con índices y páginas oficiales mediante Exa y TinyFish. **No se leyó artículo por artículo cada ley, no se verificó la transcripción íntegra de todos los videos, ni se extrajeron documentos privados del notebook.** Los títulos se conservan para trazabilidad; no se copian textos legales enteros ni contenidos privados. Los enlaces jurídicos son referencias, nunca prueba suficiente de vigencia aplicable.

**Auditoría de portadas legislativas (Exa):** se recuperaron las **25 URLs únicas** de PDF legislativo presentes en el notebook (26 entradas por duplicado de LSH); en **22** se extrajo una fecha de última reforma del encabezado, y en **3** no se pudo extraer una fecha con ese patrón. Esto verifica sólo la lectura del documento/portada, no cada artículo, anexo, transitorio ni vigencia normativa. El JSON conserva la fecha extraída por URL y marca los casos sin dato; no interpreta una ausencia como «sin reforma».

## Hallazgos contrastados

| Tema | Hallazgo concreto | Consulta oficial |
|---|---|---|
| Ley Aduanera | Índice de reformas registra DOF 2026-10-23, pero el PDF consultado seguía mostrando reforma 2025-11-19 | [Fuente](https://www.diputados.gob.mx/LeyesBiblio/ref/ladua.htm) |
| Ley Federal de Derechos | Historial de reformas registra DOF 2026-11-13; no confundir reforma con actualización de cuotas del 2025-12-28 | [Fuente](https://www.diputados.gob.mx/LeyesBiblio/ref/lfd.htm) |
| Ley del ISR | Historial registra reforma DOF 2026-11-13; el catálogo conservaba 2024-04-01 | [Fuente](https://www.diputados.gob.mx/LeyesBiblio/ref/lisr.htm) |
| Reglamento de la LIC | Publicado el 2026-09-04; es un instrumento separado de la ley | [Fuente](https://sidof.segob.gob.mx/notas/5797937) |
| RGCE | Índice SAT lista reglas base, modificaciones y anexos por separado; el PDF inicial no es equivalente a compilación vigente | [Fuente](https://www.sat.gob.mx/minisitio/NormatividadRMFyRGCE/normatividad_rmf_rgce2026.html) |
| NOM 2.4.1 | La presencia de una fracción en el anexo es una señal de revisión, no determinación completa de cumplimiento de un producto | [Fuente](https://www.snice.gob.mx/cs/avi/snice/seguridad.normatividad.html) |
| INEGI BCMM | Preservar valoración FOB, cifras revisadas/ajustadas, nivel de código y marcas de confidencialidad | [Fuente](https://www.inegi.org.mx/sistemas/Olap/Proyectos/bd/continuas/comex/comex_bcmm_mensual2023.asp) |
| TIGIE–SCIAN | Correlación estadística de versión 2025; su conteo no es una validación directa de una release arancelaria 2026 | [Fuente](https://www.inegi.org.mx/app/tigie/) |

**IEPS:** el historial de la Cámara de Diputados distingue la **última reforma del 07-11-2025** del **acuerdo de actualización de cuotas del 22-12-2025** para 2026; se corrigió el metadato que mezclaba ambos eventos. [Historial oficial](https://www.diputados.gob.mx/LeyesBiblio/ref/lieps.htm).

## Decisión de arquitectura

1. **No duplicar el catálogo.** Mantener las referencias generales y jurídicas en `external-trade-source-catalog.json`, la estadística en `inegi-analytics-catalog.json` y este archivo como registro de investigación de NotebookLM.
2. **Tres conceptos de vigencia distintos.** Fecha de reforma publicada, fecha de actualización de cantidades y fecha de consolidación del PDF; ningún campo sustituye al otro.
3. **Releases LIGIE/NICO separadas.** No incorporar reglamentos, videos, RRNA generales o datos BCMM a `source_registry.json` ni cambiar el pipeline arancelario sin un ADR y pruebas.
4. **Evitar falsa automatización regulatoria.** Las NOM del Anexo 2.4.1, tratados y cuotas requieren hechos de la operación, excepciones y vigencia; una consulta por fracción no es determinación oficial.
5. **Mantener referencias con una rutina de revisión.** Comprobar índices legislativos, RGCE, SNICE, series BCMM y enlaces al menos tras modificaciones; registrar fecha de consulta y fuente.
6. **Gestionar recursos audiovisuales separadamente.** El canal de Ruta Logística sirve para educación; no atribuir a su Módulo 8 el temario particular de tecnología del proyecto sin distinguirlo.

Un enlace a un PDF consolidado puede estar atrasado respecto de un decreto del DOF. Se debe revisar índice de reformas, decreto, transitorios y fecha de entrada en vigor antes de hacer afirmaciones jurídicas.

## Inventario completo de entradas visibles

| Nº | Fuente | Tipo | Referencia |
|---:|---|---|---|
| 1 | Datos Arancelarios MX | `unverified_nonpublic_or_secondary` | No expuesta |
| 2 | arancel-mx — Consulta el arancel de México, con su evidencia. | `project_source` | No expuesta |
| 3 | arancel-mx — Manual de Operación Aduanera, en contexto. | `project_source` | No expuesta |
| 4 | Balanza | `statistical_source` | [URL sugerida](https://www.inegi.org.mx/temas/balanza/) |
| 5 | Balanza comercial | `statistical_source` | [URL sugerida](https://www.inegi.org.mx/temas/balanza/) |
| 6 | Balanza Comercial de Mercancías de México (BCMM) | `statistical_source` | [URL sugerida](https://www.inegi.org.mx/programas/comext/default.html) |
| 7 | Clasificadores - Catálogo TIGIE - SCIAN | `statistical_source` | [URL sugerida](https://www.inegi.org.mx/app/tigie/) |
| 8 | Cuéntame de México | `statistical_source` | [URL sugerida](https://cuentame.inegi.org.mx/) |
| 9 | DOF - Diario Oficial de la Federación | `official_gazette` | [URL sugerida](https://www.dof.gob.mx/) |
| 10 | GitHub - jccontrerasg08-cpu/arancel-mx: Open-source tools and traceable public data for Mexico's LIGIE, NICO, and tariff analysis · GitHub | `project_source` | [URL sugerida](https://github.com/jccontrerasg08-cpu/arancel-mx) |
| 11 | https://www.diputados.gob.mx/LeyesBiblio/pdf/65_071220.pdf | `federal_law` | [URL original](https://www.diputados.gob.mx/LeyesBiblio/pdf/65_071220.pdf) |
| 12 | https://www.diputados.gob.mx/LeyesBiblio/pdf/207.pdf | `federal_law` | [URL original](https://www.diputados.gob.mx/LeyesBiblio/pdf/207.pdf) |
| 13 | https://www.diputados.gob.mx/LeyesBiblio/pdf/CFF.pdf | `federal_law` | [URL original](https://www.diputados.gob.mx/LeyesBiblio/pdf/CFF.pdf) |
| 14 | https://www.diputados.gob.mx/LeyesBiblio/pdf/LAdua.pdf | `federal_law` | [URL original](https://www.diputados.gob.mx/LeyesBiblio/pdf/LAdua.pdf) |
| 15 | https://www.diputados.gob.mx/LeyesBiblio/pdf/LCPAF.pdf | `federal_law` | [URL original](https://www.diputados.gob.mx/LeyesBiblio/pdf/LCPAF.pdf) |
| 16 | https://www.diputados.gob.mx/LeyesBiblio/pdf/LFAFE.pdf | `federal_law` | [URL original](https://www.diputados.gob.mx/LeyesBiblio/pdf/LFAFE.pdf) |
| 17 | https://www.diputados.gob.mx/LeyesBiblio/pdf/LFCPQ.pdf | `federal_law` | [URL original](https://www.diputados.gob.mx/LeyesBiblio/pdf/LFCPQ.pdf) |
| 18 | https://www.diputados.gob.mx/LeyesBiblio/pdf/LFD.pdf | `federal_law` | [URL original](https://www.diputados.gob.mx/LeyesBiblio/pdf/LFD.pdf) |
| 19 | https://www.diputados.gob.mx/LeyesBiblio/pdf/LFISAN.pdf | `federal_law` | [URL original](https://www.diputados.gob.mx/LeyesBiblio/pdf/LFISAN.pdf) |
| 20 | https://www.diputados.gob.mx/LeyesBiblio/pdf/LFMZAAH.pdf | `federal_law` | [URL original](https://www.diputados.gob.mx/LeyesBiblio/pdf/LFMZAAH.pdf) |
| 21 | https://www.diputados.gob.mx/LeyesBiblio/pdf/LFSA.pdf | `federal_law` | [URL original](https://www.diputados.gob.mx/LeyesBiblio/pdf/LFSA.pdf) |
| 22 | https://www.diputados.gob.mx/LeyesBiblio/pdf/LFSV.pdf | `federal_law` | [URL original](https://www.diputados.gob.mx/LeyesBiblio/pdf/LFSV.pdf) |
| 23 | https://www.diputados.gob.mx/LeyesBiblio/pdf/LFZEE.pdf | `federal_law` | [URL original](https://www.diputados.gob.mx/LeyesBiblio/pdf/LFZEE.pdf) |
| 24 | https://www.diputados.gob.mx/LeyesBiblio/pdf/LGEEPA.pdf | `federal_law` | [URL original](https://www.diputados.gob.mx/LeyesBiblio/pdf/LGEEPA.pdf) |
| 25 | https://www.diputados.gob.mx/LeyesBiblio/pdf/LGOAAC.pdf | `federal_law` | [URL original](https://www.diputados.gob.mx/LeyesBiblio/pdf/LGOAAC.pdf) |
| 26 | https://www.diputados.gob.mx/LeyesBiblio/pdf/LGPAS.pdf | `federal_law` | [URL original](https://www.diputados.gob.mx/LeyesBiblio/pdf/LGPAS.pdf) |
| 27 | https://www.diputados.gob.mx/LeyesBiblio/pdf/LGS.pdf | `federal_law` | [URL original](https://www.diputados.gob.mx/LeyesBiblio/pdf/LGS.pdf) |
| 28 | https://www.diputados.gob.mx/LeyesBiblio/pdf/LGTOC.pdf | `federal_law` | [URL original](https://www.diputados.gob.mx/LeyesBiblio/pdf/LGTOC.pdf) |
| 29 | https://www.diputados.gob.mx/LeyesBiblio/pdf/LGVS.pdf | `federal_law` | [URL original](https://www.diputados.gob.mx/LeyesBiblio/pdf/LGVS.pdf) |
| 30 | https://www.diputados.gob.mx/LeyesBiblio/pdf/LICal_010720.pdf | `federal_law` | [URL original](https://www.diputados.gob.mx/LeyesBiblio/pdf/LICal_010720.pdf) |
| 31 | https://www.diputados.gob.mx/LeyesBiblio/pdf/LIEPS.pdf | `federal_law` | [URL original](https://www.diputados.gob.mx/LeyesBiblio/pdf/LIEPS.pdf) |
| 32 | https://www.diputados.gob.mx/LeyesBiblio/pdf/LISR.pdf | `federal_law` | [URL original](https://www.diputados.gob.mx/LeyesBiblio/pdf/LISR.pdf) |
| 33 | https://www.diputados.gob.mx/LeyesBiblio/pdf/LIVA.pdf | `federal_law` | [URL original](https://www.diputados.gob.mx/LeyesBiblio/pdf/LIVA.pdf) |
| 34 | https://www.diputados.gob.mx/LeyesBiblio/pdf/LNCM.pdf | `federal_law` | [URL original](https://www.diputados.gob.mx/LeyesBiblio/pdf/LNCM.pdf) |
| 35 | https://www.diputados.gob.mx/LeyesBiblio/pdf/LSH.pdf | `federal_law` | [URL original](https://www.diputados.gob.mx/LeyesBiblio/pdf/LSH.pdf) |
| 36 | https://www.diputados.gob.mx/LeyesBiblio/pdf/LSH.pdf | `federal_law` | [URL original](https://www.diputados.gob.mx/LeyesBiblio/pdf/LSH.pdf) |
| 37 | https://www.snice.gob.mx/cs/avi/snice/biblioteca.juridica.tasas.html | `official_portal` | [URL original](https://www.snice.gob.mx/cs/avi/snice/biblioteca.juridica.tasas.html) |
| 38 | https://www.snice.gob.mx/cs/avi/snice/biblioteca.juridica.tlc.html | `official_portal` | [URL original](https://www.snice.gob.mx/cs/avi/snice/biblioteca.juridica.tlc.html) |
| 39 | https://www.snice.gob.mx/cs/avi/snice/f.c.indic.int.html | `official_portal` | [URL original](https://www.snice.gob.mx/cs/avi/snice/f.c.indic.int.html) |
| 40 | Instituto Nacional de Estadística y Geografía (INEGI) | `statistical_source` | [URL sugerida](https://www.inegi.org.mx/) |
| 41 | International Business | `unverified_nonpublic_or_secondary` | No expuesta |
| 42 | Ruta Logística MX - YouTube | `educational_video_index` | No expuesta |

## Propuestas de seguimiento

- **P0 – exactitud:** armonizar reforma, PDF y cuotas; corregir la fecha de RGCE inicial y enlazar el índice de modificaciones.
- **P1 – datos estadísticos:** incorporar metadatos de revisión/censura de INEGI y versión de correlación TIGIE–SCIAN.
- **P2 – experiencia:** añadir enlaces de procedencia al visor sin confundir referencia con requisito automático; publicar comparador histórico sólo sobre releases verificadas.
- **P3 – formación:** organizar videos y lecturas del temario propio sin confundirlos con módulos oficiales de Ruta Logística MX.

## Regla editorial

El **DOF** conserva autoridad sobre publicaciones jurídicas; la Cámara de Diputados, SAT y SNICE facilitan acceso, índices y compilaciones. Este inventario no es una fuente de verdad jurídica ni asesoría aduanera. Toda modificación de reglas aplicables debe verificarse contra el instrumento oficial, sus transitorios y la fecha de la operación.

## Fuentes formativas y límites de contenido

La Secretaría de Economía documentó el inicio de la segunda fase de [Ruta Logística MX 2026](https://www.gob.mx/se/prensa/inicia-la-segunda-fase-de-ruta-logistica-mx-2026-mexico-la-nueva-ruta-del-mundo?state=published), organizada en diez módulos del 22-09 al 24-11-2026. Este comunicado **no acredita haber visto o transcrito todos los videos**: un canal de YouTube debe verificarse por video, fecha y material disponible antes de usarlo como fuente de un programa curricular. La propuesta didáctica interna de arancel-mx tampoco debe atribuirse automáticamente al módulo oficial número 8.
