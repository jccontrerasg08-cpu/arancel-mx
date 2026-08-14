# Fuentes oficiales

`arancel-mx` sólo incorpora al build oficial documentos descubiertos mediante un registro versionado y adaptadores de dominio permitidos. La existencia de un snapshot en una página oficial no basta por sí sola para hacerlo publicable: la identidad, procedencia y reconciliación legal deben superar los gates del pipeline.

## Dominios y funciones

- `diputados.gob.mx`: **registered ledger** de la LIGIE, texto vigente, reformas y documentos asociados.
- `dof.gob.mx`: evidencia DOF de publicación, modificación y vigencia.
- `snice.gob.mx`: libros operativos de LIGIE, NICO, notas, indicadores y publicaciones relacionadas de la Secretaría de Economía.

## Registro versionado

`src/arancel_mx/sources/source_registry.json` define por conjunto la clave, `registry_version`, página canónica, papel de la fuente, autoridad jurídica, autoridad de descubrimiento, fecha efectiva, perfiles esperados y reglas de clasificación.

El registro funciona como allowlist y como parte de la procedencia reproducible. Cambiarlo modifica qué documentos pueden entrar al pipeline y por eso debe llegar como cambio revisable, con tests/fixtures offline.

## Lista permitida y descubrimiento

Los adaptadores aceptan únicamente hosts oficiales registrados. Redirecciones fuera de política, extensiones inesperadas, páginas auxiliares, cero candidatos o múltiples candidatos igualmente válidos fallan cerrados en vez de seleccionar una fuente por heurística débil.

Cada source role tiene expectativas explícitas. Las páginas de propuestas o indicadores pueden servir como contexto/observación, pero no sustituyen automáticamente la evidencia legal aplicable.

## Identidad de captura

Cada descarga conserva como mínimo la URL final, SHA256, tamaño, tipo de medio, procedencia y `retrieved_at`.

`retrieved_at` es la hora real de recuperación HTTP del snapshot, no la hora de generación del dataset. El manifest también contiene `generated_at` para representar la ejecución que produjo el candidato/release; ambos campos son semánticamente distintos.

Un parseo sólo puede reutilizarse cuando la identidad capturada y las versiones relevantes de parser/esquema/registro siguen siendo compatibles.

## Compilaciones no oficiales

El pipeline **no** captura ni publica SIICEX-CAAAREM, dumps de entrenamiento como [tigies-mx](https://github.com/andyeswong/tigies-mx), ni otros visores TIGIE de terceros.

- `http://www.siicex-caaarem.org.mx/` is not an official source. Es un visor compilado de la confederación de agentes aduanales (HTTP, Lotus Notes). Puede mostrar IGI/IGE, permisos, TLC y PROSEC, pero no es Diputados, DOF ni SNICE, y el fetch oficial exige HTTPS sobre hosts registrados.
- `tigies-mx` es un dump estático para entrenar modelos (capítulos, TIGIE plana, correlación SCIAN). No tiene procedencia SHA256 ni reconciliación legal.
- Dumps como `tigieX.json` / `arcosNuevos.txt` son el mismo tipo: árboles de 8 dígitos sin IGI/NICO ni SHA256. No son fallback cuando SNICE falla.
- Los Anexos RGCE 1–30 y los instructivos de pedimento (SAT) no entran al registro. Un consumidor puede cruzar `fraccion8`/`nico10` con esas listas; Anexo 9 (exención IGI) no sustituye el `igi_text` de LIGIE.

La ficha pública de `arancel-mx` (`arancel-mx ficha` / `Dataset.ficha`) reproduce la navegación capítulo → partida → subpartida → fracción → NICO y las tasas IGI/IGE **sólo** desde el dataset oficial verificado. No inventa IVA, franja/región, permisos, TLC, PROSEC ni correlaciones SCIAN que esas compilaciones muestran y que este registro no captura.

Un visor de terceros puede mostrar fracciones o tasas que ya no existen en la LIGIE vigente. El ejemplo SIICEX `11063001` (harina de sagú, IGI 13%) no está en el snapshot SNICE actual; las fracciones vigentes son `11062002` (sagú, IGI 10) y `11063002` (productos del Capítulo 08, IGI 10). `arancel-mx ficha 11063001` falla cerrado.

## Diputados ledger + DOF reconciliation

El ledger **registered** de la Cámara de Diputados es el ancla para saber qué documentos legales deben ser explicables por la construcción. El pipeline realiza **reconciliation** de ese ledger con evidencia del **DOF** y con las fuentes registradas de SNICE.

La reconciliación es un **blocking gate** antes de publicación. Entre otros casos, la construcción queda bloqueada si una entrada legal esperada carece de evidencia DOF suficiente, si las identidades documentales no concuerdan o si existe una **discrepancy** material que no puede explicarse con las reglas registradas.

El parser del ledger distingue `last_law_reform` (reforma de la ley) de `latest_tariff_modification` (decreto de fracciones). La release pública `data-2026.08.11` registra `law_reform` 2025-12-29 (`LIGIE_2022_ref02_29dic25.pdf`) y `tariff_decree` 2026-04-23 (`LIGIE_2022_tarifa15_23abr26.pdf`). El fixture del parser espera las mismas fechas. No se copian de visores de terceros.

La prioridad no se resuelve silenciosamente: la publicación jurídica y el texto legal gobiernan la vigencia; los libros operativos aportan estructura utilizable. Una discrepancia se conserva en diagnósticos y bloquea **publication**.

Esto no convierte al repositorio en una fuente de asesoría jurídica. El sistema verifica consistencia entre evidencia observada y reglas registradas; la validez jurídica final depende de las publicaciones oficiales aplicables.

## Cambios y no-op

Después de capturar y reconciliar, la identidad de las fuentes se compara con el último `manifest.json` publicado. Si no cambió, el pipeline devuelve `no_change`, termina en verde y no crea una nueva release. Si cambió, sólo avanza si todos los gates legales, de parser y de validación pasan.

## Evidencia preservada

Una release válida incluye `official-sources.tar.gz`, que conserva los bytes oficiales capturados —incluidos el ledger registered de Diputados que ancla la reconciliación legal— y `source_capture.json`. Los hashes permiten reconstruir exactamente qué snapshots fueron observados en ese build aunque la página oficial cambie después.

## Páginas canónicas documentadas

Estas son las URLs públicas registradas y referenciadas por el proyecto. Deben permanecer en HTTPS y en formato de enlace Markdown en la documentación orientada a usuarios:

- [Diputados, ledger LIGIE](https://www.diputados.gob.mx/LeyesBiblio/ref/ligie_2022.htm)
- [Diputados, texto consolidado PDF](https://www.diputados.gob.mx/LeyesBiblio/pdf/LIGIE_2022.pdf)
- [SNICE, LIGIE](https://www.snice.gob.mx/cs/avi/snice/ligie.info22.html)
- [SNICE, NICO y propuestas](https://www.snice.gob.mx/cs/avi/snice/ligie.nico2022.html)
- [SNICE, notas nacionales](https://www.snice.gob.mx/cs/avi/snice/ligie.notasnac22.html)
- [SNICE, indicadores arancelarios](https://www.snice.gob.mx/cs/avi/snice/ligie.indicaranc22.html)
- [DOF, metodología NICO (27/06/2022)](https://dof.gob.mx/nota_detalle.php?codigo=5656249&fecha=27/06/2022)

## Páginas HTML operativas

El pipeline y la consulta pública dependen de estas páginas HTML oficiales:

- [Diputados, ledger LIGIE](https://www.diputados.gob.mx/LeyesBiblio/ref/ligie_2022.htm) — parseo del ledger legal.
- [SNICE, índice LIGIE](https://www.snice.gob.mx/cs/avi/snice/ligie.info22.html) — descubrimiento de snapshots `FRACCIONESARANCELARIAS*.xlsx`.
- [SNICE, índice NICO](https://www.snice.gob.mx/cs/avi/snice/ligie.nico2022.html) — descubrimiento de snapshots `NICO-*.xlsx`.
- [SNICE, modificaciones](https://www.snice.gob.mx/cs/avi/snice/ligie.info22.mod.html) — índice de modificaciones publicadas.
- [SNICE, biblioteca jurídica general](https://www.snice.gob.mx/cs/avi/snice/biblioteca.juridica.html) — índice legal de SNICE con enlace a la LIGIE.
- [SNICE, biblioteca jurídica LIGIE](https://www.snice.gob.mx/cs/avi/snice/ligie.info22.ligiebibjur.html) — entrada a la consulta oficial de fracciones.
- [SNICE, clasificador individual](https://www.snice.gob.mx/cs/avi/snice/hce.mi.fraccion.arancelaria.html) — consulta individual de códigos.
- [VUCEM, buscador de fracciones](https://www.ventanillaunica.gob.mx/vucem/Clasificador.html) — clasificador informativo de la Ventanilla Única.
- [VUCEM, ficha de fracción 90014002](https://www.ventanillaunica.gob.mx/Clasificador/data/buildHojas1/90014002.html) — ejemplo de hoja HTML por código de 8 dígitos (`buildHojas1/{codigo}.html`).
- [SIICEX-CAAAREM](http://www.siicex-caaarem.org.mx/) — portal de consulta histórica de la tarifa mantenida por CAAAREM (HTTP legado).

`python -m scripts.validate_ligie_html_pages` verifica que sigan siendo alcanzables, que el HTML contenga contenido utilizable y que los recursos enlazados respondan.

`python -m scripts.check_documented_urls` verifica que estas URLs sigan siendo alcanzables desde CI y descarga el cuerpo HTML de las páginas documentadas.

## Fixtures offline

Las pruebas de PR usan fragmentos mínimos y sanitizados en `tests/fixtures/` y no dependen de que DOF, Diputados o SNICE estén disponibles en ese momento. Cada cambio de parser, reconciliación o source registry debe incluir un fixture reproducible o una construcción sintética equivalente.
