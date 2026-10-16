# Programa de profundidad: del snapshot a un registro arancelario consolidado y con fecha

Este documento describe el programa que lleva a `arancel-mx` de un snapshot vigente a un registro arancelario consolidado y consultable a cualquier fecha: el protocolo de trabajo con revisión humana, el estado objetivo, los frentes de trabajo, el orden de las compuertas y el registro de decisiones. Es para quien mantiene el proyecto y para quien quiera saber hacia dónde va el modelo de datos.

## Estado y frontera

- **Estado:** la compuerta 0 (Gate 0) fue aprobada por el propietario el 2026-10-16; las compuertas posteriores necesitan su propia confirmación.
- **Modelo de operación:** Claude hace la investigación, el código, las pruebas, la documentación y los PR. El propietario confirma cada compuerta. Nada se integra, publica una release ni cambia un contrato público sin un «sí» explícito.
- **Frontera que nunca se mueve:** `arancel-mx` recupera y verifica evidencia. No clasifica mercancías, no calcula un arancel jurídicamente vinculante ni sustituye al DOF, al SAT, a la ANAM ni a un agente aduanal con patente. No constituye asesoría legal.

## 0. Cómo trabajamos (protocolo con revisión humana)

Cada unidad de trabajo pasa por los mismos cinco pasos:

| Paso | Claude hace | Tú haces |
|---|---|---|
| 1. Proponer | Escribe un registro de decisión de una página en `docs/decisions/NNNN-*.md` (contexto, opciones, recomendación, costo, riesgos). | Aprobar, editar o rechazar. |
| 2. Construir | Implementa en una rama de feature y ejecuta localmente lint, tipos, pruebas y pruebas de navegador. | Nada. |
| 3. Evidencia | Abre un PR con los números: pruebas, resultados de checks, diffs de muestra, antes y después. | Leer el resumen de evidencia. |
| 4. Integrar | Lleva CI a verde y responde los comentarios de revisión. | Confirmar el merge. |
| 5. Publicar | Sólo para cambios de datos o de API: prepara la release o el despliegue. | Confirmar la publicación. |

Reglas:

- Una compuerta = un registro de decisión + un PR (o una pila pequeña y con nombre). Sin alcance sorpresa.
- Cada compuerta termina con **ideas para la siguiente**; tú eliges cuáles sobreviven.
- Todo lo que requiera una persona, dinero, credenciales o una opinión legal se marca como **[owner]** y nunca se da por hecho.
- Los hechos desconocidos (fechas de decretos, conteos, tasas) se investigan y se citan de fuentes primarias; nunca se rellenan de memoria.

## 1. Estado objetivo

Para cualquier código (HS2 → NICO10) y cualquier fecha, el proyecto puede responder, con una cadena de citas hasta los bytes publicados:

1. ¿Existía el código, y cuáles eran su descripción, su unidad y su jerarquía?
2. ¿Cuáles eran las tasas de IGI/IGE y qué instrumento del DOF las fijó?
3. ¿Qué otras medidas oficiales tenía asociadas (aranceles preferenciales, programas sectoriales, cupos, medidas de remedio comercial, regulaciones no arancelarias), cada una con su fuente y su vigencia?
4. Qué cambió, cuándo se publicó y cuándo entró en vigor.
5. Dónde discrepan las fuentes oficiales y cómo resolvió el proyecto cada discrepancia.

## 2. Frentes de trabajo

Cada frente indica lo que ya existe en el repositorio, lo que se agrega y la verificación externa que lo demuestra.

### A. Núcleo jurídico-temporal (base; todo lo demás depende de él)

Ya existe: `effective_from`/`effective_to`, campos de tiempo diferenciados ([modelo de datos](data-model.md)), diffs de `source_history` por release, descubrimiento de PDF del DOF (`sources/dof_pdf.py`) y la fuente de la Cámara de Diputados (`sources/diputados.py`).

Se agrega:

- **A1. Inventario de instrumentos.** Un registro de cada instrumento del DOF que creó o modificó la LIGIE (del decreto de 2022 en adelante) y del Acuerdo NICO y sus modificaciones: fecha del DOF, regla de entrada en vigor, artículos transitorios, URL, SHA-256 e identificador al estilo ELI/FRBR (obra / expresión / manifestación).
- **A2. Operaciones de modificación.** Cada instrumento se convierte en operaciones tipadas: `create`, `delete`, `modify_description`, `modify_rate`, `modify_unit`, `split`, `merge`, `renumber`, `temporary_rate` (con vencimiento).
- **A3. Motor de reproducción.** Reproducción determinista desde la base de 2022 hasta cualquier fecha, que produce una tabla bitemporal (`valid_from`, `valid_to`, `published_at`, `captured_at`, `instrument_id`).
- **A4. Verificación de consolidación.** Resultado de la reproducción contra el texto consolidado de la Cámara de Diputados y contra la captura vigente de SNICE/VUCEM, campo por campo, con salida a un registro de discrepancias.
- **A5. `AS OF` en todas partes.** `arancel-mx lookup 85171301 --as-of 2024-03-01`, `Dataset(...).as_of(date)`, archivos de historia por capítulo en la API estática (`/data/v1/history/{hs2}.json`, que el cliente filtra por fecha), `?as_of=` en el servidor FastAPI propio y una línea de tiempo por código en el explorador web.

Prueba: al menos 30 puntos de prueba con fecha, rederivados del texto del DOF con fixtures auditables a mano; el resultado de la reproducción coincide con el texto consolidado, o cada diferencia tiene un motivo tipado.

### B. Calidad de extracción

- **B1. Extracción doble.** Dos extractores independientes por tipo de fuente (por ejemplo, pdfplumber y camelot para tablas en PDF, además de HTML donde exista). Una discrepancia bloquea el build salvo que figure en una allowlist revisada.
- **B2. OCR de respaldo** sólo para páginas escaneadas, marcado como de menor confianza y nunca mezclado en silencio con la extracción de texto.
- **B3. Gramática de tasas.** Gramática formal (Ex., ad valorem, específica, mixta, prohibida, descripciones parciales «Ex.», tasas temporales) con pruebas basadas en propiedades (Hypothesis).
- **B4. Invariantes de jerarquía.** NICO → fracción → HS6 (SA 2022) → HS4 → HS2; sin huérfanos; líneas residuales «Los demás» consistentes; el HS6 de cada fracción existe en la lista de la OMA.
- **B5. Fixtures de referencia (golden)** para capítulos de alto riesgo (textiles, calzado, acero, vehículos, electrónica) y un diff semántico por release que nombra el instrumento detrás de cada cambio.

Prueba: cero discrepancias de parser sin resolver; el conjunto de invariantes pasa en cada fecha histórica de reproducción, no sólo hoy.

### C. Profundidad de la nomenclatura

- **C1. Conformidad con el SA 2022** a seis dígitos, con las tablas de correlación 2017↔2022 de la OMA.
- **C2. Preparación para el SA 2028.** Correlación 2022↔2028 cuando se publique y un plan de migración para la nueva LIGIE que exigirá.
- **C3. Notas legales.** Notas de sección, de capítulo y nacionales (Notas Nacionales) y las Reglas Generales de Interpretación tal como aparecen en la LIGIE, versionadas igual que las tasas.
- **C4. Unidades.** Unidad de medida (UMT) mapeada a los catálogos del Anexo 22 del SAT.
- **C5. Criterios oficiales de clasificación** publicados por el SAT o la ANAM, enlazados por código y con fechas. Las notas explicativas y las opiniones de clasificación de la OMA tienen derechos de autor: sólo se enlazan y referencian, nunca se redistribuyen. **[owner]** confirma esta postura de licencias.

### D. Medidas más allá de la tasa general (cada módulo es opcional; tú eliges)

Cada módulo sigue el mismo patrón que A: inventario de instrumentos → operaciones → vigencia → registro de discrepancias → `AS OF`.

- **D1. Aranceles preferenciales** de los tratados comerciales de México (primero T-MEC/USMCA, después la UE, el CPTPP, la Alianza del Pacífico y los acuerdos de ALADI), incluidos los calendarios de desgravación.
- **D2. Programas sectoriales (PROSEC) y Regla Octava**: tasas y texto de elegibilidad.
- **D3. Cupos** publicados en el DOF.
- **D4. Remedios comerciales.** Cuotas antidumping y compensatorias según resoluciones del DOF (por código, origen, exportador, tasa y vigencia).
- **D5. Regulaciones y restricciones no arancelarias (RRNA).** Acuerdos de la SE, SENASICA, COFEPRIS, SEMARNAT y NOM por código, con vigencia. Se presentan como «un instrumento oficial menciona este código», nunca como «debes cumplir con X».
- **D6. Otros impuestos a la importación** (IVA, IEPS, DTA), sólo como referencias con fecha y únicamente si los quieres.

Prueba: para cada módulo, una muestra de códigos contrastada con la publicación de la autoridad emisora; los conteos por instrumento coinciden con el anexo del instrumento.

### E. Validación externa (independiente de ti y de mí)

- **E1. Rederivación desde el DOF** (desde A).
- **E2. Cobertura de estadísticas de comercio.** Cada fracción con importaciones registradas en las estadísticas de comercio exterior del INEGI para un mes existe y está vigente en el dataset para ese mes. Verificación inversa: se listan los códigos vigentes sin comercio durante 24 meses (no es un error, es una señal).
- **E3. WTO Tariff Download Facility / IDB y Market Access Map del ITC.** Tasas NMF aplicadas comparadas código por código; cada diferencia se explica. **[owner]** registra las cuentas que se requieran.
- **E4. Consistencia con el Anexo 22.** Las combinaciones de fracción, NICO y unidad coinciden con los catálogos del SAT.
- **E5. Auditoría por agente aduanal.** Paquete de muestra estratificado por riesgo y dimensionado con ISO 2859; un agente aduanal con patente lo revisa a ciegas; la tasa de error se reporta con su intervalo de confianza. **[owner]** encuentra y contrata al agente; Claude prepara el paquete y la calificación.
- **E6. Verificación espejo (opcional).** Para las tasas preferenciales del T-MEC, comparar contra las listas publicadas de Estados Unidos y Canadá para las mismas líneas del tratado cuando correspondan.

Regla de release: cada release declara en `manifest.json` qué verificaciones se ejecutaron, sus resultados y sus fechas.

### F. Detección de cambios y alertas

- **F1. Vigilancia diaria del DOF, de sólo lectura.** La vigilancia base ya corre en el job `notify` del Official data pipeline (`scripts/watch_dof.py`), con el diseño de [historial de fuentes](source-history.md) y las decisiones 0001 y 0002. F1 la extiende para detectar instrumentos nuevos que mencionen la LIGIE, los NICO, cupos, cuotas compensatorias, PROSEC o los tratados de D, y abrir un issue con la evidencia. Nunca publica.
- **F2. Vista previa de impacto.** Para un instrumento detectado, una lista borrador de operaciones y los códigos afectados, antes de cualquier release.
- **F3. Notificaciones para consumidores.** Feed de releases (Atom/JSON) y feed de cambios por código, para que los integradores puedan suscribirse a «avísame cuando cambie 8517.13.01».

### G. Superficies de producto

- **G1. Página de línea de tiempo por código:** cada versión de un código con su instrumento, sus fechas y su diff.
- **G2. Comparar dos fechas:** todo lo que cambió entre la fecha X y la Y, filtrable por capítulo y por instrumento.
- **G3. Página de instrumento:** un instrumento del DOF → cada operación que hizo → cada código afectado.
- **G4. Explorador de discrepancias:** el registro de A4/B1, público y con sus resoluciones.
- **G5. Vista de componentes del arancel** (sólo si existen módulos D): muestra cada medida por separado con su fuente y, de forma explícita, no es un cálculo del arancel total. **[owner]** revisa la redacción.
- **G6. API:** archivos estáticos `/data/v1/instruments.json`, `/data/v1/changes/{instrument}.json` y `/data/v1/disagreements.json` generados por el pipeline ([decisión 0002](decisions/0002-arquitectura-github-primero.md)); las rutas equivalentes en el servidor FastAPI propio, y la [política de compatibilidad](compatibility.md) actualizada.

### H. Confianza, gobierno y longevidad

- **H1. Procedencia de la cadena de suministro.** Releases firmadas (Sigstore / atestaciones de artefactos de GitHub) y procedencia de build al estilo SLSA en el manifest.
- **H2. Preservación de fuentes.** Los bytes capturados del DOF se replican en Internet Archive y se guardan con la release; Software Heritage para el código.
- **H3. Datos citables.** DOI de Zenodo por release de datos y `CITATION.cff`. **[owner]** vincula la cuenta de Zenodo.
- **H4. Proceso de corrección.** Formulario público de issue «reportar una discrepancia de datos» → triage → evidencia → corrección → nota de release que da crédito a quien reportó.
- **H5. Revisión de licencias.** Qué se puede redistribuir (DOF, catálogos del SAT, material de la OMA, estadísticas de comercio). **[owner]** decide; Claude prepara la tabla fuente por fuente.
- **H6. Métricas.** Cobertura, retraso de frescura (publicación en el DOF → release), número de discrepancias y tasas de aprobación de las verificaciones externas, publicadas en el sitio.

## 3. Orden propuesto de compuertas

| Compuerta | Contenido | Por qué en este orden |
|---|---|---|
| G0 | Aprobar este programa, el protocolo y las preguntas de postura de licencias (H5, C5). | Fija las reglas. |
| G1 | A1, inventario de instrumentos (sólo investigación, sin cambios de código sobre los datos). | Todo depende de conocer cada instrumento. |
| G2 | A2–A3, operaciones y motor de reproducción detrás de un flag; B3, gramática de tasas. | Modelo central. |
| G3 | B1, B4 y B5, calidad de extracción e invariantes en todas las fechas de reproducción. | Hacer confiable el núcleo antes de exponerlo. |
| G4 | A4, verificación de consolidación y registro de discrepancias; E1, E2 y E4. | Primera prueba independiente. |
| G5 | A5, `AS OF` en CLI, Python y API, y páginas web G1–G3; actualización de esquema y compatibilidad. | Primera release visible para usuarios. |
| G6 | F1–F3, detección de cambios y feeds. | Lo mantiene al día. |
| G7 | C1–C5, profundidad de la nomenclatura; plan para el SA 2028. | |
| G8+ | Módulos D, uno por compuerta, en el orden que elijas. | Mayor alcance; opcional. |
| En paralelo | E3, E5 y H1–H6, a medida que se desbloqueen los pendientes de [owner]. | |

## 4. Lo que necesito de ti

- Sí, no o cambios en cada compuerta.
- Decisiones de licencias (H5, C5).
- Cuentas o registros: acceso a datos de la OMC y el ITC, Zenodo y cualquier fuente de pago.
- El agente aduanal para E5.
- La redacción final de todo lo que pudiera leerse como asesoría (G5, D5).

## 5. Registro de decisiones

| Fecha | Compuerta | Decisión |
|---|---|---|
| 2026-10-16 | G0 | Programa, protocolo y orden de compuertas aprobados tal como están escritos. |
| 2026-10-16 | G0 | Todos los módulos D entran en el alcance eventual (D1 preferencias/TLC, D2 PROSEC/Regla Octava, D3 cupos, D4 remedios comerciales, D5 RRNA/NOM, D6 otros impuestos), cada uno detrás de su propia compuerta. |
| 2026-10-16 | G0 | Las licencias de la OMA y de otro material con derechos de autor quedan diferidas: no se usa ninguna de esas fuentes hasta que se apruebe la tabla de licencias fuente por fuente de H5. |
| 2026-10-16 | G1 | Inventario verificado a nivel de texto con el registro de reformas de la Cámara de Diputados (26 instrumentos y modificaciones). 1,667/1,667 tasas fijadas por decreto coinciden con `data-2026.09.14`; 9803.00.01 está desactualizada después del decreto del 2026-10-13; los campos de vigencia están vacíos en todo el dataset. Captura de bytes pendiente. Ver [inventario de instrumentos](research/ligie-instrument-inventory.md). |
| 2026-10-16 | F1 | Decisión 0001 propuesta: vigilancia diaria de SIDOF con Vercel Cron, un issue de GitHub como confirmación humana y GitHub Actions sólo para build y publicación. Se retiró el workflow adicional de captura. La ubicación de la vigilancia en Vercel Cron quedó reemplazada por la decisión 0002; el resto de 0001 sigue vigente. Ver [decisión 0001](decisions/0001-vigilancia-dof-sidof.md). |
| 2026-10-16 | F1/arquitectura | Decisión 0002 aceptada: GitHub Releases y GitHub Pages guardan y sirven los datos; GitHub Actions hace todo el cómputo con un pipeline diario; Vercel sirve sólo el frontend; `/v1` queda deprecada con retiro el 2027-01-31. 0002 reemplaza la ubicación propuesta en 0001. Ver [decisión 0002](decisions/0002-arquitectura-github-primero.md). |

## Relacionado

- [Arquitectura](architecture.md)
- [Modelo de datos](data-model.md)
- [Inventario de instrumentos de la LIGIE 2022](research/ligie-instrument-inventory.md)
- [Decisión 0002](decisions/0002-arquitectura-github-primero.md)
- [Historial de fuentes](source-history.md)
