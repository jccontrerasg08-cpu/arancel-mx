import assert from 'node:assert/strict';
import test from 'node:test';

import { createStaticApi } from '../../frontend/src/static-api.js';

const RECORDS = [
  { code: '85', level: 'hs2' },
  { code: '8517', level: 'hs4', parent_code: '85' },
  { code: '85171301', level: 'fraccion8', parent_code: '851713' },
  { code: '8517130100', level: 'nico10', parent_code: '85171301' },
  { code: '851713', level: 'hs6', parent_code: '8517' },
  { code: '85171491', level: 'fraccion8', parent_code: '851714' },
  { code: '85171999', level: 'fraccion8', parent_code: '851719' },
];
const REGULATIONS = {
  annex: { status: 'available' },
  sources: { annex: { source_url: 'https://example.test/anexo.pdf', sha256: 'a'.repeat(64) } },
  requirements: [
    { fraction8: '85171301', numeral: 1, nom: 'NOM-208-SCFI-2016', scope: 'Únicamente: radiocomunicación', annex_page: 600, source_document_id: 'annex' },
    { fraction8: '85171301', numeral: 3, nom: 'NOM-024-SCFI-2013', scope: null, annex_page: 700, source_document_id: 'annex' },
    { fraction8: '85171491', numeral: 1, nom: 'NOM-999-X-2020', scope: null, annex_page: 601, source_document_id: 'annex' },
  ],
};

const api = (regulations) => createStaticApi({
  base: 'https://data.test',
  fetchImpl: async (url) => {
    if (url.endsWith('/records/85.json')) return { ok: true, status: 200, json: async () => RECORDS };
    if (url.endsWith('/regulations/85.json') && regulations) return { ok: true, status: 200, json: async () => regulations };
    return { ok: false, status: 404, json: async () => null };
  },
});

test('a fraction gets only its own NOM, with scope and the document they come from', async () => {
  const result = await api(REGULATIONS).regulations('8517.13.01');
  assert.deepEqual(result.requirements.map((item) => item.nom), ['NOM-208-SCFI-2016', 'NOM-024-SCFI-2013']);
  assert.equal(result.requirements[0].scope, 'Únicamente: radiocomunicación');
  assert.deepEqual(Object.keys(result.sources), ['annex']);
});

test('a NICO shows the NOM of its fraction and a heading shows none', async () => {
  const client = api(REGULATIONS);
  assert.equal((await client.regulations('8517130100')).requirements.length, 2);
  assert.deepEqual((await client.regulations('851713')).requirements, []);
});

test('a release without the regulations file yields no requirements instead of failing', async () => {
  const result = await api(null).regulations('85171301');
  assert.deepEqual(result, { requirements: [], sources: {}, annex: null });
});

test('the derived resource is reachable through request() and does not alter the ficha', async () => {
  const client = api(REGULATIONS);
  assert.equal((await client.request('/v1/codes/85171301/regulations')).requirements.length, 2);
  assert.deepEqual(Object.keys(await client.ficha('85171301')).sort(), ['children', 'formatted_code', 'hierarchy', 'record', 'section']);
});

test('the annex status of the release travels with the answer, even for a fraction with no NOM', async () => {
  const none = await api(REGULATIONS).regulations('85171999');
  assert.deepEqual(none.requirements, []);
  assert.equal(none.annex.status, 'available');
  const unavailable = await api({ annex: { status: 'unavailable' }, sources: {}, requirements: [] }).regulations('85171301');
  assert.deepEqual(unavailable, { requirements: [], sources: {}, annex: { status: 'unavailable' } });
});
