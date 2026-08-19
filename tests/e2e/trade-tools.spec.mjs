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
  });

  assert.equal(checklist.status, 'incomplete');
  assert.deepEqual(checklist.missing, ['Factura o documento equivalente', 'Evidencia de origen']);
  assert.match(checklist.disclaimer, /no genera ni transmite/i);
});

test('keeps an official source record for every orientation module', () => {
  assert.deepEqual(
    Object.keys(TRADE_SOURCES).sort(),
    ['classification', 'costs', 'pedimento', 'rrna', 'tmec'],
  );
  for (const source of Object.values(TRADE_SOURCES)) {
    assert.match(source.url, /^https:\/\//);
    assert.ok(source.title);
    assert.ok(source.updated);
  }
});
