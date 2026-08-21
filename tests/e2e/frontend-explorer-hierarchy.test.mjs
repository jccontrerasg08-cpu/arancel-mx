import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import path from 'node:path';
import test from 'node:test';

const root = path.resolve(import.meta.dirname, '../..');

test('Explorer owns one dedicated heading instead of reusing the home hero', async () => {
  const source = await readFile(path.join(root, 'frontend/src/pages.jsx'), 'utf8');
  const explorer = source.slice(source.indexOf('export function ExplorerPage'), source.indexOf('export function RecordPage'));
  assert.doesNotMatch(explorer, /EDITORIAL_PAGES\['\/'\]/);
  assert.match(explorer, /VERIFIED RELEASE EXPLORER/);
  assert.match(explorer, /Explore a tariff reference without losing its path/);
});
