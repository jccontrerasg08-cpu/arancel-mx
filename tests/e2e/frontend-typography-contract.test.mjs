import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import path from 'node:path';
import test from 'node:test';

const root = path.resolve(import.meta.dirname, '../..');
const read = (file) => readFile(path.join(root, file), 'utf8');

test('every heading uses the display face of the home page', async () => {
  const css = await read('frontend/src/styles.css');
  for (const tag of ['h1', 'h2', 'h3']) {
    assert.match(css, new RegExp(`^${tag} \\{[^}]*font-family:var\\(--display\\)`, 'm'), `${tag} must use --display`);
  }
  assert.match(css, /--display:'Fredoka'/);
});

test('the trade desk shares the site typefaces instead of a serif', async () => {
  const [css, html] = await Promise.all([read('src/arancel_mx/api/static/site/assets/trade-desk.css'), read('src/arancel_mx/api/static/site/trade.html')]);
  assert.doesNotMatch(css, /Instrument Serif|Georgia/);
  assert.doesNotMatch(html, /Instrument\+Serif/);
  assert.match(html, /family=Fredoka/);
});
