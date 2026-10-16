# Decisión 0001: vigilancia diaria del DOF con SIDOF y ejecución por evento

- **Estado:** reemplazada en parte por la [decisión 0002](0002-arquitectura-github-primero.md)
- **Fecha:** 2026-10-16
- **Responsable:** @jccontrerasg08-cpu
- **Revisión:** el objetivo (vigilancia diaria con SIDOF e issue como confirmación humana) se aprobó el 2026-10-16. La ubicación propuesta (Vercel Cron y Neon) se descartó: la vigilancia corre en el job `notify` del pipeline oficial de GitHub Actions (`scripts/watch_dof.py`).
- **Enlaces:** `docs/depth-program.md` (F1), `docs/research/ligie-instrument-inventory.md`

## Contexto

El pipeline oficial corre a ciegas cada lunes en GitHub Actions y lee la Tarifa del libro de SNICE. El decreto del DOF del 2026-10-13 (9803.00.01 → Ex.) entró en vigor el 2026-10-14. SNICE publicó `FRACCIONESARANCELARIAS-LIGIE_20261014` ese mismo día, pero la release vigente (`data-2026.09.14`) sigue con 10 % hasta la próxima ejecución semanal. No existe ningún aviso entre la publicación en el DOF y la release.

Durante la revisión de fuentes se verificó en vivo que el DOF ofrece servicios web oficiales y documentados (SIDOF, «Datos abiertos», manuales de diciembre de 2018):

| Servicio | URL | Uso |
|---|---|---|
| Notas por fecha | `https://sidofqa.segob.gob.mx/dof/sidof/notas/{DD-MM-AAAA}` | Lista todas las notas del día con `codNota`, `titulo`, edición y `codDiario`. Probado con 2026-10-13: devuelve la nota 5800977 del decreto de Tarifa. |
| Nota por código | `…/notas/nota/{codNota}` | HTML de la nota. |
| Word de la nota | `…/documentos/doc/{codNota}` | Texto editable del instrumento. |
| PDF de la edición | `…/documentos/pdf/{codDiario}` | Edición completa con e.firma del DOF (ediciones desde el 5 de julio de 2012). |
| Diarios por fecha | `…/diarios/porFecha/{DD-MM-AAAA}` | Ediciones y secciones del día. |

Esto vuelve innecesario raspar páginas del DOF o de la Cámara de Diputados para detectar instrumentos nuevos.

## Decisión

Separar el trabajo en tres capas, cada una en el lugar que ya existe y le conviene:

1. **Vigilar (Vercel Cron, diario).** Una función `api/watch_dof.py`, con el mismo patrón y `CRON_SECRET` que `api/sync_operational.py`, consulta SIDOF para cada día pendiente desde el último día revisado. Así recupera días perdidos, porque Vercel Hobby ejecuta una vez al día, con margen de una hora, sin reintentos. Filtra los títulos con `arancel_mx.sources.sidof.tariff_candidates` y guarda los días revisados y los candidatos en Neon, con claves idempotentes por `codNota`. También compara el libro de fracciones más reciente de SNICE (`latest_snice_fractions_workbook`) con el que usó la release vigente.
2. **Avisar y decidir (persona).** Si hay candidatos nuevos o un libro SNICE más reciente, la función abre un issue de GitHub con la nota, sus enlaces y lo que cambió. Esa es la confirmación humana; nada se publica solo.
3. **Construir y publicar (GitHub Actions, sin cambios de fondo).** El pipeline oficial sigue siendo el único camino de publicación, porque ahí viven la certificación, las atestaciones y las releases inmutables. Se añade el disparo `repository_dispatch` desde el aviso; la ejecución semanal queda como red de seguridad.

El rastreador de la Cámara de Diputados (`scripts/capture_instrument_research.py`) queda como herramienta local de respaldo histórico y deja de tener workflow propio.

**Criterio observable:** cuando el DOF publique un instrumento de Tarifa, existe un issue con su `codNota` dentro de las 24 horas siguientes a su publicación, y la release que lo recoge enlaza la nota.

## Alternativas

- **Workflow programado diario en GitHub Actions.** Funciona, pero añade otro workflow y otra ejecución a ciegas. Además, el repositorio documenta que Diputados y VUCEM cortan TLS desde Actions.
- **Cloudflare Worker con R2.** Barato y preciso, pero es otra plataforma y otro despliegue, y su `fetch` no permite bajar a `SECLEVEL=1` si un host oficial lo exige.
- **Railway cron.** El contenedor ya existe como respaldo, pero el objetivo es retirar o reducir esa superficie, no ampliarla.
- **Servicios de terceros para obtener páginas.** Sirvieron para la investigación, pero no son una fuente reproducible ni deben estar en la ruta de publicación.

## Compatibilidad

No cambia la API pública, el esquema ni el formato de las releases. Requiere:
- dos tablas nuevas en Neon (`dof_watch_day`, `dof_instrument_candidate`);
- un token de GitHub de alcance mínimo (issues y `repository_dispatch` de este repositorio) como variable de entorno en Vercel;
- una línea nueva en `crons` de `vercel.json`.

## Consecuencias y seguimiento

1. Probar desde una función de Vercel que `sidofqa.segob.gob.mx` y `www.snice.gob.mx` responden con la sesión oficial (`build_official_session`). Si falla, se reevalúa el lugar de la capa 1 antes de seguir.
2. Implementar `api/watch_dof.py`, las tablas y las pruebas sin red, con fixtures reales de SIDOF.
3. Añadir `repository_dispatch` al pipeline oficial.
4. Retirar `.github/workflows/instrument-research-capture.yml` (hecho en esta rama).
