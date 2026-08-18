# Marca y presentación de `arancel-mx`

Esta guía define la identidad visual y narrativa pública de `arancel-mx`. El objetivo no es decorar el proyecto: es hacer visible, con el menor ruido posible, qué problema resuelve, qué superficies ofrece y por qué sus datos son verificables.

**[Hub público](https://arancel-mx.vercel.app/)** · **[API / OpenAPI](https://arancel-mx.vercel.app/docs)** · **[Visión del proyecto](project-overview.md)** · **[Centro de documentación](README.md)**

## Idea de marca

`arancel-mx` convierte publicaciones oficiales arancelarias de México en una capa de datos abierta, reproducible y auditable.

La marca comunica cuatro ideas:

1. **México**: contexto arancelario y aduanero mexicano.
2. **Datos**: infraestructura consumible por archivos, DuckDB, Python, CLI y HTTP.
3. **Verificación**: procedencia, hashes, validación y releases inmutables.
4. **Apertura**: un núcleo público reusable por otras herramientas.

Posicionamiento corto:

> **Datos arancelarios abiertos de México. Trazables, auditables y reproducibles.**

En inglés:

> **Open tariff data for Mexico. Traceable. Auditable. Reproducible.**

## Sistema visual

### Paleta

| Token | Hex | Uso principal |
|---|---|---|
| Navy | `#102A43` | identidad, títulos, estructura y confianza |
| Deep navy | `#071827` | portadas y superficies oscuras |
| Mexico green | `#008A5B` | acción, validación, punto de `arancel.mx` y brackets |
| Mexico red | `#CE1126` | acento mexicano secundario |
| Off-white | `#F8FAFC` | fondos claros y documento del mark |
| Cool gray | `#D8E2EA` | detalle técnico secundario |

El rojo nunca debe competir con el verde como color de acción. Su función es contextual y secundaria.

### Mark

El símbolo combina un gateway/candado, un documento y una marca de verificación con acentos verde y rojo. Representa integridad, evidencia y contexto mexicano. **No representa certificación gubernamental ni afiliación con una autoridad.**

### Wordmark

El nombre se presenta como `arancel.mx` en minúsculas, con navy como color principal, punto verde antes de `mx` y brackets verdes como referencia discreta a datos/programación.

## Assets canónicos

| Asset | Función |
|---|---|
| `docs/assets/arancel-mx-logo.svg` | logo horizontal principal |
| `website/assets/arancel-mx-mark.svg` | mark compacto para navegación |
| `website/assets/arancel-mx-logo.svg` | wordmark desplegable del sitio |
| `docs/assets/arancel-mx-banner.svg` | hero del README |
| `docs/assets/arancel-mx-social.svg` | master social 1280×640 |
| `website/assets/arancel-mx-social.svg` | copia desplegable social |
| `docs/assets/arancel-mx-cover.svg` | portada 1600×900 para presentaciones |

Los SVG son masters vectoriales. No incrustar PNG/JPEG, elementos `<image>` ni payloads base64. Si una plataforma exige raster, exportarlo desde el master SVG sin reemplazar el archivo canónico.

## Uso del logo

**Sí:** conservar proporciones, colores, espacio libre, `<title>`/`<desc>` y usar el mark solo cuando el espacio sea reducido.

**No:** estirar, dominar con rojo, añadir sellos/escudos oficiales, añadir 3D/sombras ornamentales o alterar el símbolo de forma que sugiera respaldo gubernamental.

## Storytelling

Hay dos niveles narrativos distintos.

### Front door: README y home

La primera experiencia debe ser breve y orientada a acción:

```text
qué es
  ↓
qué puede hacer el usuario
  ↓
pruébalo en 60 segundos
  ↓
por qué confiar
  ↓
dónde profundizar
  ↓
alcance y límites
```

El README no debe intentar ser manual de CLI, runbook de release, catálogo de tablas y documentación operativa al mismo tiempo. Es una **landing técnica** que manda el detalle al centro de documentación.

### Visión profunda del proyecto

Cuando el lector ya decidió profundizar, [`project-overview.md`](project-overview.md) sigue una secuencia más completa:

```text
problema
  ↓
frontera del proyecto
  ↓
fuentes → release verificable
  ↓
superficies de consumo
  ↓
Central Hub en Vercel
  ↓
modelo de confianza
```

## Cinco rutas de consumo

| Intención | Superficie |
|---|---|
| Analizar datos | DuckDB / CSV / JSON |
| Consultar rápidamente | CLI |
| Integrar una aplicación | Python `Dataset` |
| Construir un servicio o UI | HTTP / API read-only |
| Verificar cómo se produjo | manifest, SHA256, fuentes capturadas, `provenance`, `data verify` |

El hub web es la entrada interactiva que reúne estas rutas, no una sexta fuente de verdad.

## Confianza antes que claims

Evitar “100% actualizado” o equivalentes. Mostrar la cadena que puede comprobarse:

```text
fuentes oficiales
  ↓
captura
  ↓
identidad + SHA256 + retrieved_at
  ↓
reconciliación y validación
  ↓
DuckDB canónico
  ↓
release inmutable + manifest + checksums
```

La release verificada es la fuente de verdad. Búsqueda, metadata, Neon, Vercel y FastAPI son superficies de consumo o proyecciones operacionales.

## Voz y copy

Preferir lenguaje:

- concreto sobre promocional;
- verificable sobre superlativo;
- breve en la portada y profundo en docs;
- explícito sobre `read-only`, `fail-closed`, release y procedencia cuando sean relevantes;
- claro al separar datos técnicos de interpretación jurídica.

Evitar:

- “clasificación correcta garantizada”;
- “100% actualizado” sin identidad de release;
- claims que sugieran respaldo de SAT, ANAM, SNICE, DOF o cualquier autoridad;
- prometer asesoría o cumplimiento automático;
- repetir el mismo detalle técnico en README, hub y varias guías.

## Sitio web y relación con Vercel

El dominio público principal es [`https://arancel-mx.vercel.app/`](https://arancel-mx.vercel.app/). La documentación debe tratarlo como el **front door interactivo** y enlazar también su contrato OpenAPI en [`/docs`](https://arancel-mx.vercel.app/docs).

La arquitectura vigente combina:

- `/v1/meta` y `/v1/search` en la capa operacional read-only de Vercel/Neon;
- las demás rutas `/v1/*`, `/docs` y `/readyz` bajo el mismo dominio mediante proxy al runtime FastAPI reusable;
- la GitHub Release verificable como fuente canónica del dataset.

Desde #139, Vercel bundlea `psycopg[binary]>=3.3.4` de forma aislada en `api/_vendor` mediante `buildCommand` y sólo lo incluye en las funciones operativas. `requirements.txt` fue eliminado para que ese driver no se convierta en dependencia base del paquete. Esta decisión no es copy promocional, pero las guías técnicas deben permanecer sincronizadas con ella.

Los assets mantenibles del sitio viven bajo `website/assets/`. No editar manualmente los bundles `website/assets/index-*.js`, `index-*.css` ni el runtime generado en `website/index.html` sólo para cambiar branding.

## Presentaciones

`docs/assets/arancel-mx-cover.svg` es la portada recomendada. Una presentación puede profundizar más que el README, pero su primer minuto debe responder:

> ¿Qué problema elimina `arancel-mx`, qué puedo consumir y cómo verifico la procedencia?

## Checklist antes de publicar

- [ ] Usa un asset canónico o una exportación directa.
- [ ] El logo conserva proporciones y colores.
- [ ] No sugiere afiliación gubernamental.
- [ ] El copy describe una capacidad real.
- [ ] La superficie recomendada coincide con el caso de uso.
- [ ] Los claims de confianza se pueden relacionar con release, manifest, hash o fuente.
- [ ] El README sigue siendo una landing breve y el detalle vive en `docs/`.
- [ ] Los enlaces públicos apuntan al hub `https://arancel-mx.vercel.app/` cuando corresponde.
- [ ] Si es SVG, sigue siendo vector real y conserva metadata accesible.
