import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import test from 'node:test';

const root = path.resolve(import.meta.dirname, '../..');
const load = (file) => import(pathToFileURL(path.join(root, file)).href);

test('the committed DOF changes file matches its sources', async () => {
  const { buildDofChanges } = await load('scripts/build-dof-changes.mjs');
  const committed = JSON.parse(await readFile(path.join(root, 'frontend/src/dof-changes.json'), 'utf8'));
  assert.deepEqual(committed, await buildDofChanges(root), 'run npm run build:dof-changes');
});

test('every publication has a DOF date, a document and a type, newest first', async () => {
  const committed = JSON.parse(await readFile(path.join(root, 'frontend/src/dof-changes.json'), 'utf8'));
  const dates = committed.instruments.map((item) => item.dof_date);
  assert.ok(committed.instruments.length >= 20);
  assert.deepEqual(dates, [...dates].sort().reverse());
  for (const item of committed.instruments) {
    assert.match(item.dof_date, /^\d{4}-\d{2}-\d{2}$/);
    assert.match(item.pdf, /^https:\/\//);
    assert.ok(item.section && item.title, item.id);
  }
});

test('helpers build the DOF edition link, rate labels and code lookups', async () => {
  const { dofEditionUrl, findByCode, groupOf, rateLabel } = await load('frontend/src/dof-changes.js');
  assert.equal(dofEditionUrl('2026-04-23'), 'https://www.dof.gob.mx/index.php?year=2026&month=04&day=23');
  assert.equal(rateLabel('Ex.'), 'Ex.');
  assert.equal(rateLabel('35'), '35%');
  assert.equal(rateLabel(null), '—');
  assert.equal(groupOf('law_reform'), 'law');
  assert.equal(groupOf('tariff_decree_modification'), 'tariff');
  assert.equal(groupOf('complementary'), 'agreement');
  const instruments = [
    { id: 'a', rate_rows: [['28272001', '35', 'Ex.'], ['28362001', '25', 'Ex.']], codes: null },
    { id: 'b', rate_rows: null, codes: ['28272001', '01022999'] },
    { id: 'c', rate_rows: null, codes: null },
  ];
  assert.deepEqual(findByCode(instruments, '2827').map((match) => match.instrument.id), ['a', 'b']);
  assert.deepEqual(findByCode(instruments, '28272001')[0].rows, [['28272001', '35', 'Ex.']]);
  assert.deepEqual(findByCode(instruments, '2'), []);
});