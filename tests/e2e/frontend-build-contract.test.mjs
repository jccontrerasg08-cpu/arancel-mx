import assert from 'node:assert/strict';
import { existsSync } from 'node:fs';
import { readdir } from 'node:fs/promises';
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

test('glossary data is deferred into its own published chunk', async () => {
  const app = await readFile(path.join(root, 'frontend/src/App.jsx'), 'utf8');
  const pages = await readFile(path.join(root, 'frontend/src/pages.jsx'), 'utf8');
  const assets = await readdir(path.join(root, 'website/assets'));
  const mainBundle = assets.find((name) => /^index-[A-Za-z0-9_-]+\.js$/.test(name));
  const glossaryBundle = assets.find((name) => /^glossary-page-[A-Za-z0-9_-]+\.js$/.test(name));

  assert.match(app, /lazy\(\(\) => import\('\.\/glossary-page\.jsx'\)\)/);
  assert.doesNotMatch(pages, /GLOSSARY_ENTRIES/);
  assert.ok(mainBundle);
  assert.ok(glossaryBundle);
  const glossarySource = await readFile(path.join(root, 'website/assets', glossaryBundle), 'utf8');
  assert.match(glossarySource, new RegExp(`from["']\\./${mainBundle}["']`));
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


test('static-site sync preserves the maintained hub interactions asset', async () => {
  const interactions = await readFile(path.join(root, 'website/assets/hub-interactions.js'), 'utf8');

  assert.match(interactions, /verified record/i);
});
