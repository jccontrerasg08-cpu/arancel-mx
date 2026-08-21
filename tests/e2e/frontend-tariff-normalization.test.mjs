import assert from 'node:assert/strict';
import test from 'node:test';

test('normalizes structured API rates into safe presentation text', async () => {
  const { displayRate } = await import('../../frontend/src/tariff.js');

  assert.equal(displayRate({ text: 'Ex.', kind: 'exento', value: 0 }), 'Ex.');
  assert.equal(displayRate({ text: null, kind: 'ad_valorem', value: 15 }), '15%');
  assert.equal(displayRate('20%'), '20%');
  assert.equal(displayRate(null), '—');
});

test('selects the exact verified candidate before prefix matches', async () => {
  const { selectPrimarySearchResults } = await import('../../frontend/src/tariff.js');
  const results = [
    { record: { code: '85171301' } },
    { record: { code: '8517130100' } },
  ];

  assert.deepEqual(selectPrimarySearchResults(results, '85.17.13.01'), [results[0]]);
});
