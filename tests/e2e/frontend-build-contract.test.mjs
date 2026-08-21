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

test('glossary recovery selects the available generated bundle instead of a stale hash', async () => {
  const recoveryScript = await readFile(path.join(root, 'scripts/recover-glossary-from-bundle.mjs'), 'utf8');
  assert.match(recoveryScript, /readdir/);
  assert.match(recoveryScript, /index-\[A-Za-z0-9_-\]\+\\\.js/);
  assert.doesNotMatch(recoveryScript, /index-ad6fbc25b68e\.js/);
});

test('static-site sync removes superseded generated CSS bundles', async () => {
  const source = await readFile(path.join(root, 'scripts/sync-frontend-static.mjs'), 'utf8');
  assert.match(source, /\(\?:js\|css\)/);
});

test('static-site sync script preserves the independently maintained trade desk', async () => {
  const syncScript = path.join(root, 'scripts/sync-frontend-static.mjs');
  assert.equal(existsSync(syncScript), true);

  const source = await readFile(syncScript, 'utf8');
  assert.match(source, /trade\.html/);
  assert.match(source, /src\/arancel_mx\/api\/static\/site/);
});
