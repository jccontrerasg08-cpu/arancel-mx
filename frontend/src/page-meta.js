export const SITE_ORIGIN = 'https://arancel-mx.vercel.app';
export const DEFAULT_SUMMARY = 'Datos arancelarios mexicanos verificables.';

// The page a record route is currently showing, set once its record has loaded so the title and the
// share metadata name the fraction instead of repeating the site's generic text.
let recordMeta = null;
export const setRecordMeta = (meta) => { recordMeta = meta; };
export const recordMetaFor = (pathname) => (recordMeta && recordMeta.path === pathname ? recordMeta : null);

const setHead = (selector, value, attribute = 'content') => document.querySelector(selector)?.setAttribute(attribute, value);

const clip = (text, length) => (text.length > length ? `${text.slice(0, length - 1).trimEnd()}…` : text);

// Keeps the title and the share/search metadata of the static page in step with the client route.
export function applyPageMeta({ pathname, title, summary, locale }) {
  const url = `${SITE_ORIGIN}${pathname === '/' ? '/' : pathname.replace(/\/+$/, '')}`;
  document.title = `arancel-mx — ${title}`;
  setHead('meta[name="description"]', summary);
  setHead('meta[property="og:title"]', document.title);
  setHead('meta[property="og:description"]', summary);
  setHead('meta[property="og:url"]', url);
  setHead('meta[property="og:locale"]', locale);
  setHead('link[rel="canonical"]', url, 'href');
}

// Title and description for a loaded record, e.g. "8517.13.01 · Teléfonos inteligentes".
export function describeRecord({ code, description, rates, language }) {
  const name = clip(String(description || '').replace(/\s+/g, ' ').trim().replace(/[.\s]+$/, ''), 70);
  const lead = language === 'en' ? 'Verified record' : 'Ficha verificada';
  const summary = clip(`${lead} ${code}${name ? `: ${name}.` : '.'}${rates ? ` ${rates}` : ''}`, 160);
  return { title: name ? `${code} · ${name}` : code, summary };
}
