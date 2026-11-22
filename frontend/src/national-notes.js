// National Notes (TIGIE) that the verified release publishes for a chapter, ordered and grouped for the record page.
// The notes are shown literally; matching a heading number inside a note's text is reported as a mention, not as applicability.
import registry from '../../src/arancel_mx/sources/source_registry.json' with { type: 'json' };

// The official DOF publication the pipeline reads the notes from, taken from the same registry the pipeline uses.
export const NATIONAL_NOTES_SOURCE_URL = registry.sources.national_notes.direct_documents.national_notes;
export const NATIONAL_NOTES_CANONICAL_PAGE = registry.sources.national_notes.canonical_page;

const byNumber = (a, b) => {
  const left = Number.parseInt(a.note_number, 10);
  const right = Number.parseInt(b.note_number, 10);
  if (Number.isFinite(left) && Number.isFinite(right) && left !== right) return left - right;
  return String(a.note_number).localeCompare(String(b.note_number), 'es');
};

// "8517130100" -> "85.17"; codes shorter than a heading have no heading.
export const headingLabel = (code) => {
  const digits = String(code || '').replace(/\D/g, '');
  return digits.length >= 4 ? `${digits.slice(0, 2)}.${digits.slice(2, 4)}` : null;
};

// True when the note's text cites this heading number literally (e.g. "partida 85.17", "85.17.").
export const mentionsHeading = (note, code) => {
  const heading = headingLabel(code);
  if (!heading) return false;
  const pattern = new RegExp(`(^|[^\\d.])${heading.replace('.', '\\.')}(?![\\d])`);
  return pattern.test(String(note?.text || ''));
};

// Groups the chapter file into section and chapter notes for one code, in note-number order.
export function groupNationalNotes(notes, code) {
  const digits = String(code || '').replace(/\D/g, '');
  const chapter = digits.slice(0, 2);
  const list = Array.isArray(notes) ? notes.filter((note) => note && typeof note.text === 'string' && note.text.trim()) : [];
  const decorate = (note) => ({ ...note, mentions_heading: mentionsHeading(note, digits) });
  const section = list.filter((note) => note.scope_type === 'section').sort(byNumber).map(decorate);
  const chapterNotes = list.filter((note) => note.scope_type === 'chapter' && String(note.scope_value) === chapter).sort(byNumber).map(decorate);
  return {
    section,
    chapter: chapterNotes,
    section_value: section[0]?.scope_value ?? null,
    total: section.length + chapterNotes.length,
    mentioning: [...section, ...chapterNotes].filter((note) => note.mentions_heading).length,
  };
}
