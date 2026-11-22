// Plain-text citation for one record, assembled only from the release identity in meta.json
// (docs/hub-citation-guidance.md). It never invents a SHA-256 and never calls an unverified
// release verified: the reader is sent to that release's SHA256SUMS for the asset hash.

export const REPOSITORY_URL = 'https://github.com/jccontrerasg08-cpu/arancel-mx';

const TAG = /^data-\d{4}\.\d{2}\.\d{2}$/u;

// The release tag from meta.json, or null when it is missing or not shaped data-YYYY.MM.DD.
export const datasetTag = (meta) => {
  if (!meta || typeof meta !== 'object') return null;
  if (typeof meta.dataset_tag === 'string') return TAG.test(meta.dataset_tag) ? meta.dataset_tag : null;
  if (typeof meta.dataset_version === 'string') {
    const tag = `data-${meta.dataset_version}`;
    return TAG.test(tag) ? tag : null;
  }
  return null;
};

const LEVEL = {
  es: { hs2: 'Capítulo', hs4: 'Partida', hs6: 'Subpartida', fraccion8: 'Fracción', nico10: 'NICO' },
  en: { hs2: 'Chapter', hs4: 'Heading', hs6: 'Subheading', fraccion8: 'Tariff item', nico10: 'NICO' },
};

const COPY = {
  es: {
    schema: 'esquema',
    verified: 'release verificada',
    unverified: 'release NO verificada: no la cites como release verificada',
    unknown: 'estado de verificación no publicado: no la cites como release verificada',
    consulted: 'Consultado el',
    at: 'en',
    hash: 'SHA-256 del asset usado: tómalo de SHA256SUMS de esa release.',
  },
  en: {
    schema: 'schema',
    verified: 'verified release',
    unverified: 'release NOT verified: do not cite it as a verified release',
    unknown: 'verification state not published: do not cite it as a verified release',
    consulted: 'Consulted on',
    at: 'at',
    hash: 'SHA-256 of the asset used: copy it from that release’s SHA256SUMS.',
  },
};

const oneLine = (value) => String(value ?? '').replace(/\s+/gu, ' ').trim();

// Returns the citation text, or null when the release identity is not known.
export function recordCitation({ meta, record, pageUrl, consultedOn, language = 'es' }) {
  const tag = datasetTag(meta);
  if (!tag || !record?.code) return null;
  const t = COPY[language] || COPY.es;
  const level = (LEVEL[language] || LEVEL.es)[record.level] || '';
  const state = meta.release_verified === true ? t.verified : meta.release_verified === false ? t.unverified : t.unknown;
  const schema = meta.schema_version ? `${t.schema} ${oneLine(meta.schema_version)}, ` : '';
  const code = oneLine(record.formatted_code || record.code);
  const description = oneLine(record.description);
  const day = String(consultedOn).slice(0, 10);
  return [
    `arancel-mx, dataset ${tag} (${schema}${state}).`,
    `${level ? `${level} ` : ''}${code}${description ? ` — ${description}` : ''}`,
    `${REPOSITORY_URL}/releases/tag/${tag}`,
    `${t.consulted} ${day}${pageUrl ? ` ${t.at} ${pageUrl}` : ''}.`,
    t.hash,
  ].join('\n');
}
