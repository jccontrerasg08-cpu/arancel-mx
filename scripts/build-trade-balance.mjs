// Refreshes the `latest` block (year to date and last three months) of frontend/src/trade-balance.json
// from INEGI's Indicators API. The annual table (`years`) is left untouched.
//
//   $env:INEGI_TOKEN = "<your token>"        # PowerShell; export INEGI_TOKEN=... in bash
//   node scripts/build-trade-balance.mjs --dry-run   # prints the block and writes nothing
//   node scripts/build-trade-balance.mjs             # writes frontend/src/trade-balance.json
//   npm run build:frontend                           # then rebuild the committed site bundle
//
// The token is read only from the INEGI_TOKEN environment variable and is never printed or stored.
import { readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

import { buildLatest, buildUrl, parseSeries } from './trade-balance-lib.mjs';

const target = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '../frontend/src/trade-balance.json');
const dryRun = process.argv.includes('--dry-run');
const token = process.env.INEGI_TOKEN?.trim();

if (!token) {
  console.error('INEGI_TOKEN is not set. Request a free token at https://www.inegi.org.mx/app/api/indicadores/desarrolladores/jsonxml/ and export it as INEGI_TOKEN.');
  process.exit(1);
}

const response = await fetch(buildUrl(token), { headers: { accept: 'application/json' } });
if (!response.ok) {
  console.error(`INEGI API answered HTTP ${response.status}. Check the token and try again.`);
  process.exit(1);
}
let payload;
try {
  payload = await response.json();
} catch {
  console.error('INEGI API did not return JSON (an invalid token usually answers with an error page).');
  process.exit(1);
}

const latest = buildLatest(parseSeries(payload), new Date().toISOString().slice(0, 10));
console.log(JSON.stringify(latest, null, 2));
if (dryRun) {
  console.log('\n--dry-run: nothing written.');
} else {
  const data = JSON.parse(await readFile(target, 'utf8'));
  await writeFile(target, `${JSON.stringify({ ...data, latest }, null, 2)}\n`);
  console.log(`\nUpdated ${path.relative(process.cwd(), target)}. Run "npm run build:frontend" and commit the result.`);
}
