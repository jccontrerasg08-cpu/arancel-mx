# RFC: Guías MOA por régimen, COVE y prevalidación documental

> Prioridad P1 | Estado: solo especificación | Corte: 2026-11-21
> Basado en el contenido visible de la conversación Gemini y el [inventario de 42 entradas](../../research/notebooklm-source-inventory-2026-11-21.json) junto a [auditoría](../../research/notebooklm-source-audit-2026-11-21.md). La investigación original tiene límites de acceso.

## Punto de partida / capacidad existente

Ya existe /moa y mapas oficiales ANAM, pero la ANAM avisa que su Manual de Operación Aduanera está en actualización; /trade incluye checklists y referencias RGCE, no transmite expedientes.

## Producto esperado

Navegador educativo por régimen aduanero (artículo 90 LA) que conecte fuentes MOA, Ley Aduanera, RGCE, Anexo 22, COVE, prevalidación, avisos, autorizaciones, padrones, documentos y autoridades con el hecho declarado de la operación.

## Diseño técnico, UX, fuentes y límites

- Taxonomía de regímenes: definitivos, temporales (retorno sin cambio / IMMEX), depósito fiscal, tránsito, elaboración-transformación en recinto fiscalizado y recinto fiscalizado estratégico.
- Un paso mostrado siempre será «revisar fuente» y nunca «debes tramitar» salvo que se haya evaluado un instrumento vigente y la condición esté expresamente documentada.
- Los conceptos COVE, transmisión previa de valor, datos del pedimento, validación/prevalidación, anexos, forma de pago y documentación deben citar artículo/regla/apéndice según fecha y expediente.
- Cada nodo de guía tendrá status: official_reference, provisional, historically_dated, unverified; si la página ANAM está en actualización mostrar aviso prominente.
- VUCEM/SAT/ANAM son plataformas transaccionales externas: no integrar credenciales, efectuar pagos, transmitir pedimentos o modificar padrones.
- Diseñar UX con árbol de pasos (orientación) y enlaces a norma, documentos, estado/version, glosario y listas de preguntas para el agente aduanal.
- Distinguir autoridades sanitario/zoosanitario/fitosanitario/ambiental y sus atribuciones; no deducir permisos por NICO sin instrumento.
- No duplicar /moa ni el mapa existente: reutilizar contenido y profundizar con rutas por régimen y celdas de evidencia.

## Contrato lógico preliminar (no implementado)

~~~json
{
  "regime": "definitivo_importacion|temporal_immex|deposito_fiscal|transito|recinto|unknown",
  "operation_date": "YYYY-MM-DD",
  "steps": [
    {
      "title": "consultar aviso",
      "instrument_url": "https://...",
      "rule_ref": null,
      "status": "official_reference|provisional|not_verified",
      "applicability": "not_determined"
    }
  ],
  "transactional": false
}
~~~

Metadatos requeridos: identificador estable, fuente original/URL, fecha de consulta y publicación, versión, SHA256 cuando existan bytes, derechos de reutilización, estado verificado/refencia/declarado, fecha efectiva cuando corresponda. No reemplazar unknown con valores inferidos.

## Criterios de aceptación comprobables

- [ ] Regímenes de los dos tipos temporales sin confundir IMMEX con retorno simple.
- [ ] Fuente MOA en actualización presenta warning y remite a Ley/RGCE actual.
- [ ] Ningún checklist envía expedientes o pide RFC/contraseñas.
- [ ] Vínculos/reglas fechados por operación, no por fecha de scraping.
- [ ] Accesibilidad y flujo de navegación con disclaimer de que no verifica obligaciones.
- [ ] Especificar fallback, seguridad, accesibilidad, idiomas, privacidad, rollback, presupuesto de recursos y compatibilidad antes de PR de código.
- [ ] No reactivar /v1 ni modificar releases LIGIE/NICO sin ADR.

## Plan de implementación

1. Ampliación del índice MOA existente con taxonomía
2. Grafo de fuentes de régimen y documento
3. Interfaz de guía/autoestudio y tests de vigencia
4. Mantenimiento editorial del año siguiente

## Preguntas abiertas y verificaciones pendientes

Revisión normativa de supuestos y fechas; portal ANAM del MOA aún puede conservar material anterior al marco actual.

## Trazabilidad a NotebookLM y fuentes oficiales

- Notebook: entrada 3 arancel-mx MOA, 9 DOF, 11–36 leyes: LAdua, LCPAF, LNCM, LGOAAC, LFSA, LFSV, LGS; entrada 42 Ruta Logística.
- https://www.anam.gob.mx/manual-de-operacion-aduanera-moa/
- https://www.anam.gob.mx/moa/
- https://www.sat.gob.mx/minisitio/NormatividadRMFyRGCE/normatividad_rmf_rgce2026.html

## Fuera de alcance del PR

El PR crea esta especificación; no activa IA, transmisiones aduaneras, nuevos contenidos multimedia o cambios en producción. Implementación posterior mediante PRs separados con CI y revisión del propietario.
