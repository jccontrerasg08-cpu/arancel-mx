import assert from 'node:assert/strict';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import test from 'node:test';

const root = path.resolve(import.meta.dirname, '../..');

test('computes figures per level, chapter and section from the search index', async () => {
  const { computeStats } = await import(pathToFileURL(path.join(root, 'frontend/src/data-stats.js')).href);
  const stats = computeStats({
    sections: [{ roman: 'I', name: 'Animales', chapter_from: '01', chapter_to: '02' }, { roman: 'II', name: 'Vegetales', chapter_from: '03', chapter_to: '03' }],
    chapters: [{ code: '01', description: 'Animales vivos' }, { code: '02', description: 'Carne' }, { code: '03', description: 'Pescado' }],
    entries: [['01', 'a'], ['0101', 'a'], ['01012101', 'a'], ['0101210100', 'a'], ['0101210101', 'a'], ['01012102', 'a'], ['0201', 'a'], ['02011001', 'a'], ['0301', 'a']],
  });

  assert.deepEqual(stats.levels, { 2: 1, 4: 3, 6: 0, 8: 3, 10: 2 });
  assert.equal(stats.topChapters[0].code, '01');
  assert.equal(stats.topChapters[0].fractions, 2);
  assert.deepEqual(stats.emptyChapters, ['03']);
  assert.deepEqual(stats.busiestHeading, { code: '0101', count: 2 });
  assert.deepEqual(stats.mostNico, { code: '01012101', count: 2 });
  assert.equal(stats.averageNico, 2 / 3);
  assert.equal(stats.sectionRows[0].fractions, 3);
  assert.equal(stats.widestSection.roman, 'I');
});