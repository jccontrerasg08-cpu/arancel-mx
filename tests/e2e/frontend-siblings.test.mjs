import assert from 'node:assert/strict';
import test from 'node:test';

import { createStaticApi } from '../../frontend/src/static-api.js';

const RECORDS = [
  { code: '85', level: 'hs2' },
  { code: '8517', level: 'hs4', parent_code: '85' },
  { code: '851713', level: 'hs6', parent_code: '8517' },
  { code: '851714', level: 'hs6', parent_code: '8517' },
  { code: '85171301', level: 'fraccion8', parent_code: '851713', igi: 'Ex.' },
  { code: '8517130100', level: 'nico10', parent_code: '85171301' },
  { code: '85171491', level: 'fraccion8', parent_code: '851714', igi: 'Ex.' },
  { code: '85171101', level: 'fraccion8', parent_code: '851711', igi: '15' },
  { code: '85180101', level: 'fraccion8', parent_code: '851801', igi: '10' },
];

const api = createStaticApi({
  base: 'https://data.test',
  fetchImpl: async (url) =>
    url.endsWith('/records/85.json')
      ? { ok: true, status: 200, json: async () => RECORDS }
      : { ok: false, status: 404, json: async () => null },
});

test('siblings are the other fractions of the same heading, never NICO or other headings', async () => {
  const siblings = await api.siblings('8517.13.01');
  assert.deepEqual(siblings.map((item) => item.code).sort(), ['85171101', '85171491']);
  assert.ok(siblings.every((item) => item.level === 'fraccion8'));
});

test('only a fraction has siblings, and the derived resource does not alter the /v1 ficha', async () => {
  assert.deepEqual(await api.siblings('851713'), []);
  assert.deepEqual(await api.siblings('8517130100'), []);
  assert.deepEqual((await api.request('/v1/codes/85171301/siblings')).length, 2);
  const ficha = await api.ficha('85171301');
  assert.deepEqual(Object.keys(ficha).sort(), ['children', 'formatted_code', 'hierarchy', 'record', 'section']);
});
