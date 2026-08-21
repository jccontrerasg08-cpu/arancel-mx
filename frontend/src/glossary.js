function normalize(value) {
  return value
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLocaleLowerCase('es-MX');
}

export function filterGlossary(entries, query, category) {
  const normalizedQuery = normalize(query.trim());
  return entries.filter((entry) => {
    if (category !== 'Todas' && entry.category !== category) return false;
    if (!normalizedQuery) return true;
    return normalize(`${entry.term} ${entry.definition}`).includes(normalizedQuery);
  });
}
