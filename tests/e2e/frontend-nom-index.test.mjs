import assert from 'node:assert/strict';
import test from 'node:test';

import { createStaticApi } from '../../frontend/src/static-api.js';

test('looks up a NOM in the release-specific reverse index', async () => {
  const calls = [];
  const api = createStaticApi({ base: '/data/v1', fetchImpl: async (url) => {
    calls.push(url);
    return Response.json({
      dataset_tag: 'data-2026.11.20',
      annex: { status: 'available' },
      entries: [{ nom: 'NOM-024-SCFI-2013', fractions: ['85171301'] }],
    });
  } });
  assert.deepEqual(await api.nomLookup(' nom-024-scfi-2013 '), {
    dataset_tag: 'data-2026.11.20',
    annex: { status: 'available' },
    fractions: ['85171301'],
  });
  assert.deepEqual(calls, ['/data/v1/nom-index.json']);
  assert.deepEqual((await api.nomLookup('NOM-999-TEST')).fractions, []);
});

test('preserves absent index status and rejects malformed identifiers', async () => {
  const api = createStaticApi({ fetchImpl: async () => new Response(null, { status: 404 }) });
  assert.deepEqual(await api.nomLookup('NOM-024-SCFI-2013'), {
    annex: { status: 'not_included' }, fractions: [], dataset_tag: null,
  });
  await assert.rejects(api.nomLookup('../NOM-024'), /invalid NOM/);
});
