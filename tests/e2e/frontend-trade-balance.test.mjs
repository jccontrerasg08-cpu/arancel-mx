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
  assert.ok(data.years.every((entry, index) => index === 0 || entry.year === data.years[index - 1].year + 1), 'consecutive years');
  assert.match(data.source_url, /^https:\/\/www\.inegi\.org\.mx\//);
});

test('the latest year-to-date block adds up and cites INEGI', async () => {
  const { data } = await load();
  const { latest } = data;
  assert.ok(Math.abs(latest.exports - latest.imports - latest.balance) <= 0.2);
  assert.match(latest.source_url, /^https:\/\/www\.inegi\.org\.mx\//);
  assert.ok(latest.published || latest.retrieved, 'the block says when its figures were taken');
  assert.equal(latest.months.length, 3);
  for (const entry of latest.months) assert.ok(Math.abs(entry.exports - entry.imports - entry.balance) <= 0.2, `${entry.month} does not add up`);
  assert.ok(latest.months.every((entry, index) => index === 0 || entry.month > latest.months[index - 1].month));
  assert.ok(latest.months.at(-1).month.startsWith(String(latest.label.match(/\d{4}/)[0])), 'the last month belongs to the labelled year');
});

// INEGI's annual table for 2016-2025 (BCMM, millions of dollars), as a fixed fixture for the arithmetic.
const ANNUAL_2016_2025 = [
  [2016, 373953.6, 387087.5, -13133.9], [2017, 409432.6, 420393.6, -10961.0], [2018, 450712.7, 464302.4, -13589.6],
  [2019, 460603.9, 455241.6, 5362.3], [2020, 417170.7, 382985.9, 34184.8], [2021, 494949.0, 505703.1, -10754.1],
  [2022, 577697.5, 605805.4, -28107.9], [2023, 593001.2, 605280.0, -12278.7], [2024, 617770.7, 636218.0, -18447.3],
  [2025, 664266.7, 664057.3, 209.4],
].map(([year, exports, imports, balance]) => ({ year, exports, imports, balance }));

test('the summary finds the extremes and the growth from the data itself', async () => {
  const { summarizeBalance } = await load();
  const summary = summarizeBalance(ANNUAL_2016_2025);
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
  assert.ok(component.includes("LIVE_ENDPOINT = '/api/trade_balance'") && component.includes('buildTradeBalance(parseSeries(payload)'), 'the page computes its figures from the live series');
});
