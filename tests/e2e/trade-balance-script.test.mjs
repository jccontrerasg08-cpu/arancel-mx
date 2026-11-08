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
  assert.ok(url.startsWith('https://www.inegi.org.mx/app/api/indicadores/desarrolladores/jsonxml/INDICATOR/33860,33861,33229/es/00/false/BIE/2.0/abc123?type=json'));
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
