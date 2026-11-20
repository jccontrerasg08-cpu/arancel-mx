// Descriptive statistics over INEGI's annual trade balance (millions of US dollars).
// Everything shown on the page is read from trade-balance.json or derived here; nothing is typed by hand.

export function summarizeBalance(years) {
  if (!years.length) return null;
  const surplusYears = years.filter((entry) => entry.balance > 0);
  const deficitYears = years.filter((entry) => entry.balance < 0);
  const pick = (entries, better) => entries.reduce((best, entry) => (better(entry, best) ? entry : best), entries[0]);
  const first = years[0];
  const last = years.at(-1);
  return {
    first,
    last,
    largestSurplus: surplusYears.length ? pick(surplusYears, (entry, best) => entry.balance > best.balance) : null,
    largestDeficit: deficitYears.length ? pick(deficitYears, (entry, best) => entry.balance < best.balance) : null,
    surplusCount: surplusYears.length,
    deficitCount: deficitYears.length,
    exportGrowth: last.exports / first.exports - 1,
    importGrowth: last.imports / first.imports - 1,
    peak: Math.max(...years.flatMap((entry) => [entry.exports, entry.imports])),
  };
}

export const formatMillions = (value, language, { sign = false } = {}) => {
  const text = Math.abs(value).toLocaleString(language === 'en' ? 'en-US' : 'es-MX', { minimumFractionDigits: 1, maximumFractionDigits: 1 });
  if (value < 0) return `−${text}`;
  return sign && value > 0 ? `+${text}` : text;
};

export const formatPercent = (ratio, language) => `${(ratio * 100).toLocaleString(language === 'en' ? 'en-US' : 'es-MX', { maximumFractionDigits: 0 })} %`;
