import assert from 'node:assert/strict';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import test from 'node:test';

const root = path.resolve(import.meta.dirname, '../..');
const load = () => import(pathToFileURL(path.join(root, 'scripts/trade-balance-lib.mjs')).href);

// Synthetic response in the shape INEGI's Indicators API documents (Series[].INDICADOR / OBSERVATIONS[]).
// The values are made up for the arithmetic: 2025 is 100/90/10 a month, 2026 is 130/117/13 for Jan-Sep.
const observation = (year, month, value) => ({ TIME_PERIOD: `${year}/${String(month).padStart(2, '0')}`, OBS_VALUE: String(value) });
const payload = () => ({
  Series: [
    { INDICADOR: '33860', OBSERVATIONS: [...Array(12)].map((_, i) => observation(2025, i + 1, 100)).concat([...Array(9)].map((_, i) => observation(2026, i + 1, 130))) },
    { INDICADOR: '33861', OBSERVATIONS: [...Array(12)].map((_, i) => observation(2025, i + 1, 90)).concat([...Array(9)].map((_, i) => observation(2026, i + 1, 117))) },
    { INDICADOR: '33229', OBSERVATIONS: [...Array(12)].map((_, i) => observation(2025, i + 1, 10)).concat([...Array(9)].map((_, i) => observation(2026, i + 1, 13))) },
  ],
});

test('the request names the three verified monthly indicators and keeps the token in the path only', async () => {
  const { INDICATORS, buildUrl } = await load();
  assert.deepEqual(INDICATORS, { exports: '33860', imports: '33861', balance: '33229' });
  const url = buildUrl('abc123');
  assert.ok(url.startsWith('https://www.inegi.org.mx/app/api/indicadores/desarrolladores/jsonxml/INDICATOR/33860,33861,33229/es/00/false/BIE-BISE/2.0/abc123?type=json'));
});

test('the annual table is summed from complete years only, shows the last ten and flags adjusted years', async () => {
  const { buildTradeBalance, parseSeries } = await load();
  const only2025 = buildTradeBalance(parseSeries(payload()), '2026-11-08');
  assert.deepEqual(only2025.years, [{ year: 2025, exports: 1200, imports: 1080, balance: 120, adjusted: true }], '2026 is incomplete, so it is not a year yet');
  const long = (value) => [...Array(14 * 12)].map((_, index) => observation(2010 + Math.floor(index / 12), (index % 12) + 1, value));
  const years = buildTradeBalance(parseSeries({ Series: [{ INDICADOR: '33860', OBSERVATIONS: long(2) }, { INDICADOR: '33861', OBSERVATIONS: long(1) }, { INDICADOR: '33229', OBSERVATIONS: long(1) }] }), '2026-01-31').years;
  assert.deepEqual(years.map((entry) => entry.year), [2014, 2015, 2016, 2017, 2018, 2019, 2020, 2021, 2022, 2023]);
  assert.ok(years.filter((entry) => entry.adjusted).map((entry) => entry.year).join() === '2023', 'adjusted from 2023 on');
  assert.equal(years[0].exports, 24);
});

test('the latest block sums the year to date, compares it with the same months of the year before and lists three months', async () => {
  const { buildLatest, parseSeries } = await load();
  const latest = buildLatest(parseSeries(payload()), '2026-11-08');
  assert.equal(latest.label, 'Enero–septiembre 2026');
  assert.equal(latest.label_en, 'January–September 2026');
  assert.equal(latest.retrieved, '2026-11-08');
  assert.equal(latest.exports, 1170);
  assert.equal(latest.imports, 1053);
  assert.equal(latest.balance, 117);
  assert.equal(latest.exports_growth, 30);
  assert.equal(latest.imports_growth, 30);
  assert.deepEqual(latest.months.map((entry) => entry.month), ['2026-07', '2026-08', '2026-09']);
  assert.match(latest.source_url, /^https:\/\/www\.inegi\.org\.mx\//);
});

test('the curl fallback returns status and body, and reports a failure without throwing', async () => {
  const { spawn } = await import('node:child_process');
  const { curlGet } = await import(pathToFileURL(path.join(root, 'scripts/curl-get.mjs')).href);
  // curlGet blocks (spawnSync), so the test server must live in another process.
  const server = spawn(process.execPath, ['-e', `
    require('node:http').createServer((req, res) => {
      res.writeHead(req.url.includes('missing') ? 404 : 200, { 'content-type': 'application/json' });
      res.end(JSON.stringify({ Series: [], path: req.url }));
    }).listen(0, '127.0.0.1', function () { console.log(this.address().port); });
  `], { stdio: ['ignore', 'pipe', 'ignore'] });
  const port = await new Promise((resolve) => server.stdout.once('data', (chunk) => resolve(Number(String(chunk).trim()))));
  const base = `http://127.0.0.1:${port}`;
  try {
    const found = curlGet(`${base}/INDICATOR/1/token-123?type=json`);
    assert.equal(found.ok, true);
    assert.equal(found.status, 200);
    assert.equal(JSON.parse(found.text).path, '/INDICATOR/1/token-123?type=json');
    const missing = curlGet(`${base}/missing`);
    assert.equal(missing.ok, false);
    assert.equal(missing.status, 404);
  } finally {
    server.kill();
  }
  assert.equal(curlGet('http://127.0.0.1:9/', { timeoutMs: 3000 }).ok, false);
});

test('a certificate error explains the system-store fix for the Node version and never suggests disabling checks', async () => {
  const { explainFetchError } = await load();
  const tls = Object.assign(new TypeError('fetch failed'), { cause: { code: 'UNABLE_TO_VERIFY_LEAF_SIGNATURE' } });
  const old = explainFetchError(tls, 'v22.14.0');
  assert.match(old, /Update to Node 22\.15 or newer/);
  assert.match(old, /--use-system-ca/);
  assert.match(explainFetchError(tls, 'v22.15.0'), /^TLS certificate not trusted[^]*set NODE_OPTIONS=--use-system-ca/);
  assert.ok(!/REJECT_UNAUTHORIZED/.test(old) && /Do not disable certificate checks/.test(old));
  assert.match(explainFetchError(new TypeError('fetch failed'), 'v22.15.0'), /Could not reach the INEGI API \(unknown\)/);
});

test('a January-only year is labelled as that month and a response with a missing indicator is rejected', async () => {
  const { buildLatest, parseSeries } = await load();
  const january = payload();
  for (const series of january.Series) series.OBSERVATIONS = series.OBSERVATIONS.filter((entry) => entry.TIME_PERIOD <= '2026/01');
  assert.equal(buildLatest(parseSeries(january), '2026-02-10').label, 'Enero 2026');
  const missing = payload();
  missing.Series.pop();
  assert.throws(() => parseSeries(missing), /33229/);
  assert.throws(() => parseSeries({}), /Series/);
});

test('the script refuses to run without a token and never writes the token anywhere', async () => {
  const { spawnSync } = await import('node:child_process');
  const env = { ...process.env };
  delete env.INEGI_TOKEN;
  const run = spawnSync(process.execPath, [path.join(root, 'scripts/build-trade-balance.mjs'), '--dry-run'], { env, encoding: 'utf8' });
  assert.equal(run.status, 1);
  assert.match(run.stderr, /INEGI_TOKEN is not set/);
  const { readFile } = await import('node:fs/promises');
  const source = await readFile(path.join(root, 'scripts/build-trade-balance.mjs'), 'utf8');
  const printing = source.split('\n').filter((line) => line.includes('console.'));
  assert.ok(printing.length > 0 && printing.every((line) => !/\$\{token\}|\(token\b|,\s*token\b/.test(line)), 'the token variable is never printed');
});
