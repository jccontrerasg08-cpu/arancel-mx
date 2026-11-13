import assert from 'node:assert/strict';
import test from 'node:test';

import {
  buildPedimentoChecklist,
  calculateCustomsValue,
  calculateImportEstimate,
  evaluateRrnaOrientation,
  evaluateTmecOrientation,
  TRADE_SOURCES,
} from '../../src/arancel_mx/api/static/site/assets/trade-tools.js';

test('builds an orientative customs value from commercial components', () => {
  const customsValue = calculateCustomsValue({
    incoterm: 'CIF',
    productValueMxn: 1000,
    freightMxn: 120,
    insuranceMxn: 30,
    incrementablesMxn: 50,
  });

  assert.equal(customsValue.customsValueMxn, 1200);
  assert.equal(customsValue.method, 'declared_components');
  assert.match(customsValue.disclaimer, /orientativ/i);
});

test('uses a declared direct customs value before commercial components', () => {
  const customsValue = calculateCustomsValue({
    directValueMxn: 1200,
    incoterm: 'CIF',
    productValueMxn: 1000,
    freightMxn: 120,
    insuranceMxn: 30,
    incrementablesMxn: 50,
  });

  assert.equal(customsValue.customsValueMxn, 1200);
  assert.equal(customsValue.method, 'direct_value');
  assert.deepEqual(customsValue.components, []);
});

test('calculates an itemized import estimate from a declared customs value', () => {
  const estimate = calculateImportEstimate({
    customsValueMxn: 1000,
    igiRatePercent: 10,
    dtaRatePercent: 0.8,
    ivaRatePercent: 16,
    iepsRatePercent: 0,
  });

  assert.deepEqual(estimate.items, [
    { key: 'customs_value', label: 'Valor en aduana declarado', amount: 1000 },
    { key: 'igi', label: 'IGI estimado', amount: 100 },
    { key: 'dta', label: 'DTA estimado', amount: 8 },
    { key: 'ieps', label: 'IEPS estimado', amount: 0 },
    { key: 'iva', label: 'IVA de importación estimado', amount: 177.28 },
  ]);
  assert.equal(estimate.totalContributions, 285.28);
  assert.equal(estimate.landedCost, 1285.28);
  assert.equal(estimate.status, 'orientation_only');
});

test('rejects a simulation when the declared customs value is not positive', () => {
  assert.throws(
    () => calculateImportEstimate({ customsValueMxn: 0 }),
    /valor en aduana/i,
  );
});

test('marks a T-MEC review as incomplete when traceable origin evidence is missing', () => {
  const result = evaluateTmecOrientation({
    tariffCode: '85171301',
    originCountry: 'MX',
    regionalValueContent: 75,
    requiredRegionalValueContent: 75,
    supplierDeclarations: false,
    billOfMaterials: false,
    tmecReferenceUrl: 'https://www.gob.mx/t-mec/acciones-y-programas/textos-finales-del-tratado-entre-mexico-estados-unidos-y-canada-t-mec-202730',
    tmecReferenceConsultedAt: '2026-08-20',
    tmecReferenceNote: 'Regla de origen declarada para revisión documental.',
  });

  assert.equal(result.status, 'evidence_required');
  assert.match(result.nextStep, /declaraciones de proveedor/i);
  assert.equal(result.preferentialRateConfirmed, false);
});

test('builds a non-transactional pedimento checklist from missing operation data', () => {
  const checklist = buildPedimentoChecklist({
    tariffCode: '85171301',
    regime: 'definitive_import',
    originCountry: 'CN',
    customsValueMxn: 1000,
    hasInvoice: false,
    hasTransportEvidence: true,
    hasOriginEvidence: false,
    rrnaReferenceUrl: 'https://www.snice.gob.mx/cs/avi/snice/drrnas.avisosypermisos.html',
    rrnaReferenceConsultedAt: '2026-08-20',
    rrnaReferenceNote: 'Revisión declarada de avisos y permisos.',
  });

  assert.equal(checklist.status, 'incomplete');
  assert.deepEqual(checklist.missing, [
    'Factura o documento equivalente',
    'Evidencia de origen',
    'Revisión documental de RRNA y programas aplicables',
  ]);
  assert.match(checklist.disclaimer, /no genera ni transmite/i);
});

test('keeps an official source record for every orientation module', () => {
  assert.deepEqual(
    Object.keys(TRADE_SOURCES).sort(),
    [
      'classification',
      'costs',
      'pedimento',
      'rrna',
      'tmec',
      'tmecOriginProcedures',
      'tmecOriginRules',
    ],
  );
  for (const source of Object.values(TRADE_SOURCES)) {
    assert.match(source.url, /^https:\/\//);
    assert.ok(source.title);
    assert.ok(source.updated);
  }
});

test('keeps declared VCR inputs traceable when the T-MEC threshold is not met', () => {
  const result = evaluateTmecOrientation({
    tariffCode: '85171301',
    originCountry: 'MX',
    regionalValueContent: 45,
    requiredRegionalValueContent: 75,
    supplierDeclarations: true,
    billOfMaterials: true,
    tmecReferenceUrl: 'https://www.gob.mx/t-mec/acciones-y-programas/textos-finales-del-tratado-entre-mexico-estados-unidos-y-canada-t-mec-202730',
    tmecReferenceConsultedAt: '2026-08-20',
    tmecReferenceNote: 'Regla de origen declarada para revisión documental.',
  });

  assert.equal(result.status, 'threshold_not_met');
  assert.equal(result.regionalValueContent, 45);
  assert.equal(result.requiredRegionalValueContent, 75);
  assert.equal(result.preferentialRateConfirmed, false);
});

test('keeps RRNA review as an explicit declared checklist requirement', () => {
  const checklist = buildPedimentoChecklist({
    tariffCode: '85171301',
    regime: 'definitive_import',
    originCountry: 'CN',
    customsValueMxn: 1000,
    hasInvoice: true,
    hasTransportEvidence: true,
    hasOriginEvidence: true,
    hasRrnaReview: false,
  });

  assert.equal(checklist.status, 'incomplete');
  assert.ok(checklist.missing.includes('Revisión documental de RRNA y programas aplicables'));
  assert.equal(checklist.checklist.at(-1).complete, false);
});


test('builds an evidence-bound RRNA matrix without confirming applicability', () => {
  const result = evaluateRrnaOrientation({
    tariffCode: '85171301',
    hasRrnaReview: true,
    rrnaReferenceUrl: 'https://www.snice.gob.mx/cs/avi/snice/drrnas.avisosypermisos.html',
    rrnaReferenceConsultedAt: '2026-08-22',
    rrnaReferenceNote: 'Se revisó el punto de entrada oficial y la medida específica sigue pendiente de contraste documental.',
  });

  assert.equal(result.status, 'evidence_review_required');
  assert.equal(result.applicabilityConfirmed, false);
  assert.deepEqual(result.matrix.map((row) => [row.key, row.complete]), [
    ['tariff_code', true],
    ['official_reference', true],
    ['consulted_at', true],
    ['measure_note', true],
    ['review_declared', true],
  ]);
  assert.match(result.disclaimer, /no confirma.*aplicabilidad/i);
});


test('keeps the RRNA matrix incomplete when the proposed tariff code is invalid', () => {
  const result = evaluateRrnaOrientation({
    tariffCode: 'not-a-code',
    hasRrnaReview: true,
    rrnaReferenceUrl: 'https://www.snice.gob.mx/cs/avi/snice/drrnas.avisosypermisos.html',
    rrnaReferenceConsultedAt: '2026-08-22',
    rrnaReferenceNote: 'Aviso revisado para contraste documental.',
  });

  assert.equal(result.status, 'evidence_required');
  assert.deepEqual(result.matrix[0], {
    key: 'tariff_code',
    label: 'Fracción propuesta',
    value: 'Formato inválido',
    complete: false,
  });
});


test('keeps a T-MEC review evidence-required without a declared specific official reference', () => {
  const result = evaluateTmecOrientation({
    tariffCode: '85171301',
    originCountry: 'MX',
    regionalValueContent: 75,
    requiredRegionalValueContent: 75,
    supplierDeclarations: true,
    billOfMaterials: true,
  });

  assert.equal(result.status, 'evidence_required');
  assert.match(result.nextStep, /referencia oficial específica/i);
  assert.equal(result.preferentialRateConfirmed, false);
});


test('rejects an external HTTPS URL presented as a T-MEC official reference', () => {
  const result = evaluateTmecOrientation({
    tariffCode: '85171301',
    originCountry: 'MX',
    regionalValueContent: 75,
    requiredRegionalValueContent: 75,
    supplierDeclarations: true,
    billOfMaterials: true,
    tmecReferenceUrl: 'https://example.com/tmec-rule',
    tmecReferenceConsultedAt: '2026-08-20',
    tmecReferenceNote: 'No debe aceptarse como fuente oficial.',
  });

  assert.equal(result.status, 'evidence_required');
  assert.match(result.nextStep, /referencia oficial específica/i);
});


test('rejects an external HTTPS URL presented as an RRNA official reference', () => {
  const checklist = buildPedimentoChecklist({
    tariffCode: '85171301',
    regime: 'definitive_import',
    originCountry: 'CN',
    customsValueMxn: 1000,
    hasInvoice: true,
    hasTransportEvidence: true,
    hasOriginEvidence: true,
    hasRrnaReview: true,
    rrnaReferenceUrl: 'https://example.com/rrna',
    rrnaReferenceConsultedAt: '2026-08-20',
    rrnaReferenceNote: 'No debe aceptarse como fuente oficial.',
  });

  assert.equal(checklist.status, 'incomplete');
  assert.ok(checklist.missing.includes('Referencia oficial específica de RRNA revisada'));
});


test('keeps the RRNA checklist incomplete without a declared specific official reference', () => {
  const checklist = buildPedimentoChecklist({
    tariffCode: '85171301',
    regime: 'definitive_import',
    originCountry: 'CN',
    customsValueMxn: 1000,
    hasInvoice: true,
    hasTransportEvidence: true,
    hasOriginEvidence: true,
    hasRrnaReview: true,
  });

  assert.equal(checklist.status, 'incomplete');
  assert.ok(checklist.missing.includes('Referencia oficial específica de RRNA revisada'));
});

// Paridad con la antigua calculadora-aranceles-mx: mismos vectores numéricos, ahora en el Trade Desk.
test('converts USD components at a declared exchange rate before building the customs value', () => {
  const customsValue = calculateCustomsValue({
    currency: 'USD',
    exchangeRate: 20,
    incoterm: 'CIF',
    productValueMxn: 10_000,
    incrementablesMxn: 1_000,
  });

  assert.equal(customsValue.customsValueMxn, 220_000);
  assert.equal(customsValue.currency, 'USD');
  assert.equal(customsValue.exchangeRate, 20);
});

test('reproduces the ad-valorem cascade with IVA over the full base from a USD capture', () => {
  const customsValue = calculateCustomsValue({
    currency: 'USD',
    exchangeRate: 20,
    productValueMxn: 10_000,
    incrementablesMxn: 1_000,
  });
  const estimate = calculateImportEstimate({
    customsValueMxn: customsValue.customsValueMxn,
    igiRatePercent: 10,
    dtaRatePercent: 0.8,
    ivaRatePercent: 16,
  });

  assert.equal(estimate.items.find((item) => item.key === 'igi').amount, 22_000);
  assert.equal(estimate.items.find((item) => item.key === 'dta').amount, 1_760);
  assert.equal(estimate.ivaBase, 243_760);
  assert.equal(estimate.items.find((item) => item.key === 'iva').amount, 39_001.6);
  assert.equal(estimate.totalContributions, 62_761.6);
});

test('includes a fixed DTA, a fixed IEPS and a compensatory quota in the IVA base', () => {
  const estimate = calculateImportEstimate({
    customsValueMxn: 1_000,
    igiRatePercent: 10,
    dtaMode: 'fixed',
    dtaFixedMxn: 10,
    dtaRatePercent: 5,
    iepsFixedMxn: 20,
    compensatoryQuotaMxn: 30,
    ivaRatePercent: 16,
  });

  assert.equal(estimate.items.find((item) => item.key === 'dta').amount, 10, 'fixed mode ignores the DTA rate');
  assert.equal(estimate.items.find((item) => item.key === 'compensatory_quota').amount, 30);
  assert.equal(estimate.ivaBase, 1_160);
  assert.equal(estimate.items.find((item) => item.key === 'iva').amount, 185.6);
  assert.equal(estimate.totalContributions, 345.6);
});

test('keeps the itemization unchanged when no compensatory quota is declared', () => {
  const estimate = calculateImportEstimate({ customsValueMxn: 1_000, igiRatePercent: 10 });
  assert.equal(estimate.items.some((item) => item.key === 'compensatory_quota'), false);
});

test('rejects invalid currency, missing exchange rate and negative additional amounts', () => {
  assert.throws(() => calculateCustomsValue({ currency: 'EUR', productValueMxn: 1 }), /MXN o USD/);
  assert.throws(() => calculateCustomsValue({ currency: 'USD', productValueMxn: 1 }), /tipo de cambio/i);
  assert.throws(() => calculateImportEstimate({ customsValueMxn: 100, compensatoryQuotaMxn: -1 }), /cuota compensatoria/i);
  assert.throws(() => calculateImportEstimate({ customsValueMxn: 100, dtaMode: 'fixed', dtaFixedMxn: -5 }), /DTA/);
});
