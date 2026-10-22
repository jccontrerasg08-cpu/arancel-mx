// Usage: node static_api_parity.mjs <static-root> <cases.json>
// Replays /v1 paths through the browser client against an exported tree and
// exits non-zero on the first difference from the Python reference.
import { readFile } from 'node:fs/promises';
import { isDeepStrictEqual } from 'node:util';
import { createStaticApi } from '../../frontend/src/static-api.js';

const [root, casesPath] = process.argv.slice(2);
const fetchImpl = async (url) => {
  try {
    const text = await readFile(`${root}/${url.replace('https://data.test/', '')}`, 'utf8');
    return { ok: true, status: 200, json: async () => JSON.parse(text) };
  } catch {
    return { ok: false, status: 404, json: async () => null };
  }
};
const api = createStaticApi({ base: 'https://data.test', fetchImpl });
const cases = JSON.parse(await readFile(casesPath, 'utf8'));
for (const [path, expected] of Object.entries(cases)) {
  let got;
  try {
    got = await api.request(path);
  } catch (error) {
    got = { error: error.status };
  }
  if (!isDeepStrictEqual(got, expected)) {
    console.error(`MISMATCH ${path}\n got: ${JSON.stringify(got)}\nwant: ${JSON.stringify(expected)}`);
    process.exit(1);
  }
}
console.log(`static API parity: ${Object.keys(cases).length} cases`);
