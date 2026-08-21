import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import path from 'node:path';
import test from 'node:test';

const root = path.resolve(import.meta.dirname, '../..');

test('app routes every maintained page through the shared source manifest', async () => {
  const source = await readFile(path.join(root, 'frontend/src/App.jsx'), 'utf8');
  assert.match(source, /import\s+\{\s*PAGE_COMPONENTS\s*\}/);
  assert.match(source, /<Route/);
  assert.match(source, /Object\.entries\(PAGE_COMPONENTS\)/);
});
