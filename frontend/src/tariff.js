export function displayRate(rate) {
  if (rate == null) return '—';
  if (typeof rate === 'string' || typeof rate === 'number') return String(rate);
  if (typeof rate.text === 'string' && rate.text.trim()) return rate.text;
  if (typeof rate.value === 'number' && Number.isFinite(rate.value)) return `${rate.value}%`;
  return '—';
}

export function selectPrimarySearchResults(results, query) {
  const candidates = Array.isArray(results) ? results : [];
  const code = String(query || '').replace(/\D/g, '');
  const exact = code
    ? candidates.filter((item) => String(item?.record?.code || item?.code || '') === code)
    : [];
  const exactIsEstimable = exact.some((item) => /^\d{8}(?:\d{2})?$/.test(String(item?.record?.code || item?.code || '')));
  return exact.length && exactIsEstimable ? exact : candidates;
}
