// Merges the DOF instrument inventory with the extracted Tarifa rows into the file the
// "Cambios" page loads (frontend/src/dof-changes.json). Run `npm run build:dof-changes` after
// either source changes; a node test fails when the committed file is stale.
import { readFile, writeFile } from 'node:fs/promises';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const readJson = async (base, file) => JSON.parse(await readFile(path.join(base, file), 'utf8'));

export async function buildDofChanges(base = root) {
  const legal = await readJson(base, 'src/arancel_mx/sources/legal_instruments.json');
  const inventory = await readJson(base, 'docs/research/ligie-instrument-inventory.json');
  const withRates = new Map(legal.instruments.map((instrument) => [instrument.id, instrument]));
  const pending = new Map((legal.unmodeled || []).map((instrument) => [instrument.id, instrument]));
  const instruments = inventory.instruments.map((item) => {
    const rates = withRates.get(item.id);
    const unmodeled = pending.get(item.id);
    return {
      id: item.id,
      section: item.section,
      title: item.title,
      dof_date: item.dof_date,
      entry_into_force: rates?.entry_into_force ?? item.entry_into_force?.date ?? null,
      validity_end: rates?.validity_end ?? null,
      operations: item.operations || [],
      pdf: item.pdf,
      // The original law lists every fraction, so only its count is kept.
      rate_rows: rates && rates.kind !== 'base' ? rates.rows : null,
      rate_row_count: rates ? rates.rows.length : 0,
      codes: unmodeled ? unmodeled.codes : null,
      pending_reason: unmodeled?.reason ?? null,
    };
  }).sort((a, b) => b.dof_date.localeCompare(a.dof_date) || a.id.localeCompare(b.id));
  return {
    kind: 'arancel-mx/dof-tariff-changes',
    inventory_observed_at: inventory.observed_at,
    rates_version: legal.version,
    instruments,
  };
}

if (process.argv[1] && path.resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const data = await buildDofChanges();
  await writeFile(path.join(root, 'frontend/src/dof-changes.json'), `${JSON.stringify(data)}\n`);
  console.log(`${data.instruments.length} instruments, ${data.instruments.filter((item) => item.rate_rows).length} with rate rows`);
}
