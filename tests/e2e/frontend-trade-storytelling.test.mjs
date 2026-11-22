import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import test from 'node:test';

const root = path.resolve(import.meta.dirname, '../..');
const json = async (name) => JSON.parse(await readFile(path.join(root, 'frontend/src', name), 'utf8'));
const helpers = () => import(pathToFileURL(path.join(root, 'frontend/src/trade-balance.js')).href);

test('the state export table covers the 32 states, adds up and cites INEGI', async () => {
  const data = await json('state-exports.json');
  assert.equal(data.states.length, 32);
  assert.equal(new Set(data.states.map((state) => state.cve_ent)).size, 32);
  assert.deepEqual(data.states.map((state) => state.cve_ent).sort(), [...Array(32)].map((_, index) => String(index + 1).padStart(2, '0')));
  const sum = data.states.reduce((total, state) => total + state.millions, 0);
  assert.ok(Math.abs(sum - data.total_millions) <= 1, `states add up to ${sum}`);
  for (const state of data.states) {
    assert.ok(Math.abs((state.millions / data.total_millions) * 100 - state.share) <= 0.06, `${state.name} share`);
  }
  assert.deepEqual(data.states.map((state) => state.rank).sort((a, b) => a - b), [...Array(32)].map((_, index) => index + 1));
  const sorted = [...data.states].sort((a, b) => b.millions - a.millions);
  assert.ok(sorted.every((state, index) => state.rank === index + 1), 'ranks follow the values');
  assert.match(data.source_url, /^https:\/\/www\.inegi\.org\.mx\//);
});

test('the state map has an outline and a population for each of the 32 states, keyed like the export table', async () => {
  const [data, map] = await Promise.all([json('state-exports.json'), json('state-map.json')]);
  assert.equal(map.states.length, 32);
  assert.deepEqual(map.states.map((shape) => shape.cve_ent), data.states.map((state) => state.cve_ent).sort());
  for (const shape of map.states) {
    assert.match(shape.d, /^M[\d.,L-]+Z/, `${shape.name} has a path`);
    assert.ok(Number.isInteger(shape.population) && shape.population > 0, `${shape.name} population`);
  }
  assert.ok(map.width > 0 && map.height > 0);
  assert.match(map.service, /^https:\/\/gaia\.inegi\.org\.mx\//);
  const total = map.states.reduce((sum, shape) => sum + shape.population, 0);
  assert.ok(total > 126_000_000 && total < 127_000_000, `census 2020 population is about 126.0 million, got ${total}`);
});

test('the trade structure parts add up to the published totals', async () => {
  const data = await json('trade-structure.json');
  for (const flow of [data.exports, data.imports]) {
    const sum = flow.parts.reduce((total, part) => total + part.value, 0);
    assert.ok(Math.abs(sum - flow.total) <= 0.2, `parts add up to ${sum}, total ${flow.total}`);
  }
  assert.match(data.source_url, /^https:\/\/(www\.)?inegi\.org\.mx\//);
});

test('the storytelling helpers compute changes, shares and concentration from the data', async () => {
  const { yearlyChanges, formatChange, balanceScale, partShares, tileIntensity, topConcentration } = await helpers();
  const years = [{ year: 2020, exports: 100, imports: 80, balance: 20 }, { year: 2021, exports: 110, imports: 120, balance: -10 }];
  const changes = yearlyChanges(years);
  assert.equal(changes[0].exports, null);
  assert.ok(Math.abs(changes[1].exports - 0.1) < 1e-9 && Math.abs(changes[1].imports - 0.5) < 1e-9);
  assert.equal(formatChange(null, 'es'), '—');
  assert.equal(formatChange(0.1234, 'es'), '+12.3 %');
  assert.equal(formatChange(-0.05, 'en'), '−5.0 %');
  assert.deepEqual(balanceScale(years).map((entry) => entry.ratio), [1, 0.5]);
  assert.equal(Math.round(partShares([{ value: 1 }, { value: 3 }], 4)[1].share), 75);
  assert.equal(tileIntensity(0, 25), 0);
  assert.equal(tileIntensity(25, 25), 1);
  assert.ok(tileIntensity(1, 25) > 0.19, 'small shares stay visible');
  const { top, share } = topConcentration([{ millions: 50 }, { millions: 30 }, { millions: 20 }], 2, 100);
  assert.equal(top.length, 2);
  assert.equal(share, 80);
});

test('the trade context page renders the structure and the state map', async () => {
  const pages = await readFile(path.join(root, 'frontend/src/pages.jsx'), 'utf8');
  assert.ok(pages.includes('<TradeStructure />') && pages.includes('<StateExports />'));
  const [structure, states] = await Promise.all(['trade-structure.jsx', 'state-exports.jsx'].map((name) => readFile(path.join(root, 'frontend/src', name), 'utf8')));
  assert.ok(structure.includes('data-testid="trade-structure"') && states.includes('data-testid="state-exports"'));
  assert.ok(states.includes('<table') && states.includes('<caption>'), 'the map has a table with every figure');
});
