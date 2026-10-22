// Helpers that fake the static data API (decision 0002) inside Playwright tests.
// Records are served the way the exporter writes them: a search index plus one
// records file per HS2 chapter, with missing ancestors filled in so ficha and
// hierarchy lookups resolve.

const LEVELS = { 2: 'hs2', 4: 'hs4', 6: 'hs6', 8: 'fraccion8', 10: 'nico10' };

const normalize = (value) => String(value ?? '')
  .normalize('NFKD')
  .replace(/\p{M}/gu, '')
  .toLowerCase()
  .split(/\s+/u)
  .filter(Boolean)
  .join(' ');

function completeRecord(partial) {
  const code = partial.code;
  return {
    level: LEVELS[code.length],
    description: '',
    unit_name: null,
    igi: null,
    ige: null,
    parent_code: code.length > 2 ? code.slice(0, code.length === 10 ? 8 : code.length - 2) : null,
    dataset_version: '2026.08.15',
    schema_version: '2',
    effective_from: null,
    effective_to: null,
    is_current: true,
    hierarchy: {},
    ligie_version: 'LIGIE-2022',
    validity_basis: 'observed_snapshot',
    ...partial,
  };
}

/**
 * Serve `records` as the only searchable data. `gate` (optional promise) delays
 * the search index response so tests can observe loading states.
 */
export async function serveStaticRecords(page, records, { gate } = {}) {
  const byCode = new Map();
  for (const record of records.map(completeRecord)) {
    byCode.set(record.code, record);
    for (const width of [2, 4, 6, 8]) {
      const ancestor = record.code.slice(0, width);
      if (width < record.code.length && !byCode.has(ancestor)) byCode.set(ancestor, completeRecord({ code: ancestor }));
    }
  }
  const all = [...byCode.values()].sort((a, b) => (a.code < b.code ? -1 : 1));
  await page.route('**/data/v1/search-index.json', async (route) => {
    if (gate) await gate;
    await route.fulfill({
      json: {
        scorer_version: '1',
        entries: records.map((record) => [record.code, normalize(record.description)]),
      },
    });
  });
  for (const chapter of new Set(all.map((record) => record.code.slice(0, 2)))) {
    await page.route(`**/data/v1/records/${chapter}.json`, (route) => route.fulfill({
      json: all.filter((record) => record.code.startsWith(chapter)),
    }));
  }
}

/** Fail one static data file with an HTTP status, counting attempts. */
export async function failStaticFile(page, name, status = 503) {
  const counter = { attempts: 0 };
  await page.route(`**/data/v1/${name}`, async (route) => {
    counter.attempts += 1;
    await route.fulfill({ status, contentType: 'application/json', body: '{}' });
  });
  return counter;
}
