function normalize(value) {
  return value
    .normalize('NFD')
    .replace(/[\u0300-\u036f]/g, '')
    .toLocaleLowerCase('es-MX');
}

// Index letter of a term: its first character without accents, or '#' when it is not A-Z.
export function glossaryLetter(term) {
  const letter = normalize(term.trim()).charAt(0).toUpperCase();
  return /^[A-Z]$/.test(letter) ? letter : '#';
}

export function filterGlossary(entries, query, category, letter = '') {
  const normalizedQuery = normalize(query.trim());
  return entries.filter((entry) => {
    if (category !== 'Todas' && entry.category !== category) return false;
    if (letter && glossaryLetter(entry.term) !== letter) return false;
    if (!normalizedQuery) return true;
    return normalize(`${entry.term} ${entry.definition}`).includes(normalizedQuery);
  });
}