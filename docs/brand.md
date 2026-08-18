# Marca y presentación de `arancel-mx`

Esta guía define la identidad visual y narrativa pública de `arancel-mx`. El objetivo no es decorar el proyecto: es hacer visible, desde el primer vistazo, qué problema resuelve, qué superficies ofrece y por qué sus datos son verificables.

## Idea de marca

`arancel-mx` convierte publicaciones oficiales arancelarias de México en una capa de datos abierta, reproducible y auditable.

La marca debe comunicar cuatro ideas sin exagerarlas:

1. **México**: contexto aduanero y arancelario mexicano.
2. **Datos**: una infraestructura consumible por archivos, DuckDB, Python, CLI y HTTP.
3. **Verificación**: procedencia, hashes, validación y releases inmutables.
4. **Apertura**: un núcleo público reusable por otras herramientas de comercio exterior.

La frase corta de posicionamiento es:

> **Datos arancelarios abiertos de México. Trazables, auditables y reproducibles.**

Para material en inglés puede usarse:

> **Open tariff data for Mexico. Traceable. Auditable. Reproducible.**

## Sistema visual

### Paleta

| Token | Hex | Uso principal |
|---|---|---|
| Navy | `#102A43` | identidad, títulos, estructura y confianza |
| Deep navy | `#071827` | portadas y superficies oscuras |
| Mexico green | `#008A5B` | acción, validación, punto de `arancel.mx` y brackets |
| Mexico red | `#CE1126` | acento aduanero mexicano, siempre secundario |
| Off-white | `#F8FAFC` | fondos claros y documento del mark |
| Cool gray | `#D8E2EA` | detalle técnico secundario |

El rojo no debe competir con el verde ni convertirse en color de llamada a la acción. Su función es dar contexto visual mexicano al mark y a detalles muy puntuales.

### Mark

El símbolo combina:

- un candado/gateway para representar control e integridad;
- un documento para representar evidencia oficial;
- una marca de verificación para representar validación;
- paneles verde y rojo para representar el contexto mexicano y el flujo de mercancías.

No significa certificación gubernamental ni sustituye sellos oficiales. Es una identidad visual del proyecto.

### Wordmark

El nombre se presenta como `arancel.mx` en minúsculas, con:

- navy como color principal;
- punto verde antes de `mx`;
- brackets verdes para sugerir una herramienta de datos/programación sin convertir el logo en una consola literal.

## Assets canónicos

| Asset | Función |
|---|---|
| `docs/assets/arancel-mx-logo.svg` | logo horizontal principal para documentación y presentaciones |
| `website/assets/arancel-mx-mark.svg` | mark compacto para favicon y navegación |
| `website/assets/arancel-mx-logo.svg` | wordmark horizontal desplegable en el sitio |
| `docs/assets/arancel-mx-banner.svg` | hero del README |
| `docs/assets/arancel-mx-social.svg` | fuente vectorial 1280×640 para sharing/social |
| `website/assets/arancel-mx-social.svg` | copia desplegable de la composición social |
| `docs/assets/arancel-mx-cover.svg` | portada oscura 1600×900 para presentaciones y documentación |

Los SVG son los masters de marca. Deben mantenerse como vector real: no incrustar PNG/JPEG ni payloads base64 dentro de ellos.

Cuando una plataforma exija PNG/JPG para una imagen social, el raster debe exportarse desde `arancel-mx-social.svg`; no debe convertirse el master del repositorio en un archivo raster ni envolver una imagen raster dentro de un SVG.

## Uso del logo

### Sí

- mantener espacio libre alrededor del mark y del wordmark;
- conservar proporciones y colores canónicos;
- usar el mark solo cuando el espacio es pequeño;
- usar el wordmark completo cuando la identidad del proyecto necesita ser explícita;
- usar fondos claros o deep navy con contraste suficiente;
- conservar `<title>` y `<desc>` en assets SVG públicos.

### No

- estirar el logo horizontal o verticalmente;
- cambiar el punto verde a rojo;
- usar el rojo como color dominante;
- añadir escudos, sellos o elementos que puedan sugerir afiliación gubernamental;
- añadir sombras, 3D o ilustración ornamental que compita con el carácter técnico;
- incrustar capturas raster dentro del SVG para simular un vector.

## Storytelling

La presentación pública debe seguir este orden:

```text
qué es
  ↓
por qué existe
  ↓
qué quiero hacer con él
  ↓
qué interfaz uso
  ↓
por qué confiar en el resultado
  ↓
cómo funciona por dentro
```

### 1. Qué es

Una capa pública de datos arancelarios mexicanos que transforma fuentes oficiales observadas en releases verificables y fáciles de consumir.

### 2. Por qué existe

Un archivo oficial por sí solo no resuelve procedencia, cambios, jerarquía, normalización, reproducibilidad ni consumo aguas abajo. `arancel-mx` concentra ese trabajo para que cada aplicación consumidora no tenga que rehacerlo.

### 3. Qué puede hacer el usuario

Las cinco rutas canónicas son:

| Intención | Superficie |
|---|---|
| Analizar datos | DuckDB / CSV / JSON |
| Consultar rápidamente | CLI |
| Integrar una aplicación | Python `Dataset` |
| Construir un servicio o UI | HTTP / API read-only |
| Verificar cómo se produjo | manifest, SHA256, fuentes capturadas, `provenance`, `data verify` |

### 4. Confianza antes que claims

La narrativa no debe basarse en “tenemos datos actualizados”. Debe mostrar la cadena verificable:

```text
fuentes oficiales
  ↓
captura
  ↓
identidad + SHA256 + retrieved_at
  ↓
reconciliación legal
  ↓
parseo + normalización + validación
  ↓
DuckDB canónico
  ↓
release inmutable + manifest + checksums
```

La release verificada es la fuente de verdad. Las capas de búsqueda, metadata y servicio son superficies de consumo, no sustitutos del pipeline de publicación.

## Voz y copy

Preferir:

- concreto sobre promocional;
- verificable sobre superlativo;
- “read-only”, “fail-closed”, “release verificada” y “procedencia” cuando sean relevantes;
- ejemplos reales de comandos y archivos;
- separar claramente información técnica de interpretación jurídica.

Evitar:

- “la clasificación correcta garantizada”;
- “100% actualizado” sin contexto verificable;
- lenguaje que sugiera respaldo de SAT, ANAM, SNICE, DOF o cualquier otra autoridad;
- convertir una herramienta de datos en promesa de asesoría aduanera.

## Presentaciones

`docs/assets/arancel-mx-cover.svg` es la portada recomendada para decks. Una presentación debe llevar al lector de problema → capa de datos → superficies de consumo → cadena de confianza → arquitectura → caso de uso.

El proyecto puede explicar capacidades avanzadas después, pero el primer minuto debe responder:

> ¿Qué problema elimina `arancel-mx` y por qué debería consumir esta capa en vez de volver a construirla?

## Sitio web

Los assets mantenibles del sitio viven bajo `website/assets/`. `site-brand.css` es la frontera estable para tokens visuales y selectores de marca.

No se deben editar manualmente los bundles `website/assets/index-*.js` / `index-*.css` ni el runtime generado dentro de `website/index.html` sólo para cambiar branding. Un cambio de esa naturaleza debe hacerse en la fuente que genere esos artefactos y luego regenerarse de manera reproducible.

## Relación con la arquitectura actual

Desde la integración #132, el hub público combina metadata/búsqueda operational en Vercel/Neon con rutas proxificadas al runtime FastAPI reusable. El branding debe explicar esa superficie sin alterar sus fronteras. La release verificada sigue siendo la fuente canónica para sincronización y auditoría.

El **Official data pipeline** usa actualmente una revisión programada semanal los lunes. El branding y la narrativa nunca deben convertir frecuencias de automatización en promesas de frescura legal; la confianza proviene de la identidad de la release y su evidencia.

## Checklist antes de publicar una pieza nueva

- [ ] Usa un asset canónico o una exportación directa de éste.
- [ ] El logo conserva proporciones y colores.
- [ ] No sugiere afiliación gubernamental.
- [ ] El copy explica una capacidad real del repositorio.
- [ ] La superficie recomendada coincide con el caso de uso.
- [ ] Los claims de confianza pueden relacionarse con una release, manifest, hash o fuente.
- [ ] La pieza sigue siendo legible en tamaño pequeño o thumbnail.
- [ ] Si es SVG, sigue siendo vector real y conserva metadata accesible.
