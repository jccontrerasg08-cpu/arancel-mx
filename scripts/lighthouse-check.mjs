// Weekly Lighthouse check of the public site (docs/operations/public-service-observability.md).
//
//   node scripts/lighthouse-check.mjs [--base https://arancel-mx.vercel.app]
//
// Runs Lighthouse (mobile defaults) on the main pages, prints a table, writes it to the job summary when running in
// GitHub Actions, and exits 1 when accessibility, best practices or SEO fall below the floor. Performance is reported
// but never fails the run: it moves with the runner's load, so it is a trend, not a gate.
import { execFileSync } from 'node:child_process';
import { appendFileSync, mkdtempSync, readFileSync } from 'node:fs';
import { tmpdir } from 'node:os';
import { join } from 'node:path';

export const FLOORS = { accessibility: 95, 'best-practices': 90, seo: 95 };
export const PAGES = ['/', '/app', '/learn', '/trade'];

export function evaluate(scores) {
  return Object.entries(FLOORS)
    .filter(([category, floor]) => scores[category] < floor)
    .map(([category, floor]) => `${category} ${scores[category]} < ${floor}`);
}

export function summaryTable(rows) {
  const header = '| Page | Performance | Accessibility | Best practices | SEO | Status |\n| --- | ---: | ---: | ---: | ---: | --- |';
  const lines = rows.map(({ page, scores, problems }) => `| ${page} | ${scores.performance} | ${scores.accessibility} | ${scores['best-practices']} | ${scores.seo} | ${problems.length ? `below floor: ${problems.join(', ')}` : 'ok'} |`);
  return [header, ...lines].join('\n');
}

function audit(url, directory, index) {
  const output = join(directory, `report-${index}.json`);
  execFileSync(
    'npx',
    ['--yes', 'lighthouse@12.8.2', url, '--quiet', '--output=json', `--output-path=${output}`, '--only-categories=performance,accessibility,best-practices,seo', '--chrome-flags=--headless=new --no-sandbox'],
    { stdio: ['ignore', 'ignore', 'inherit'] },
  );
  const { categories } = JSON.parse(readFileSync(output, 'utf8'));
  return Object.fromEntries(Object.entries(categories).map(([id, value]) => [id, Math.round(value.score * 100)]));
}

function main() {
  const flag = process.argv.indexOf('--base');
  const base = (flag > -1 ? process.argv[flag + 1] : 'https://arancel-mx.vercel.app').replace(/\/$/, '');
  const directory = mkdtempSync(join(tmpdir(), 'lighthouse-'));
  const rows = PAGES.map((page, index) => {
    const scores = audit(`${base}${page}`, directory, index);
    return { page, scores, problems: evaluate(scores) };
  });
  const table = summaryTable(rows);
  console.log(table);
  if (process.env.GITHUB_STEP_SUMMARY) appendFileSync(process.env.GITHUB_STEP_SUMMARY, `## Lighthouse (${base})\n\n${table}\n`);
  if (rows.some((row) => row.problems.length)) process.exit(1);
}

if (import.meta.url === `file://${process.argv[1]}`) main();
