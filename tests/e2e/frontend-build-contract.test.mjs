import assert from 'node:assert/strict';
import { existsSync } from 'node:fs';
import { readFile } from 'node:fs/promises';
import path from 'node:path';
import test from 'node:test';

const root = path.resolve(import.meta.dirname, '../..');

async function readJson(relativePath) {
  return JSON.parse(await readFile(path.join(root, relativePath), 'utf8'));
}

test('frontend has a reproducible build that keeps trade desk assets separate', async () => {
  const packageManifest = await readJson('package.json');

  assert.equal(typeof packageManifest.scripts['build:frontend'], 'string');
  assert.ok(packageManifest.scripts['build:frontend'].includes('vite'));
  assert.equal(existsSync(path.join(root, 'vite.config.js')), true);
  assert.equal(existsSync(path.join(root, 'frontend/index.html')), true);
  assert.equal(existsSync(path.join(root, 'frontend/src/main.jsx')), true);
});

test('static-site sync script preserves the independently maintained trade desk', async () => {
  const syncScript = path.join(root, 'scripts/sync-frontend-static.mjs');
  assert.equal(existsSync(syncScript), true);

  const source = await readFile(syncScript, 'utf8');
  assert.match(source, /trade\.html/);
  assert.match(source, /src\/arancel_mx\/api\/static\/site/);
});
