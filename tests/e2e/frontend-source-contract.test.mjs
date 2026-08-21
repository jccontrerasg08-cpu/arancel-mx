import assert from 'node:assert/strict';
import { existsSync } from 'node:fs';
import { readFile } from 'node:fs/promises';
import path from 'node:path';
import test from 'node:test';

const root = path.resolve(import.meta.dirname, '../..');
const routeManifestPath = path.join(root, 'frontend/src/routes.js');
const PUBLIC_SURFACES = [
  '/',
  '/app',
  '/product',
  '/app/record/:code',
  '/chapters',
  '/changes',
  '/moa',
  '/moa-guide',
  '/wiki',
  '/glossary',
  '/trade-context',
  '/documentation',
  '/trust',
  '/records',
  '/trade',
  '/features',
  '/pricing',
  '/analytics',
  '/community',
];

test('maintained frontend route manifest covers every public product surface', async () => {
  assert.equal(existsSync(routeManifestPath), true, 'expected a source route manifest');
  const { PUBLIC_ROUTES } = await import(`${routeManifestPath}?cacheBust=${Date.now()}`);
  const paths = PUBLIC_ROUTES.map(({ path: routePath }) => routePath);

  for (const expected of PUBLIC_SURFACES) {
    assert.ok(paths.includes(expected), `missing maintained route ${expected}`);
  }
});

test('maintained frontend uses source components instead of modifying the deployed bundle', async () => {
  const appSourcePath = path.join(root, 'frontend/src/App.jsx');
  assert.equal(existsSync(appSourcePath), true, 'expected a maintained App.jsx source file');
  const source = await readFile(appSourcePath, 'utf8');
  assert.match(source, /createBrowserRouter|BrowserRouter|Routes/, 'expected an explicit client routing implementation');
});
