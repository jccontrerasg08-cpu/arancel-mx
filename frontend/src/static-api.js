// Static read-only client for the GitHub Pages data API (decision 0002).
// It answers the same /v1 paths the frontend used to request from Vercel
// functions, with the semantics of arancel_mx.static_api.StaticApi (the Python
// reference). Parity fixtures generated in Python guard the two against drift.

const DEFAULT_DATA_BASE = 'https://jccontrerasg08-cpu.github.io/arancel-mx/v1';
const REPOSITORY_API = 'https://api.github.com/repos/jccontrerasg08-cpu/arancel-mx';
const SCORER_VERSION = '1';
const SUGGEST_DISCLAIMER = 'This is not a classification. Retrieve-only matches from the official dataset. WCO is not LIGIE/NICO authority.';
const CHILD_LEVEL = { 2: ['hs4', 4], 4: ['hs6', 6], 6: ['fraccion8', 8], 8: ['nico10', 10], 10: null };

export class StaticApiError extends Error {
  constructor(status, message) {
    super(message);
    this.status = status;
  }
}

export function normalizeText(value) {
  return value
    .normalize('NFKD')
    .replace(/\p{M}/gu, '')
    .toLowerCase()
    .replace(/ß/g, 'ss')
    .split(/\s+/u)
    .filter(Boolean)
    .join(' ');
}

export function normalizeCode(value) {
  const text = String(value ?? '').trim();
  if (!text) throw new StaticApiError(422, 'tariff code is required');
  if (/[^0-9.\s-]/u.test(text)) throw new StaticApiError(422, `invalid tariff code: ${value}`);
  const digits = text.replace(/[.\s-]/gu, '');
  if (![2, 4, 6, 8, 10].includes(digits.length)) throw new StaticApiError(422, `invalid tariff code length: ${value}`);
  return digits;
}

function searchCodeCandidate(text) {
  if (/[^0-9.\s-]/u.test(text)) return null;
  const digits = text.replace(/[.\s-]/gu, '');
  return digits && digits.length <= 10 ? digits : null;
}

export function formatNormalizedCode(digits) {
  if (digits.length === 2) return digits;
  if (digits.length === 4) return `${digits.slice(0, 2)}.${digits.slice(2)}`;
  if (digits.length === 6) return `${digits.slice(0, 4)}.${digits.slice(4)}`;
  if (digits.length === 8) return `${digits.slice(0, 4)}.${digits.slice(4, 6)}.${digits.slice(6)}`;
  return `${digits.slice(0, 4)}.${digits.slice(4, 6)}.${digits.slice(6, 8)} ${digits.slice(8)}`;
}

export function createStaticApi({ base = DEFAULT_DATA_BASE, fetchImpl = globalThis.fetch } = {}) {
  const cache = new Map();
  const json = (name, signal) => {
    if (!cache.has(name)) {
      const request = fetchImpl(`${base}/${name}`, { signal, headers: { Accept: 'application/json' } }).then((response) => {
        if (response.status === 404) return null;
        if (!response.ok) throw new StaticApiError(response.status, `Request failed (${response.status})`);
        return response.json();
      });
      request.catch(() => cache.delete(name));
      cache.set(name, request);
    }
    return cache.get(name);
  };

  const chapterRecords = async (chapter, signal) => (await json(`records/${chapter}.json`, signal)) || [];

  const lookup = async (code, signal) => {
    const normalized = normalizeCode(code);
    const record = (await chapterRecords(normalized.slice(0, 2), signal)).find((item) => item.code === normalized);
    if (!record) throw new StaticApiError(404, `tariff record not found: ${normalized}`);
    return record;
  };

  const children = async (code, signal) => {
    const record = await lookup(code, signal);
    const next = CHILD_LEVEL[record.code.length];
    if (!next) return [];
    const [level, width] = next;
    return (await chapterRecords(record.code.slice(0, 2), signal)).filter(
      (item) => item.level === level && item.code.length === width && item.code.startsWith(record.code),
    );
  };

  const parent = async (code, signal) => {
    const record = await lookup(code, signal);
    return record.parent_code == null ? null : lookup(record.parent_code, signal);
  };

  const sectionFor = async (chapter, signal) => {
    const sections = (await json('sections.json', signal)) || [];
    return sections.find((section) => section.chapter_from <= chapter && chapter <= section.chapter_to) || null;
  };

  const ficha = async (code, signal) => {
    const record = await lookup(code, signal);
    const widths = [2, 4, 6, 8, 10].filter((width) => width <= record.code.length);
    return {
      record,
      formatted_code: formatNormalizedCode(record.code),
      section: await sectionFor(record.code.slice(0, 2), signal),
      hierarchy: await Promise.all(widths.map((width) => lookup(record.code.slice(0, width), signal))),
      children: await children(record.code, signal),
    };
  };

  const provenance = async (code, signal) => {
    const record = await lookup(code, signal);
    const data = (await json(`provenance/${record.code.slice(0, 2)}.json`, signal)) || { sources: {}, links: {} };
    return (data.links[record.code] || []).map(([sourceId, role, isPrimary]) => {
      const source = data.sources[sourceId];
      return {
        source_document_id: sourceId,
        role,
        is_primary: isPrimary,
        authority: source.authority,
        publication_venue: source.publication_venue,
        title: source.title,
        source_url: source.source_url,
        sha256: source.sha256,
        published_at: source.published_at,
        effective_from: source.effective_from,
        effective_to: source.effective_to,
      };
    });
  };

  const nationalNotes = async (chapter, signal) => {
    if (!/^\d{2}$/u.test(chapter)) throw new StaticApiError(422, 'chapter must be exactly two digits');
    return (await json(`national-notes/${chapter}.json`, signal)) || [];
  };

  const rank = async (text, signal) => {
    if (typeof text !== 'string' || !text.trim()) throw new StaticApiError(422, 'search text must not be empty');
    const tokens = normalizeText(text).split(' ').filter(Boolean);
    const candidate = searchCodeCandidate(text.trim());
    const index = await json('search-index.json', signal);
    const hits = [];
    for (const [code, description] of index.entries) {
      if (candidate !== null && code === candidate) hits.push([code, 1000, 'exact_code', 1.0]);
      else if (candidate !== null && code.startsWith(candidate)) hits.push([code, 700, 'code_prefix', 0.85]);
      else {
        const matched = tokens.filter((token) => description.includes(token)).length;
        if (matched) hits.push([code, 300 + 25 * matched + (matched === tokens.length ? 5 : 0), 'description', matched / tokens.length]);
      }
    }
    const byCode = (a, b) => (a[0] < b[0] ? -1 : a[0] > b[0] ? 1 : 0);
    if (candidate === null) {
      const best = new Map();
      for (const [code, score] of hits) best.set(code.slice(0, 2), Math.max(score, best.get(code.slice(0, 2)) ?? score));
      hits.sort((a, b) => best.get(b[0].slice(0, 2)) - best.get(a[0].slice(0, 2)) || b[1] - a[1] || byCode(a, b));
    } else {
      hits.sort((a, b) => b[1] - a[1] || byCode(a, b));
    }
    return hits;
  };

  const toResult = async ([code, score, matchKind, confidence], signal) => ({
    record: await lookup(code, signal),
    score,
    match_kind: matchKind,
    scorer_version: SCORER_VERSION,
    confidence,
  });

  const search = async (text, limit = 20, signal) => {
    if (limit <= 0) throw new StaticApiError(422, 'search limit must be greater than zero');
    return Promise.all((await rank(text, signal)).slice(0, limit).map((hit) => toResult(hit, signal)));
  };

  const suggest = async (text, limit = 5, signal) => {
    if (limit <= 0) throw new StaticApiError(422, 'suggest limit must be greater than zero');
    const ranked = await rank(text, signal);
    // Fraction records are exactly the 8-digit codes (level "fraccion8").
    const preferred = ranked.filter(([code]) => code.length === 8);
    const chosen = await Promise.all((preferred.length ? preferred : ranked).slice(0, limit).map((hit) => toResult(hit, signal)));
    return Promise.all(
      chosen.map(async (item) => ({
        search: item,
        ficha: await ficha(item.record.code, signal),
        national_notes: await nationalNotes(item.record.code.slice(0, 2), signal),
        disclaimer: SUGGEST_DISCLAIMER,
      })),
    );
  };

  const repository = async (signal) => {
    const response = await fetchImpl(`${REPOSITORY_API}/releases?per_page=5`, { signal, headers: { Accept: 'application/vnd.github+json' } });
    if (!response.ok) throw new StaticApiError(response.status, `Request failed (${response.status})`);
    const releases = await response.json();
    return {
      releases: releases
        .filter((item) => item.published_at)
        .map((item) => ({ tag: item.tag_name, publishedAt: item.published_at, url: item.html_url })),
      source: 'live',
    };
  };

  // Resolve a /v1 path (with optional query string) the way the Vercel functions did.
  const request = async (path, signal) => {
    const url = new URL(path, 'https://static.invalid');
    const parts = url.pathname.replace(/\/+$/u, '').split('/').slice(1);
    if (parts[0] !== 'v1') throw new StaticApiError(404, `unknown path: ${path}`);
    const [, resource, value, sub] = parts;
    const limit = (fallback) => (url.searchParams.has('limit') ? Number(url.searchParams.get('limit')) : fallback);
    if (resource === 'meta' && !value) return json('meta.json', signal);
    if (resource === 'sections' && !value) return json('sections.json', signal);
    if (resource === 'chapters' && !value) return json('chapters.json', signal);
    if (resource === 'chapters' && sub === 'national-notes') return nationalNotes(value, signal);
    if (resource === 'search') return search(url.searchParams.get('q') ?? '', limit(20), signal);
    if (resource === 'suggest') return suggest(url.searchParams.get('q') ?? '', limit(5), signal);
    if (resource === 'lookup' && value) return lookup(value, signal);
    if (resource === 'ficha' && value) return ficha(value, signal);
    if (resource === 'codes' && value && sub === 'parent') return parent(value, signal);
    if (resource === 'codes' && value && sub === 'children') return children(value, signal);
    if (resource === 'codes' && value && sub === 'provenance') return provenance(value, signal);
    if (resource === 'repository') return repository(signal);
    throw new StaticApiError(404, `unknown path: ${path}`);
  };

  return { request, lookup, ficha, parent, children, provenance, nationalNotes, search, suggest };
}
