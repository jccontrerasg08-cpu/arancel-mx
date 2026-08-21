import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import path from 'node:path';
import test from 'node:test';

const root = path.resolve(import.meta.dirname, '../..');

test('vite preview permits the sandbox proxy suffix without allowing arbitrary hosts', async () => {
  const source = await readFile(path.join(root, 'vite.config.js'), 'utf8');
  assert.match(source, /allowedHosts\s*:\s*\[\s*['"]\.manus\.computer['"]\s*\]/);
  assert.doesNotMatch(source, /allowedHosts\s*:\s*true/);
});
