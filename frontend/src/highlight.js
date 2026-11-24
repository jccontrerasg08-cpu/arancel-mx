// Marks the words of a search query inside a result description, matching the way search
// compares text (accents and case ignored), and returns plain segments: the caller renders
// them as text nodes and <mark> elements, so nothing in the description is parsed as HTML.

const foldChar = (character) => character
  .normalize('NFKD')
  .replace(/\p{M}/gu, '')
  .toLowerCase()
  .replace(/ß/g, 'ss');

// Query words worth marking: at least two characters after folding, longest first so a
// longer word wins over a shorter one that it contains.
export function highlightTerms(query) {
  const terms = String(query ?? '')
    .split(/\s+/u)
    .map(foldChar)
    .map((term) => term.replace(/[^\p{L}\p{N}]/gu, ''))
    .filter((term) => term.length >= 2);
  return [...new Set(terms)].sort((a, b) => b.length - a.length);
}

export function highlightSegments(text, query) {
  const source = String(text ?? '');
  const terms = highlightTerms(query);
  if (!source || !terms.length) return source ? [{ text: source, match: false }] : [];
  // Fold the description character by character, remembering which original character
  // each folded character came from, so a match maps back to the text as written.
  let folded = '';
  const origin = [];
  let start = 0;
  for (const character of source) {
    const piece = foldChar(character);
    folded += piece;
    for (let i = 0; i < piece.length; i += 1) origin.push([start, start + character.length]);
    start += character.length;
  }
  const marked = new Array(source.length).fill(false);
  for (const term of terms) {
    let at = folded.indexOf(term);
    while (at !== -1) {
      const from = origin[at][0];
      const to = origin[at + term.length - 1][1];
      for (let i = from; i < to; i += 1) marked[i] = true;
      at = folded.indexOf(term, at + term.length);
    }
  }
  const segments = [];
  for (let i = 0; i < source.length; i += 1) {
    const last = segments[segments.length - 1];
    if (last && last.match === marked[i]) last.text += source[i];
    else segments.push({ text: source[i], match: marked[i] });
  }
  return segments;
}
