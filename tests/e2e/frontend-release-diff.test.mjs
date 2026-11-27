import assert from 'node:assert/strict';
import test from 'node:test';

import { loadReleaseDiff } from '../../frontend/src/release-diff.js';

const from = '2026.08.15';
const to = '2026.11.20';
const path = `diffs/${from}--${to}.json`;
const change = { code: '01012101', level: 'fraccion8', event: 'igi_changed', old_value: '0', new_value: null };

function fixture({ changes = [change], changesInIndex = changes.length, latest = path, verified = true, reportTo = to } = {}) {
  const index = {
    policy_version: 'release-diff-pages-v1',
    to,
    latest,
    diffs: [{ from, to, path: latest, comparison_status: 'verified_snapshots', changes: changesInIndex }],
  };
  const report = {
    policy_version: 'release-diff-v1',
    comparison_status: 'verified_snapshots',
    from: { dataset_version: from, release_verified: true },
    to: { dataset_version: reportTo, release_verified: verified },
    counts: { changes: changes.length },
    changes,
    auxiliary: { nom: { status: 'not_compared', changes: [] }, national_notes: { status: 'compared', changes: [] } },
  };
  return { index, report };
}

function fixtures(index, report) {
  const urls = [];
  const fetchImpl = async (url) => {
    urls.push(url);
    return Response.json(url.endsWith('/index.json') ? index : report);
  };
  return { fetchImpl, urls };
}

test('loads the published pair and preserves a numeric zero and a missing value', async () => {
  const { index, report } = fixture();
  const { fetchImpl, urls } = fixtures(index, report);
  assert.deepEqual(await loadReleaseDiff('/data/v1', { fetchImpl }), { kind: 'ready', from, to, path, report });
  assert.deepEqual(urls, ['/data/v1/diffs/index.json', `/data/v1/${path}`]);
});

test('distinguishes a verified empty comparison from an unavailable comparison', async () => {
  const { index, report } = fixture({ changes: [] });
  const empty = await loadReleaseDiff('/data/v1', fixtures(index, report));
  assert.equal(empty.kind, 'ready');
  assert.deepEqual(empty.report.changes, []);

  const unavailable = { ...index, latest: null, diffs: [], reason: 'previous release unavailable' };
  assert.deepEqual(await loadReleaseDiff('/data/v1', fixtures(unavailable)), { kind: 'unavailable' });
  assert.deepEqual(await loadReleaseDiff('/data/v1', { fetchImpl: async () => new Response(null, { status: 404 }) }), { kind: 'unavailable' });
});

test('rejects external paths before issuing a detail request', async () => {
  const { index, report } = fixture({ latest: 'https://example.invalid/data.json' });
  const { fetchImpl, urls } = fixtures(index, report);
  await assert.rejects(loadReleaseDiff('/data/v1', { fetchImpl }));
  assert.deepEqual(urls, ['/data/v1/diffs/index.json']);
});

test('rejects inconsistent release identities, unverified snapshots and inconsistent counts', async () => {
  for (const overrides of [{ reportTo: '2026.11.19' }, { verified: false }, { changesInIndex: 99 }]) {
    const { index, report } = fixture(overrides);
    await assert.rejects(loadReleaseDiff('/data/v1', fixtures(index, report)));
  }
});

test('distinguishes an unpublished index from a failed request', async () => {
  await assert.rejects(loadReleaseDiff('/data/v1', { fetchImpl: async () => new Response(null, { status: 503 }) }), /503/);
});
