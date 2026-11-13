import assert from 'node:assert/strict';
import test from 'node:test';

import { chapterSummary } from '../../frontend/src/dof-changes.js';

test('chapterSummary counts fractions per chapter and orders the rates and the chapters', () => {
  const summary = chapterSummary({
    rate_rows: [
      ['72011001', '35', 'Ex.'],
      ['72011002', '35', 'Ex.'],
      ['72011003', '25', 'Ex.'],
      ['72011004', 'Ex.', 'Ex.'],
      ['62011001', '25', 'Ex.'],
      ['62011002', '25', 'Ex.'],
      ['62011003', '25', 'Ex.'],
      ['39011001', '7', 'Ex.'],
    ],
  });
  assert.deepEqual(summary.map((entry) => [entry.chapter, entry.count]), [['72', 4], ['62', 3], ['39', 1]]);
  assert.deepEqual(summary[0].rates, [['35%', 2], ['25%', 1], ['Ex.', 1]]);
  assert.deepEqual(summary[1].rates, [['25%', 3]]);
});

test('a publication without rate rows has no chapter summary', () => {
  assert.deepEqual(chapterSummary({ codes: ['01012101'] }), []);
  assert.deepEqual(chapterSummary({}), []);
});
