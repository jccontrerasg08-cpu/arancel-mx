import assert from 'node:assert/strict';
import test from 'node:test';

import {
  buildPedimentoChecklist,
  calculateCustomsValue,
  calculateImportEstimate,
  evaluateTmecOrientation,
  TRADE_SOURCES,
} from '../../website/assets/trade-tools.js';

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
