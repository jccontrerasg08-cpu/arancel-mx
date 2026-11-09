import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import test from 'node:test';

const root = path.resolve(import.meta.dirname, '../..');
const read = (file) => readFile(path.join(root, file), 'utf8');

test('the static page ships the canonical and share metadata that each route then updates', async () => {
  const [html, app] = await Promise.all([read('frontend/index.html'), read('frontend/src/page-meta.js')]);
  assert.match(html, /<link rel="canonical" href="https:\/\/arancel-mx\.vercel\.app\/"/);
  assert.match(html, /<meta property="og:title"/);
  assert.match(html, /<meta property="og:description"/);
  assert.match(html, /<meta property="og:url"/);
  for (const selector of ['link[rel="canonical"]', 'meta[property="og:title"]', 'meta[property="og:description"]', 'meta[property="og:url"]']) {
    assert.ok(app.includes(selector), `page-meta keeps ${selector} in step with the route`);
  }
});

test('the secondary routes are written in both languages instead of English only', async () => {
  const pages = await read('frontend/src/pages.jsx');
  const copy = pages.slice(pages.indexOf('const MARKETING_COPY'), pages.indexOf('function MarketingPage'));
  for (const path of ['/features', '/releases', '/release-analytics', '/community']) {
    const line = copy.split('\n').find((entry) => entry.includes(`'${path}'`));
    assert.ok(line, `${path} has copy`);
    assert.equal((line.match(/\['[^']*', '[^']*'\]/g) || []).length >= 3, true, `${path} carries Spanish and English`);
  }
  assert.doesNotMatch(pages, /<MarketingPage eyebrow=/);
});

test('the trade desk uses the same header, logo and palette as the explorer', async () => {
  const [html, css] = await Promise.all([read('src/arancel_mx/api/static/site/trade.html'), read('src/arancel_mx/api/static/site/assets/trade-desk.css')]);
  assert.match(html, /class="trade-brand"[^>]*><img src="\/assets\/arancel-mx-logo\.svg"/);
  assert.doesNotMatch(html, /trade-topline|trade-brand__seal/);
  assert.match(css, /--trade-teal: #008a5b;/);
  assert.match(css, /--trade-ink: #102a43;/);
});

test('a record has a section navigation whose targets all exist', async () => {
  const [pages, css] = await Promise.all([read('frontend/src/pages.jsx'), read('frontend/src/styles.css')]);
  for (const id of ['record-summary', 'record-hierarchy', 'record-provenance']) {
    assert.ok(pages.includes(`href="#${id}"`), `the navigation links to #${id}`);
    assert.ok(pages.includes(`id="${id}"`), `#${id} exists on the page`);
    assert.ok(css.includes(`#${id}`), `#${id} keeps room for the sticky header`);
  }
});

test('the Learn group opens with a start-here guide that every layer knows about', async () => {
  const [content, app, routes, locale, api, vercel] = await Promise.all(['frontend/src/content.js', 'frontend/src/App.jsx', 'frontend/src/routes.js', 'frontend/src/locale.jsx', 'src/arancel_mx/api/app.py', 'vercel.json'].map(read));
  assert.match(content, /id: 'learn', items: \['\/learn',/);
  assert.ok(content.includes("'/learn': {"), 'editorial copy exists in both languages');
  assert.ok(app.includes('path="/learn"'));
  assert.ok(routes.includes("path: '/learn'"));
  assert.ok(locale.includes("'/learn': 'Guía para empezar'") && locale.includes("'/learn': 'Start here'"));
  assert.ok(api.includes('"/learn",'));
  assert.ok(JSON.parse(vercel).rewrites.at(-1).source.includes('|learn|'));
});

test('the Learn guide explains the five code levels and cites official sources', async () => {
  const page = await read('frontend/src/learn-page.jsx');
  for (const level of ["'Capítulo'", "'Partida'", "'Subpartida'", "'Fracción arancelaria'", "'NICO'"]) assert.ok(page.includes(level), `${level} is explained`);
  assert.ok(page.includes('snice.gob.mx') && page.includes('diputados.gob.mx'), 'cites the SNICE page and the LIGIE text');
  assert.ok(page.includes('12 de diciembre de 2022') && page.includes('12 December 2022'), 'states the LIGIE entry into force');
});

test('a record names its fraction in the title and the shared description', async () => {
  const { describeRecord } = await import(pathToFileURL(path.join(root, 'frontend/src/page-meta.js')).href);
  const es = describeRecord({ code: '8517.13.01', description: 'Teléfonos inteligentes.', rates: 'IGI Ex. · IGE Ex.', language: 'es' });
  assert.equal(es.title, '8517.13.01 · Teléfonos inteligentes');
  assert.equal(es.summary, 'Ficha verificada 8517.13.01: Teléfonos inteligentes. IGI Ex. · IGE Ex.');
  assert.match(describeRecord({ code: '85', description: 'x', language: 'en' }).summary, /^Verified record 85: x\.$/);
  const long = describeRecord({ code: '8517', description: 'a'.repeat(300), rates: 'IGI 5% · IGE Ex.', language: 'es' });
  assert.ok(long.summary.length <= 160 && long.title.length <= 90);
  assert.equal(describeRecord({ code: '85', description: '', language: 'es' }).title, '85');
});

test('the trade desk carries canonical and share metadata like the other pages', async () => {
  const html = await read('src/arancel_mx/api/static/site/trade.html');
  assert.match(html, /<link rel="canonical" href="https:\/\/arancel-mx\.vercel\.app\/trade"/);
  assert.match(html, /<meta property="og:title" content="arancel-mx — Estimador de importación"/);
  assert.match(html, /<meta property="og:url" content="https:\/\/arancel-mx\.vercel\.app\/trade"/);
});

test('every public page has its own tab title and description, not the site default', async () => {
  const [pages, content, { PUBLIC_ROUTES }] = await Promise.all([
    read('frontend/src/pages.jsx'),
    read('frontend/src/content.js'),
    import(pathToFileURL(path.join(root, 'frontend/src/routes.js')).href),
  ]);
  const editorial = content.split('export const EDITORIAL_PAGES = {')[1].split('export const editorialPage')[0];
  const marketing = pages.split('const MARKETING_COPY = {')[1].split('};')[0];
  const exempt = new Set(['/', '/trade', '/app/record/:code', '/moa-guide']); // home has its own title, the desk is a static page, records build theirs
  for (const { path: route } of PUBLIC_ROUTES) {
    if (exempt.has(route)) continue;
    const covered = editorial.includes(`'${route}': {`) || marketing.includes(`'${route}': {`) || pages.includes(`'${route}': EXPLORER_META`);
    assert.ok(covered, `${route} has no page title`);
  }
  for (const phrase of ['Explora una referencia arancelaria sin perder su camino.', 'Explore a tariff reference without losing its path.']) {
    assert.equal(pages.split(phrase).length - 1, 2, `the explorer hero and its tab title say the same thing (${phrase})`);
  }
});
