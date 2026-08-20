# Atlas visual de `arancel-mx`

Este atlas vincula cada superficie de lectura con un recurso visual cuyo propósito es **orientar la navegación**, no sustituir una fuente jurídica ni sugerir aval institucional. La wiki de GitHub no está habilitada en el repositorio; por ello, este documento y el índice bajo `docs/` constituyen la superficie documental mantenida.

![Ruta de comercio exterior](assets/visuals/trade-route-atlas.jpg)

## Biblioteca de activos

| Activo | Uso | Procedencia y tratamiento | Restricción de uso |
|---|---|---|---|
| `trade-route-atlas.jpg` | Hero de la mesa de comercio exterior; LIGIE/NICO, origen y tránsito. | Ilustración original de proyecto, sin texto, emblemas ni marcas de terceros. | Mantener el área oscura izquierda para encabezados; no usarla como representación de una aduana, puerto o autoridad determinada. |
| `evidence-ledger.jpg` | Fuentes, clasificación, vigencia, trazabilidad y proceso de release. | Ilustración original de proyecto, sin texto, emblemas ni marcas de terceros. | Usar junto con el aviso de que una hipótesis no equivale a una determinación. |
| Banderas de México, Estados Unidos y Canadá | Contexto visual del T-MEC y origen declarado. | Se sirven desde FlagCDN mediante códigos ISO de dos letras y tamaños explícitos.[1] | Son contexto geográfico: nunca acreditan origen, preferencia, residencia ni cumplimiento. |
| Identidad del Gobierno de México | Encabezado del directorio de portales de autoridad. | Se solicita al CDN institucional y se acompaña de enlaces a los portales de las autoridades. La guía de identidad pública debe revisarse antes de cualquier reutilización más amplia.[2] | No se almacena como un activo de `arancel-mx`, no se altera y no se presenta como patrocinio o aval. |

## Taxonomía por capítulo y sección

| Tema de la wiki | Señal visual | Aplicación recomendada |
|---|---|---|
| **LIGIE, NICO y jerarquía** | Ruta marítima y contenedores. | Portadas de exploración, navegación de capítulo y referencias a la release publicada. |
| **Clasificación, fichas y procedencia** | Expediente, lupa y globo. | Explicar hipótesis, fuente observada, vigencia y evidencia técnica. |
| **T-MEC y origen** | Trío de banderas accesibles con nombre de país. | Indicar el alcance geográfico de una revisión documental, sin inferir preferencia. |
| **RRNA, VUCEM y despacho** | Rail de portales oficiales. | Enlaces visibles a SNICE, VUCEM, SAT y ANAM; la acción sigue ocurriendo fuera de la plataforma. |
| **Fuentes, reconciliación y release** | Expediente documental, capas y rutas sutiles. | Materializar la cadena de confianza: captura, validación, manifest y distribución. |
| **CLI, API y consumo externo** | Motivos de datos discretos, sin fotografía. | Conservar el foco en contratos, ejemplos y formatos legibles. |

> Las marcas, nombres y logotipos de autoridades pertenecen a sus respectivos titulares. El uso editorial en esta plataforma se limita a identificar una fuente enlazada y no implica relación, autorización, patrocinio ni validación por parte de esas instituciones.

## Implementación y accesibilidad

Las imágenes locales se publican de manera idéntica desde `website/assets/visuals/` y desde los activos estáticos del runtime. Cada imagen incluye dimensiones, texto alternativo y carga diferida cuando no es crítica. Las banderas usan `<img>` con `alt` específico por país, `src` explícito y dimensiones reservadas; el patrón de URL está documentado por FlagCDN.[1]

El directorio de autoridades conserva enlaces explícitos y la marca institucional se trata como referencia de fuente. Para evitar dependencia innecesaria, el sitio no incorpora bibliotecas completas de banderas. Si en el futuro se requiere operación offline o un conjunto mayor de países, `lipis/flag-icons` es una alternativa mantenida bajo licencia MIT que permite incluir únicamente los países necesarios.[3]

## Referencias

[1] [FlagCDN — formatos, tamaños y patrón de integración](https://flagpedia.net/download/api)

[2] [Gobierno de México — Guía de identidad gráfica 2024–2030](https://www.gob.mx/salud/conbioetica/documentos/manual-de-identidad-grafica-2025)

[3] [`lipis/flag-icons` — colección SVG con licencia MIT](https://github.com/lipis/flag-icons)
