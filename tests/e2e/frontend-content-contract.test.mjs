import assert from 'node:assert/strict';
import { existsSync } from 'node:fs';
import path from 'node:path';
import test from 'node:test';

const root = path.resolve(import.meta.dirname, '../..');
const contentPath = path.join(root, 'frontend/src/content.js');

test('editorial route content is maintained as declarative source data', async () => {
  assert.equal(existsSync(contentPath), true, 'expected declarative frontend content');
  const { EDITORIAL_PAGES } = await import(`${contentPath}?cacheBust=${Date.now()}`);

  for (const expected of ['/', '/moa', '/wiki', '/glossary', '/trade-context', '/documentation', '/trust', '/records', '/chapters', '/changes']) {
    assert.ok(EDITORIAL_PAGES[expected], `missing content for ${expected}`);
    assert.equal(typeof EDITORIAL_PAGES[expected].title, 'string');
    assert.ok(EDITORIAL_PAGES[expected].title.length > 0);
    assert.equal(typeof EDITORIAL_PAGES[expected].disclaimer, 'string');
  }
});
