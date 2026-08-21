import assert from 'node:assert/strict';
import { existsSync } from 'node:fs';
import path from 'node:path';
import test from 'node:test';

const root = path.resolve(import.meta.dirname, '../..');
const glossaryPath = path.join(root, 'frontend/src/glossary-data.js');

test('reconstructed glossary retains the complete 189-entry source snapshot', async () => {
  assert.equal(existsSync(glossaryPath), true, 'expected recovered glossary source data');
  const { GLOSSARY_ENTRIES } = await import(`${glossaryPath}?cacheBust=${Date.now()}`);
  assert.equal(GLOSSARY_ENTRIES.length, 189);
  assert.deepEqual(GLOSSARY_ENTRIES[0], { category: 'Siglas', term: 'ANAM', definition: 'Agencia Nacional de Aduanas de México' });
  assert.equal(GLOSSARY_ENTRIES.at(-1).term, 'Zonas libres');
});
