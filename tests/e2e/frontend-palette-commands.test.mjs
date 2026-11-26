import assert from 'node:assert/strict';
import test from 'node:test';

import { NAVIGATION } from '../../frontend/src/content.js';
import { findPaletteCommands } from '../../frontend/src/palette-commands.js';

const labels = Object.fromEntries(NAVIGATION.map(([label, href]) => [href, label]));
const paths = (query) => findPaletteCommands(query, labels).map(({ href }) => href);

test('suggests the four product modules when opened', () => {
  assert.deepEqual(paths('  '), ['/app', '/trade', '/data', '/moa']);
});

test('matches translated commands and official-resource aliases across locales', () => {
  assert.deepEqual(paths('  CÁLCULAdora  '), ['/trade']);
  assert.deepEqual(paths('import estimator'), ['/trade']);
  assert.deepEqual(paths('datos abiertos'), ['/data']);
  assert.deepEqual(paths('manual aduanera'), ['/moa']);
  assert.deepEqual(paths('dof'), ['/changes']);
  assert.deepEqual(paths('API'), ['/documentation']);
  assert.deepEqual(paths('glosario'), ['/glossary']);
  assert.ok(findPaletteCommands('calculadora', labels)[0].standalone);
});

test('does not route tariff codes, NOM identifiers, or unrelated keywords to commands', () => {
  for (const query of ['8517', '8517.13.01.00', 'NOM-024', 'teléfonos']) {
    assert.deepEqual(paths(query), []);
  }
  for (const { href } of findPaletteCommands('', labels)) assert.ok(labels[href]);
});
