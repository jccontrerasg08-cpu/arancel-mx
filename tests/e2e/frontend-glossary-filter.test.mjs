import assert from 'node:assert/strict';
import test from 'node:test';

import { GLOSSARY_ENTRIES } from '../../frontend/src/glossary-data.js';
import { filterGlossary, glossaryLetter } from '../../frontend/src/glossary.js';

test('filters recovered glossary objects by category and normalized text', () => {
  const allAduana = filterGlossary(GLOSSARY_ENTRIES, 'aduana', 'Todas');
  assert.ok(allAduana.length >= 29);
  assert.ok(allAduana.some(({ term }) => term === 'Aduana'));

  const acronyms = filterGlossary(GLOSSARY_ENTRIES, '', 'Siglas');
  assert.ok(acronyms.length > 0);
  assert.ok(acronyms.every(({ category }) => category === 'Siglas'));
});

test('narrows entries by index letter and ignores accents', () => {
  assert.equal(glossaryLetter('Álamo'), 'A');
  assert.equal(glossaryLetter('3PL'), '#');
  const letterN = filterGlossary(GLOSSARY_ENTRIES, '', 'Todas', 'N');
  assert.ok(letterN.length > 0);
  assert.ok(letterN.every(({ term }) => glossaryLetter(term) === 'N'));
  assert.equal(filterGlossary(GLOSSARY_ENTRIES, '', 'Todas', '').length, GLOSSARY_ENTRIES.length);
});
