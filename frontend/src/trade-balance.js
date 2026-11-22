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

// Year-over-year change of each year against the one before it (a ratio, 0.05 = +5 %); the first year has none.
export const yearlyChanges = (years) => years.map((entry, index) => {
  const previous = years[index - 1];
  const change = (current, before) => (previous && before ? current / before - 1 : null);
  return { year: entry.year, exports: change(entry.exports, previous?.exports), imports: change(entry.imports, previous?.imports) };
});

// Percent with an explicit sign and a dash when there is nothing to compare with.
export const formatChange = (ratio, language) => {
  if (ratio === null || ratio === undefined) return '—';
  const text = (Math.abs(ratio) * 100).toLocaleString(language === 'en' ? 'en-US' : 'es-MX', { minimumFractionDigits: 1, maximumFractionDigits: 1 });
  if (ratio < 0) return `−${text} %`;
  return ratio > 0 ? `+${text} %` : `${text} %`;
};

// Height (0..1) of each year's balance bar against the largest absolute balance, so the strip shows the swings.
export const balanceScale = (years) => {
  const largest = Math.max(...years.map((entry) => Math.abs(entry.balance)), 1);
  return years.map((entry) => ({ year: entry.year, balance: entry.balance, ratio: Math.abs(entry.balance) / largest }));
};

// Shares (percent of the whole) of the parts of a total; the parts are kept in the order given.
export const partShares = (parts, total) => parts.map((part) => ({ ...part, share: (part.value / total) * 100 }));

// Colour intensity (0..1) of a state tile: square root of its share of the largest share, so small states stay visible.
export const tileIntensity = (share, maxShare) => (maxShare > 0 ? Math.sqrt(Math.max(share, 0) / maxShare) : 0);

// How much of the total the n largest states hold, in percent.
export const topConcentration = (states, n, total) => {
  const top = [...states].sort((a, b) => b.millions - a.millions).slice(0, n);
  return { top, share: (top.reduce((sum, state) => sum + state.millions, 0) / total) * 100 };
};
