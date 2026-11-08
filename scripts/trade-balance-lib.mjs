// Pure helpers for scripts/build-trade-balance.mjs: no network, no file access, so they can be tested.
//
// INEGI Indicators API (Banco de Información Económica). The three monthly series below are the
// "Balanza Comercial de Mercancías de México" series, millions of US dollars, original figures:
//   33860 Exportaciones totales FOB   (Sector externo > Valor de las exportaciones e importaciones por tipo de bien > Total)
//   33861 Importaciones totales FOB   (same path)
//   33229 Saldo FOB                   (Sector externo > Resumen de la balanza comercial de mercancías de México)

export const INDICATORS = { exports: '33860', imports: '33861', balance: '33229' };

export const API_BASE = 'https://www.inegi.org.mx/app/api/indicadores/desarrolladores/jsonxml/INDICATOR';

// The token goes in the URL path, so this is the only place that builds the URL and callers must never log it.
export const buildUrl = (token) => `${API_BASE}/${Object.values(INDICATORS).join(',')}/es/00/false/BIE-BISE/2.0/${encodeURIComponent(token)}?type=json`;

const TLS_CODES = new Set(['UNABLE_TO_VERIFY_LEAF_SIGNATURE', 'SELF_SIGNED_CERT_IN_CHAIN', 'DEPTH_ZERO_SELF_SIGNED_CERT', 'UNABLE_TO_GET_ISSUER_CERT_LOCALLY', 'CERT_UNTRUSTED']);

// Node ships its own certificate list and ignores the Windows store, so an antivirus or proxy that re-signs HTTPS
// breaks fetch. `--use-system-ca` (Node 22.15+ and 23.8+) makes Node trust the system store. Never suggest turning
// verification off: the token travels in the URL. The message never includes the request URL.
export const isTlsError = (error) => TLS_CODES.has(error?.cause?.code || error?.code);

export function explainFetchError(error, nodeVersion = process.version) {
  const code = error?.cause?.code || error?.code || 'unknown';
  if (!TLS_CODES.has(code)) return `Could not reach the INEGI API (${code}). Check your connection and try again.`;
  const [major, minor] = nodeVersion.replace(/^v/, '').split('.').map(Number);
  const supportsSystemCa = major > 23 || (major === 23 && minor >= 8) || (major === 22 && minor >= 15);
  const fix = supportsSystemCa
    ? 'Run it again with the system certificate store: set NODE_OPTIONS=--use-system-ca (PowerShell: $env:NODE_OPTIONS = "--use-system-ca").'
    : `This Node (${nodeVersion}) cannot use the system certificate store. Update to Node 22.15 or newer, then set NODE_OPTIONS=--use-system-ca (PowerShell: $env:NODE_OPTIONS = "--use-system-ca").`;
  return `TLS certificate not trusted (${code}). Something on this machine (antivirus, proxy) re-signs HTTPS traffic and Node does not trust its certificate. ${fix} Do not disable certificate checks: the token is sent in the URL.`;
}

const round1 = (value) => Math.round(value * 10) / 10;

const MONTHS_ES = ['enero', 'febrero', 'marzo', 'abril', 'mayo', 'junio', 'julio', 'agosto', 'septiembre', 'octubre', 'noviembre', 'diciembre'];
const MONTHS_EN = ['January', 'February', 'March', 'April', 'May', 'June', 'July', 'August', 'September', 'October', 'November', 'December'];

// INEGI answers { Series: [{ INDICADOR: '33860', OBSERVATIONS: [{ TIME_PERIOD: '2026/09', OBS_VALUE: '77796.6...' }] }] }.
// Returns { exports: Map('2026-09' -> number), imports: Map, balance: Map } and throws if the shape is not that.
export function parseSeries(payload) {
  if (!payload || !Array.isArray(payload.Series)) throw new Error('INEGI response has no Series array');
  const result = {};
  for (const [name, id] of Object.entries(INDICATORS)) {
    const series = payload.Series.find((entry) => String(entry.INDICADOR) === id);
    if (!series || !Array.isArray(series.OBSERVATIONS)) throw new Error(`INEGI response is missing indicator ${id} (${name})`);
    const months = new Map();
    for (const observation of series.OBSERVATIONS) {
      const match = /^(\d{4})\/(\d{2})$/.exec(String(observation.TIME_PERIOD).trim());
      const value = Number.parseFloat(observation.OBS_VALUE);
      if (!match || !Number.isFinite(value)) continue;
      months.set(`${match[1]}-${match[2]}`, value);
    }
    if (!months.size) throw new Error(`INEGI returned no monthly values for indicator ${id} (${name})`);
    result[name] = months;
  }
  return result;
}

// Last month that all three series publish.
export function latestCommonMonth(series) {
  const common = [...series.exports.keys()].filter((month) => series.imports.has(month) && series.balance.has(month)).sort();
  if (!common.length) throw new Error('The three series share no month');
  return common.at(-1);
}

const sumMonths = (map, year, upToMonth) => {
  let total = 0;
  for (let month = 1; month <= upToMonth; month += 1) {
    const value = map.get(`${year}-${String(month).padStart(2, '0')}`);
    if (value === undefined) return null;
    total += value;
  }
  return total;
};

// The `latest` block of frontend/src/trade-balance.json: year to date, growth against the same months of the
// previous year, and the last three months. `retrieved` is the day the API was queried (YYYY-MM-DD).
export function buildLatest(series, retrieved) {
  const last = latestCommonMonth(series);
  const year = Number(last.slice(0, 4));
  const month = Number(last.slice(5, 7));
  const ytd = (name) => sumMonths(series[name], year, month);
  const previous = (name) => sumMonths(series[name], year - 1, month);
  if (ytd('exports') === null || ytd('imports') === null || ytd('balance') === null) throw new Error(`Year ${year} is missing months before ${last}`);
  const growth = (name) => (previous(name) ? Math.round((ytd(name) / previous(name) - 1) * 100) : null);
  const months = [];
  for (let offset = 2; offset >= 0; offset -= 1) {
    const index = year * 12 + (month - 1) - offset;
    const key = `${Math.floor(index / 12)}-${String((index % 12) + 1).padStart(2, '0')}`;
    if (series.exports.has(key) && series.imports.has(key) && series.balance.has(key)) {
      months.push({ month: key, exports: round1(series.exports.get(key)), imports: round1(series.imports.get(key)), balance: round1(series.balance.get(key)) });
    }
  }
  const capitalize = (text) => text.charAt(0).toUpperCase() + text.slice(1);
  const label = month === 1 ? `${capitalize(MONTHS_ES[0])} ${year}` : `Enero–${MONTHS_ES[month - 1]} ${year}`;
  const labelEn = month === 1 ? `January ${year}` : `January–${MONTHS_EN[month - 1]} ${year}`;
  return {
    label,
    label_en: labelEn,
    note: 'Cifras oportunas',
    retrieved,
    source_url: 'https://www.inegi.org.mx/temas/balanza/',
    exports: round1(ytd('exports')),
    imports: round1(ytd('imports')),
    balance: round1(ytd('balance')),
    exports_growth: growth('exports'),
    imports_growth: growth('imports'),
    months,
  };
}
