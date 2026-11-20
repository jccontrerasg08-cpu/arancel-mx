import assert from 'node:assert/strict';
import test from 'node:test';
import { FLOORS, evaluate, summaryTable } from '../../scripts/lighthouse-check.mjs';

test('only accessibility, best practices and SEO can fail the run, never performance', () => {
  assert.deepEqual(Object.keys(FLOORS).sort(), ['accessibility', 'best-practices', 'seo']);
  assert.deepEqual(evaluate({ performance: 10, accessibility: 100, 'best-practices': 100, seo: 100 }), []);
  assert.deepEqual(evaluate({ performance: 99, accessibility: 94, 'best-practices': 89, seo: 100 }), ['accessibility 94 < 95', 'best-practices 89 < 90']);
});

test('the summary table lists every page with its status', () => {
  const table = summaryTable([
    { page: '/', scores: { performance: 90, accessibility: 100, 'best-practices': 96, seo: 100 }, problems: [] },
    { page: '/app', scores: { performance: 80, accessibility: 90, 'best-practices': 96, seo: 100 }, problems: ['accessibility 90 < 95'] },
  ]);
  assert.match(table, /\| \/ \| 90 \| 100 \| 96 \| 100 \| ok \|/);
  assert.match(table, /\| \/app \| 80 \| 90 \| 96 \| 100 \| below floor: accessibility 90 < 95 \|/);
});
