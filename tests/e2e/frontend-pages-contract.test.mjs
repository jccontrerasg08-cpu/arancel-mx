import assert from 'node:assert/strict';
import { existsSync } from 'node:fs';
import { readFile } from 'node:fs/promises';
import path from 'node:path';
import test from 'node:test';

const root = path.resolve(import.meta.dirname, '../..');
const pagesPath = path.join(root, 'frontend/src/pages.jsx');

test('maintained frontend implements every public route as a source page component', async () => {
  assert.equal(existsSync(pagesPath), true, 'expected maintained page components');
  const source = await readFile(pagesPath, 'utf8');

  assert.match(source, /export\s+const\s+PAGE_COMPONENTS/);
  for (const routePath of [
    '/', '/app', '/app/record/:code', '/chapters', '/changes', '/moa', '/wiki',
    '/glossary', '/trade-context', '/documentation', '/trust', '/records', '/trade',
  ]) {
    assert.match(source, new RegExp(`['"]${routePath.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')}['"]`));
  }
});
