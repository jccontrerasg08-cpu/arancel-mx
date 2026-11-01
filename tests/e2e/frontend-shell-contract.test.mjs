import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import path from 'node:path';
import test from 'node:test';

const root = path.resolve(import.meta.dirname, '../..');
const read = (file) => readFile(path.join(root, file), 'utf8');

test('the static page ships the canonical and share metadata that each route then updates', async () => {
  const [html, app] = await Promise.all([read('frontend/index.html'), read('frontend/src/App.jsx')]);
  assert.match(html, /<link rel="canonical" href="https:\/\/arancel-mx\.vercel\.app\/"/);
  assert.match(html, /<meta property="og:title"/);
  assert.match(html, /<meta property="og:description"/);
  assert.match(html, /<meta property="og:url"/);
  for (const selector of ['link[rel="canonical"]', 'meta[property="og:title"]', 'meta[property="og:description"]', 'meta[property="og:url"]']) {
    assert.ok(app.includes(selector), `RoutedPage keeps ${selector} in step with the route`);
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
