const SOURCE_DATE = '2026-08-19';

export const TRADE_SOURCES = Object.freeze({
  classification: Object.freeze({
    title: 'LIGIE, NICO y consulta de clasificación — SNICE/SAT',
    url: 'https://www.snice.gob.mx/cs/avi/snice/ligie.info22.html',
    updated: SOURCE_DATE,
  }),
  costs: Object.freeze({
    title: 'Reglas Generales de Comercio Exterior 2026 — SAT',
    url: 'https://www.sat.gob.mx/minisitio/NormatividadRMFyRGCE/documentos2026/rgce/rgce/ReglasGeneralesComercioExteriorpara2026.pdf',
    updated: SOURCE_DATE,
  }),
  pedimento: Object.freeze({
    title: 'Anexo 22 de las RGCE 2026 — SAT',
    url: 'https://www.sat.gob.mx/minisitio/NormatividadRMFyRGCE/documentos2026/rgce/anexos/Anexo22delasRGCEpara2026.pdf',
    updated: SOURCE_DATE,
  }),
  rrna: Object.freeze({
    title: 'Avisos y permisos — SNICE',
    url: 'https://www.snice.gob.mx/cs/avi/snice/drrnas.avisosypermisos.html',
    updated: SOURCE_DATE,
  }),
  tmec: Object.freeze({
    title: 'Textos finales del T-MEC — Secretaría de Economía',
    url: 'https://www.gob.mx/t-mec/acciones-y-programas/textos-finales-del-tratado-entre-mexico-estados-unidos-y-canada-t-mec-202730',
    updated: SOURCE_DATE,
  }),
});

const ORIENTATION_DISCLAIMER =
  'Resultado orientativo: no determina contribuciones, origen, clasificación, cumplimiento ni genera o transmite un pedimento.';

function numberOrZero(value, label) {
  if (value === undefined || value === null || value === '') return 0;
  const numeric = Number(value);
  if (!Number.isFinite(numeric) || numeric < 0) {
    throw new Error(`${label} debe ser un número igual o mayor que cero.`);
  }
  return numeric;
}

function positiveNumber(value, label) {
  const numeric = numberOrZero(value, label);
  if (numeric <= 0) throw new Error(`${label} debe ser mayor que cero.`);
  return numeric;
}

function roundCurrency(value) {
  return Math.round((value + Number.EPSILON) * 100) / 100;
}

function percentOf(base, rate) {
  return roundCurrency((base * rate) / 100);
}

export function calculateCustomsValue(input) {
  const allowedIncoterms = new Set(['EXW', 'FCA', 'FOB', 'CFR', 'CIF', 'CPT', 'CIP', 'DAP', 'DPU', 'DDP', 'OTHER']);
  const incoterm = String(input.incoterm || 'OTHER').toUpperCase();
  if (!allowedIncoterms.has(incoterm)) {
    throw new Error('El Incoterm debe seleccionarse de la lista disponible.');
  }

  const productValue = positiveNumber(input.productValueMxn, 'El precio de la mercancía');
  const freight = numberOrZero(input.freightMxn, 'El flete declarado');
  const insurance = numberOrZero(input.insuranceMxn, 'El seguro declarado');
  const incrementables = numberOrZero(input.incrementablesMxn, 'Los incrementables declarados');

  return Object.freeze({
    method: 'declared_components',
    incoterm,
    customsValueMxn: roundCurrency(productValue + freight + insurance + incrementables),
    components: Object.freeze([
      Object.freeze({ key: 'product', label: 'Precio de mercancía declarado', amount: productValue }),
      Object.freeze({ key: 'freight', label: 'Flete declarado', amount: freight }),
      Object.freeze({ key: 'insurance', label: 'Seguro declarado', amount: insurance }),
      Object.freeze({ key: 'incrementables', label: 'Otros incrementables declarados', amount: incrementables }),
    ]),
    disclaimer:
      'Base orientativa construida con componentes declarados. El Incoterm no confirma qué conceptos son incrementables, incluidos o decrementables para una operación concreta.',
    source: TRADE_SOURCES.costs,
  });
}

export function calculateImportEstimate(input) {
  const customsValue = positiveNumber(input.customsValueMxn, 'El valor en aduana');
  const igiRate = numberOrZero(input.igiRatePercent, 'La tasa IGI');
  const dtaRate = numberOrZero(input.dtaRatePercent, 'La tasa DTA');
  const iepsRate = numberOrZero(input.iepsRatePercent, 'La tasa IEPS');
  const ivaRate = numberOrZero(input.ivaRatePercent ?? 16, 'La tasa IVA');

  const igi = percentOf(customsValue, igiRate);
  const dta = percentOf(customsValue, dtaRate);
  const ieps = percentOf(customsValue, iepsRate);
  const ivaBase = roundCurrency(customsValue + igi + dta + ieps);
  const iva = percentOf(ivaBase, ivaRate);
  const totalContributions = roundCurrency(igi + dta + ieps + iva);

  return Object.freeze({
    status: 'orientation_only',
    items: Object.freeze([
      Object.freeze({ key: 'customs_value', label: 'Valor en aduana declarado', amount: customsValue }),
      Object.freeze({ key: 'igi', label: 'IGI estimado', amount: igi }),
      Object.freeze({ key: 'dta', label: 'DTA estimado', amount: dta }),
      Object.freeze({ key: 'ieps', label: 'IEPS estimado', amount: ieps }),
      Object.freeze({ key: 'iva', label: 'IVA de importación estimado', amount: iva }),
    ]),
    ivaBase,
    totalContributions,
    landedCost: roundCurrency(customsValue + totalContributions),
    disclaimer: ORIENTATION_DISCLAIMER,
    sources: Object.freeze([TRADE_SOURCES.costs, TRADE_SOURCES.classification]),
  });
}

export function evaluateTmecOrientation(input) {
  const hasSupplierDeclarations = input.supplierDeclarations === true;
  const hasBillOfMaterials = input.billOfMaterials === true;
  const regionalValueContent = numberOrZero(
    input.regionalValueContent,
    'El contenido regional declarado',
  );
  const requiredRegionalValueContent = numberOrZero(
    input.requiredRegionalValueContent,
    'El contenido regional requerido',
  );

  if (!input.tariffCode || !input.originCountry) {
    return Object.freeze({
      status: 'evidence_required',
      preferentialRateConfirmed: false,
      regionalValueContent,
      requiredRegionalValueContent,
      nextStep: 'Indica la fracción propuesta y el país de origen antes de revisar la evidencia.',
      disclaimer: ORIENTATION_DISCLAIMER,
      source: TRADE_SOURCES.tmec,
    });
  }

  if (!hasSupplierDeclarations || !hasBillOfMaterials) {
    return Object.freeze({
      status: 'evidence_required',
      preferentialRateConfirmed: false,
      regionalValueContent,
      requiredRegionalValueContent,
      nextStep:
        'Integra declaraciones de proveedor y la lista de materiales antes de evaluar una preferencia T-MEC.',
      disclaimer: ORIENTATION_DISCLAIMER,
      source: TRADE_SOURCES.tmec,
    });
  }

  if (regionalValueContent < requiredRegionalValueContent) {
    return Object.freeze({
      status: 'threshold_not_met',
      preferentialRateConfirmed: false,
      regionalValueContent,
      requiredRegionalValueContent,
      nextStep:
        'El VCR declarado no alcanza el umbral indicado. Revisa la regla específica, el método y la evidencia de costos.',
      disclaimer: ORIENTATION_DISCLAIMER,
      source: TRADE_SOURCES.tmec,
    });
  }

  return Object.freeze({
    status: 'evidence_review_required',
    preferentialRateConfirmed: false,
    regionalValueContent,
    requiredRegionalValueContent,
    nextStep:
      'La evidencia declarada permite una revisión documental inicial; confirma la regla específica de origen y la certificación con la fuente oficial.',
    disclaimer: ORIENTATION_DISCLAIMER,
    source: TRADE_SOURCES.tmec,
  });
}

export function buildPedimentoChecklist(input) {
  const missing = [];
  if (!input.tariffCode) missing.push('Fracción arancelaria propuesta');
  if (!input.regime) missing.push('Régimen aduanero');
  if (!input.originCountry) missing.push('País de origen');
  if (!Number.isFinite(Number(input.customsValueMxn)) || Number(input.customsValueMxn) <= 0) {
    missing.push('Valor en aduana declarado');
  }
  if (input.hasInvoice !== true) missing.push('Factura o documento equivalente');
  if (input.hasTransportEvidence !== true) missing.push('Evidencia de transporte');
  if (input.hasOriginEvidence !== true) missing.push('Evidencia de origen');
  if (input.hasRrnaReview !== true) missing.push('Revisión documental de RRNA y programas aplicables');

  return Object.freeze({
    status: missing.length === 0 ? 'review_required' : 'incomplete',
    missing: Object.freeze(missing),
    checklist: Object.freeze([
      Object.freeze({ label: 'Datos de operación', complete: Boolean(input.tariffCode && input.regime) }),
      Object.freeze({ label: 'Valor y documentos comerciales', complete: input.hasInvoice === true }),
      Object.freeze({ label: 'Transporte y seguro', complete: input.hasTransportEvidence === true }),
      Object.freeze({ label: 'Origen y preferencia, si se invoca', complete: input.hasOriginEvidence === true }),
      Object.freeze({ label: 'RRNA y programas aplicables', complete: input.hasRrnaReview === true }),
    ]),
    disclaimer:
      'Checklist informativa: no genera ni transmite un pedimento, no valida el despacho y no sustituye la revisión del agente, agencia o autoridad aduanal.',
    sources: Object.freeze([TRADE_SOURCES.pedimento, TRADE_SOURCES.rrna]),
  });
}

export { ORIENTATION_DISCLAIMER };
