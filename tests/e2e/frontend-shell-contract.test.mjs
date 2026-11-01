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
  for (const path of ['/features', '/pricing', '/analytics', '/community']) {
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
