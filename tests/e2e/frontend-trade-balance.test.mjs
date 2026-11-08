import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import test from 'node:test';

const root = path.resolve(import.meta.dirname, '../..');
const load = async () => {
  const [{ summarizeBalance, formatMillions, formatPercent }, raw] = await Promise.all([
    import(pathToFileURL(path.join(root, 'frontend/src/trade-balance.js')).href),
    readFile(path.join(root, 'frontend/src/trade-balance.json'), 'utf8'),
  ]);
  return { summarizeBalance, formatMillions, formatPercent, data: JSON.parse(raw) };
};

test('every year balances: exports minus imports equals the published balance within rounding', async () => {
  const { data } = await load();
  assert.equal(data.years.length, 10);
  for (const entry of data.years) {
    assert.ok(Math.abs(entry.exports - entry.imports - entry.balance) <= 0.2, `${entry.year} does not add up`);
  }
  assert.deepEqual(data.years.map((entry) => entry.year), [2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023, 2024, 2025]);
  assert.match(data.source_url, /^https:\/\/www\.inegi\.org\.mx\//);
});

test('the latest year-to-date block adds up and cites an INEGI bulletin', async () => {
  const { data } = await load();
  const { latest } = data;
  assert.ok(Math.abs(latest.exports - latest.imports - latest.balance) <= 0.2);
  assert.match(latest.source_url, /^https:\/\/www\.inegi\.org\.mx\/contenidos\/saladeprensa\/boletines\//);
  assert.equal(latest.months.length, 3);
  for (const entry of latest.months) assert.ok(Math.abs(entry.exports - entry.imports - entry.balance) <= 0.2, `${entry.month} does not add up`);
  assert.ok(latest.months.every((entry, index) => index === 0 || entry.month > latest.months[index - 1].month));
  assert.equal(latest.months.at(-1).month, '2026-09');
});

test('the summary finds the extremes and the growth from the data itself', async () => {
  const { data, summarizeBalance } = await load();
  const summary = summarizeBalance(data.years);
  assert.equal(summary.largestSurplus.year, 2020);
  assert.equal(summary.largestDeficit.year, 2022);
  assert.equal(summary.surplusCount, 3);
  assert.equal(summary.deficitCount, 7);
  assert.equal(Math.round(summary.exportGrowth * 100), 78);
  assert.equal(Math.round(summary.importGrowth * 100), 72);
  assert.equal(summary.peak, 664266.7);
  assert.equal(summarizeBalance([]), null);
  assert.equal(summarizeBalance([{ year: 2000, exports: 1, imports: 2, balance: -1 }]).largestSurplus, null);
});

test('figures are formatted for each language with a visible sign', async () => {
  const { formatMillions, formatPercent } = await load();
  assert.equal(formatMillions(-13133.9, 'es'), '−13,133.9');
  assert.equal(formatMillions(209.4, 'es', { sign: true }), '+209.4');
  assert.equal(formatMillions(1234567.8, 'en'), '1,234,567.8');
  assert.equal(formatPercent(0.776, 'es'), '78 %');
});

test('the trade context page shows the balance section and the component reads the data file', async () => {
  const [pages, component] = await Promise.all([readFile(path.join(root, 'frontend/src/pages.jsx'), 'utf8'), readFile(path.join(root, 'frontend/src/trade-balance.jsx'), 'utf8')]);
  assert.ok(pages.includes('<TradeBalance />'));
  assert.ok(component.includes("from './trade-balance.json'") && component.includes('data-testid="trade-balance"'));
});
