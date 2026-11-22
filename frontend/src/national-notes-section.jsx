import { NATIONAL_NOTES_SOURCE_URL, groupNationalNotes, headingLabel } from './national-notes.js';

const COPY = {
  es: {
    title: 'Notas nacionales',
    intro: 'Notas Nacionales de la Tarifa que la release registra para este capítulo y su sección. Orientan la clasificación; no la resuelven ni sustituyen las notas legales de Sección y Capítulo.',
    section: (value) => `Sección ${value}`,
    chapter: (value) => `Capítulo ${value}`,
    note: 'Nota',
    mentions: (heading) => `Menciona la partida ${heading}`,
    summary: (total, mentioning, heading) => `${total} ${total === 1 ? 'nota' : 'notas'}${mentioning ? `; ${mentioning} ${mentioning === 1 ? 'menciona' : 'mencionan'} la partida ${heading}` : ''}`,
    none: 'La release no registra Notas Nacionales para este capítulo.',
    source: 'Fuente: Notas Nacionales publicadas en el DOF',
  },
  en: {
    title: 'National Notes',
    intro: 'National Notes of the Tariff that the release records for this chapter and its section. They guide classification; they do not settle it or replace the legal Section and Chapter notes.',
    section: (value) => `Section ${value}`,
    chapter: (value) => `Chapter ${value}`,
    note: 'Note',
    mentions: (heading) => `Mentions heading ${heading}`,
    summary: (total, mentioning, heading) => `${total} ${total === 1 ? 'note' : 'notes'}${mentioning ? `; ${mentioning} ${mentioning === 1 ? 'mentions' : 'mention'} heading ${heading}` : ''}`,
    none: 'The release records no National Notes for this chapter.',
    source: 'Source: National Notes published in the DOF',
  },
};

function NoteList({ notes, label, heading, copy }) {
  if (!notes.length) return null;
  return (
    <div className="national-notes__group">
      <h3>{label}</h3>
      <ol className="national-notes__list">
        {notes.map((note) => (
          <li key={`${note.scope_type}-${note.scope_value}-${note.note_number}`} className={note.mentions_heading ? 'is-relevant' : undefined}>
            <p className="national-notes__meta"><strong>{copy.note} {note.note_number}</strong>{note.mentions_heading && <span className="national-notes__badge">{copy.mentions(heading)}</span>}</p>
            <p className="national-notes__text">{note.text}</p>
          </li>
        ))}
      </ol>
    </div>
  );
}

// Shown on every record page with a chapter; notes are rendered as plain text (React escapes them).
export function NationalNotesSection({ notes, code, language }) {
  const copy = COPY[language === 'en' ? 'en' : 'es'];
  const digits = String(code || '').replace(/\D/g, '');
  if (digits.length < 2 || notes === null) return null;
  const grouped = groupNationalNotes(notes, digits);
  const heading = headingLabel(digits);
  return (
    <section id="record-national-notes" className="national-notes" data-testid="national-notes">
      <h2>{copy.title}</h2>
      {grouped.total === 0 ? <p className="field-hint" data-testid="national-notes-none">{copy.none}</p> : (
        <details>
          <summary data-testid="national-notes-summary">{copy.summary(grouped.total, grouped.mentioning, heading)}</summary>
          <p className="field-hint">{copy.intro}</p>
          <NoteList notes={grouped.section} label={copy.section(grouped.section_value)} heading={heading} copy={copy} />
          <NoteList notes={grouped.chapter} label={copy.chapter(digits.slice(0, 2))} heading={heading} copy={copy} />
        </details>
      )}
      <p className="field-hint"><a href={NATIONAL_NOTES_SOURCE_URL} target="_blank" rel="noreferrer">{copy.source} <span aria-hidden="true">↗</span></a></p>
    </section>
  );
}
