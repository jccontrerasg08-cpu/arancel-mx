import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import test from 'node:test';

const root = path.resolve(import.meta.dirname, '../..');
const site = path.join(root, 'src/arancel_mx/api/static/site');
const load = (file) => import(pathToFileURL(path.join(root, file)).href);
const attribute = (html, pattern) => html.match(pattern)?.[1];

test('every public page except the home, the desk, the aliases and the dynamic ones has its own HTML file', async () => {
  const { routePageRoutes, routePageFile } = await load('scripts/route-pages.mjs');
  const { PUBLIC_ROUTES, ROUTE_ALIASES } = await load('frontend/src/routes.js');
  const routes = routePageRoutes();

  const expected = PUBLIC_ROUTES.map(({ path: route }) => route).filter((route) => !route.includes(':') && route !== '/' && route !== '/trade' && !(route in ROUTE_ALIASES));
  assert.deepEqual(routes, expected);
  assert.ok(routes.length >= 16);
  for (const route of routes) assert.match(routePageFile(route), /^[a-z-]+\.html$/, `${route} maps to a flat file`);
  for (const alias of Object.keys(ROUTE_ALIASES)) assert.ok(!routes.includes(alias), `${alias} redirects, so it has no page`);
});

test('each route file is exactly what the build generates and carries its own head metadata', async () => {
  const { GENERATED_MARKER, renderRoutePage, routePageFile, routePageMeta, routePageRoutes } = await load('scripts/route-pages.mjs');
  const index = await readFile(path.join(site, 'index.html'), 'utf8');
  const titles = new Set();

  for (const route of routePageRoutes()) {
    const html = await readFile(path.join(site, routePageFile(route)), 'utf8');
    assert.equal(html, renderRoutePage(index, route), `${route}: run "npm run build:frontend" and commit the result`);
    const meta = routePageMeta(route);
    assert.equal(attribute(html, /<link rel="canonical" href="([^"]*)"/), `https://arancel-mx.vercel.app${route}`);
    assert.equal(attribute(html, /<meta property="og:url" content="([^"]*)"/), `https://arancel-mx.vercel.app${route}`);
    assert.ok(html.includes(GENERATED_MARKER));
    assert.ok(meta.title.startsWith('arancel-mx — ') && meta.description.length > 20, `${route} has a real title and description`);
    titles.add(meta.title);
  }
  assert.equal(titles.size, routePageRoutes().length, 'no two pages share a title');
});

test('a route file differs from index.html only in its head metadata, so the app boots the same way', async () => {
  const { renderRoutePage } = await load('scripts/route-pages.mjs');
  const index = await readFile(path.join(site, 'index.html'), 'utf8');
  const page = renderRoutePage(index, '/learn');
  const stripHead = (html) => html.replace(/<title>[^<]*<\/title>/, '').replace(/<meta (name="description"|property="og:(title|description|url)") content="[^"]*" \/>/g, '').replace(/<link rel="canonical" href="[^"]*" \/>/, '').replace(/<!-- generated route page[^>]*-->\r?\n/, '');
  assert.equal(stripHead(page), stripHead(index));
  assert.ok(page.includes('<div id="root"></div>') && page.includes('type="module"'));
});

test('rewriting fails loudly instead of publishing a page with the home metadata', async () => {
  const { renderRoutePage } = await load('scripts/route-pages.mjs');
  assert.throws(() => renderRoutePage('<!doctype html><html><head></head></html>', '/learn'), /exactly one <title>/);
  const index = await readFile(path.join(site, 'index.html'), 'utf8');
  assert.throws(() => renderRoutePage(index, '/pricing'), /has no title and description/);
});
