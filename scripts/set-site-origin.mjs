// Change the public address of the site in one step.
//
//   node scripts/set-site-origin.mjs https://www.example.com [--dry-run] [--no-build]
//
// The origin lives in many tracked files (canonical and share tags, sitemap, robots.txt, the page bridge, the health
// canary, the docs and the tests that pin them). This replaces the current origin (SITE_ORIGIN in
// frontend/src/page-meta.js) with the new one in every tracked text file except the changelog, then rebuilds the
// frontend so the hashed bundle and the per-route HTML agree. The old *.vercel.app address keeps working on Vercel
// and should redirect to the new one (docs/operations/custom-domain.md).
import { execFileSync } from 'node:child_process';
import { readFileSync, writeFileSync } from 'node:fs';

const PAGE_META = 'frontend/src/page-meta.js';
const SKIP = [/^CHANGELOG\.md$/, /^package-lock\.json$/, /\.(png|jpe?g|gif|ico|woff2?|pdf|duckdb|gz)$/i, /^src\/arancel_mx\/api\/static\/site\/assets\/.*-[A-Za-z0-9_-]{8,}\.(js|css)$/];

export function validateOrigin(value) {
  let url;
  try { url = new URL(value); } catch { throw new Error(`"${value}" is not a URL`); }
  if (url.protocol !== 'https:') throw new Error('the origin must use https');
  if (url.pathname !== '/' || url.search || url.hash || value.endsWith('/')) throw new Error('give the origin only, like https://www.example.com (no path, no trailing slash)');
  return url.origin;
}

const escapeDots = (host) => host.replace(/\./g, '\\.');

export function rewriteOrigin(text, from, to) {
  const fromHost = new URL(from).host;
  const toHost = new URL(to).host;
  // Tests pin the address inside regular expressions, with the dots escaped: rewrite that spelling too.
  return text.split(from).join(to).split(fromHost).join(toHost).split(escapeDots(fromHost)).join(escapeDots(toHost));
}

export const currentOrigin = () => /SITE_ORIGIN = '([^']+)'/.exec(readFileSync(PAGE_META, 'utf8'))?.[1];

function main() {
  const args = process.argv.slice(2);
  const dryRun = args.includes('--dry-run');
  const build = !args.includes('--no-build');
  const target = args.find((item) => !item.startsWith('--'));
  if (!target) throw new Error('usage: node scripts/set-site-origin.mjs https://www.example.com [--dry-run] [--no-build]');
  const to = validateOrigin(target);
  const from = currentOrigin();
  if (!from) throw new Error(`SITE_ORIGIN not found in ${PAGE_META}`);
  if (from === to) { console.log(`The site origin is already ${to}`); return; }
  const fromHost = new URL(from).host;

  const files = execFileSync('git', ['ls-files', '-z'], { encoding: 'utf8' }).split('\0').filter(Boolean)
    .filter((file) => !SKIP.some((pattern) => pattern.test(file)));
  const changed = [];
  for (const file of files) {
    let text;
    try { text = readFileSync(file, 'utf8'); } catch { continue; }
    if (text.includes('\0') || !(text.includes(fromHost) || text.includes(escapeDots(fromHost)))) continue;
    const next = rewriteOrigin(text, from, to);
    if (next === text) continue;
    changed.push(file);
    if (!dryRun) writeFileSync(file, next);
  }
  console.log(`${dryRun ? 'Would change' : 'Changed'} ${changed.length} files: ${from} -> ${to}`);
  for (const file of changed) console.log(`  ${file}`);
  if (dryRun || !build) return;
  execFileSync('npm', ['run', 'build:frontend'], { stdio: 'inherit' });
  console.log('Rebuilt the frontend. Run the tests, then follow docs/operations/custom-domain.md for the Vercel and DNS steps.');
}

if (import.meta.url === `file://${process.argv[1]}`) main();
