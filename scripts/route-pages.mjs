// One HTML file per public route, so a crawler or a link preview that does not run JavaScript still reads the
// page's own title, description, canonical address and share metadata instead of the home page's.
//
// Each file is the published index.html with six head tags rewritten; the body and the scripts are identical, so
// the React app boots the same way. Vercel serves `<route>.html` for `/<route>` (cleanUrls) before any rewrite, and
// the dynamic pages (records, chapters, one DOF publication) keep falling through to index.html.
//
// scripts/sync-frontend-static.mjs writes the files; tests/e2e/frontend-route-pages.test.mjs checks them.
import { EDITORIAL_PAGES } from '../frontend/src/content.js';
import { routeMeta } from '../frontend/src/marketing-copy.js';
import { SITE_ORIGIN } from '../frontend/src/page-meta.js';
import { PUBLIC_ROUTES, ROUTE_ALIASES } from '../frontend/src/routes.js';

export const GENERATED_MARKER = '<!-- generated route page: scripts/route-pages.mjs, do not edit -->';

// `/` is index.html itself and `/trade` is a standalone page with its own file.
const OWN_FILE = new Set(['/', '/trade']);

export const routePageRoutes = () => PUBLIC_ROUTES
  .map(({ path }) => path)
  .filter((route) => !route.includes(':') && !OWN_FILE.has(route) && !(route in ROUTE_ALIASES));

export const routePageFile = (route) => `${route.slice(1)}.html`;

// The words the client shows for the route in Spanish, the language of the first paint.
export function routePageMeta(route) {
  const editorial = EDITORIAL_PAGES[route];
  const meta = editorial ? { title: editorial.title, description: editorial.description } : routeMeta(route, 'es');
  if (!meta?.title || !meta?.description) throw new Error(`${route} has no title and description`);
  return { title: `arancel-mx — ${meta.title}`, description: meta.description, url: `${SITE_ORIGIN}${route}` };
}

const escapeAttribute = (value) => String(value).replace(/&/g, '&amp;').replace(/"/g, '&quot;').replace(/</g, '&lt;');
const escapeText = (value) => String(value).replace(/&/g, '&amp;').replace(/</g, '&lt;');

function replaceOnce(html, pattern, replacement, label) {
  const matches = html.match(new RegExp(pattern.source, 'g'));
  if (matches?.length !== 1) throw new Error(`index.html must have exactly one ${label}, found ${matches?.length ?? 0}`);
  return html.replace(pattern, replacement);
}

export function renderRoutePage(indexHtml, route) {
  const meta = routePageMeta(route);
  let html = indexHtml;
  html = replaceOnce(html, /<title>[^<]*<\/title>/, `<title>${escapeText(meta.title)}</title>`, '<title>');
  html = replaceOnce(html, /<meta name="description" content="[^"]*" \/>/, `<meta name="description" content="${escapeAttribute(meta.description)}" />`, 'meta description');
  html = replaceOnce(html, /<link rel="canonical" href="[^"]*" \/>/, `<link rel="canonical" href="${meta.url}" />`, 'canonical link');
  html = replaceOnce(html, /<meta property="og:title" content="[^"]*" \/>/, `<meta property="og:title" content="${escapeAttribute(meta.title)}" />`, 'og:title');
  html = replaceOnce(html, /<meta property="og:description" content="[^"]*" \/>/, `<meta property="og:description" content="${escapeAttribute(meta.description)}" />`, 'og:description');
  html = replaceOnce(html, /<meta property="og:url" content="[^"]*" \/>/, `<meta property="og:url" content="${meta.url}" />`, 'og:url');
  return html.replace(/^<!doctype html>\r?\n/i, (doctype) => `${doctype}${GENERATED_MARKER}\n`);
}
