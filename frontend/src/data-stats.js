// Descriptive figures computed from the verified static data tree (sections, chapters and the
// search index, whose entries are [code, normalized description]). Nothing here is hard-coded.
const LEVEL_DIGITS = [2, 4, 6, 8, 10];

const bump = (map, key) => map.set(key, (map.get(key) || 0) + 1);
const sum = (rows, key) => rows.reduce((total, row) => total + row[key], 0);
const top = (map) => {
  let best = ['', 0];
  for (const entry of map) if (entry[1] > best[1]) best = entry;
  return { code: best[0], count: best[1] };
};

export function computeStats({ sections, chapters, entries }) {
  const levels = Object.fromEntries(LEVEL_DIGITS.map((digits) => [digits, 0]));
  const perChapter = new Map(chapters.map((chapter) => [chapter.code, { code: chapter.code, description: chapter.description, headings: 0, fractions: 0, nico: 0 }]));
  const fractionsPerHeading = new Map();
  const nicoPerFraction = new Map();
  for (const [rawCode] of entries) {
    const code = String(rawCode).replace(/\D/g, '');
    if (!(code.length in levels)) continue;
    levels[code.length] += 1;
    const chapter = perChapter.get(code.slice(0, 2));
    if (code.length === 4 && chapter) chapter.headings += 1;
    if (code.length === 8) {
      if (chapter) chapter.fractions += 1;
      bump(fractionsPerHeading, code.slice(0, 4));
    }
    if (code.length === 10) {
      if (chapter) chapter.nico += 1;
      bump(nicoPerFraction, code.slice(0, 8));
    }
  }
  const chapterRows = [...perChapter.values()];
  const sectionRows = sections.map((section) => {
    const from = Number(section.chapter_from);
    const to = Number(section.chapter_to);
    const inRange = chapterRows.filter((chapter) => Number(chapter.code) >= from && Number(chapter.code) <= to);
    return { roman: section.roman, name: section.name, from: section.chapter_from, to: section.chapter_to, chapters: inRange.length, fractions: sum(inRange, 'fractions'), nico: sum(inRange, 'nico') };
  });
  return {
    levels,
    chapterRows,
    topChapters: [...chapterRows].sort((a, b) => b.fractions - a.fractions || a.code.localeCompare(b.code)).slice(0, 10),
    emptyChapters: chapterRows.filter((chapter) => chapter.fractions === 0).map((chapter) => chapter.code),
    sectionRows,
    topSections: [...sectionRows].sort((a, b) => b.fractions - a.fractions).slice(0, 8),
    busiestHeading: top(fractionsPerHeading),
    mostNico: top(nicoPerFraction),
    averageNico: levels[8] ? levels[10] / levels[8] : 0,
    widestSection: [...sectionRows].sort((a, b) => b.chapters - a.chapters)[0] || null,
  };
}