import assert from 'node:assert/strict';
import test from 'node:test';

import { NATIONAL_NOTES_SOURCE_URL, groupNationalNotes, headingLabel, mentionsHeading } from '../../frontend/src/national-notes.js';

const NOTES = [
  { chapter: '85', note_number: '10', text: 'En la partida 85.17 se encuentran comprendidos los dispositivos llamados "Smartphones".', scope_type: 'chapter', scope_value: '85' },
  { chapter: '85', note_number: '1', text: 'Para efectos de este Capítulo: circuitos de la partida 85.34.', scope_type: 'chapter', scope_value: '85' },
  { chapter: '85', note_number: '2', text: 'Nota sobre las cifras 85.171 y 85.1700, que no son la partida.', scope_type: 'chapter', scope_value: '85' },
  { chapter: '85', note_number: '1', text: 'No obstante lo dispuesto en la Nota 1 de la Sección XVI de la Tarifa.', scope_type: 'section', scope_value: 'XVI' },
  { chapter: '85', note_number: '3', text: '   ', scope_type: 'chapter', scope_value: '85' },
  { chapter: '84', note_number: '1', text: 'Nota de otro capítulo.', scope_type: 'chapter', scope_value: '84' },
];

test('notes are grouped by section and chapter and ordered by number, not as text', () => {
  const grouped = groupNationalNotes(NOTES, '8517130100');
  assert.deepEqual(grouped.chapter.map((note) => note.note_number), ['1', '2', '10']);
  assert.deepEqual(grouped.section.map((note) => note.note_number), ['1']);
  assert.equal(grouped.section_value, 'XVI');
  assert.equal(grouped.total, 4);
});

test('empty notes and notes of another chapter are left out', () => {
  const grouped = groupNationalNotes(NOTES, '85171301');
  assert.ok(grouped.chapter.every((note) => note.scope_value === '85' && note.text.trim()));
  assert.deepEqual(groupNationalNotes(null, '85171301'), { section: [], chapter: [], section_value: null, total: 0, mentioning: 0 });
});

test('a note mentions the heading only when it cites that exact number', () => {
  assert.equal(headingLabel('8517130100'), '85.17');
  assert.equal(headingLabel('85'), null);
  assert.equal(mentionsHeading(NOTES[0], '85171301'), true);
  assert.equal(mentionsHeading(NOTES[1], '85171301'), false);
  assert.equal(mentionsHeading({ text: 'partida 85.171' }, '85171301'), false);
  assert.equal(mentionsHeading({ text: 'partida 185.17' }, '85171301'), false);
  assert.equal(mentionsHeading({ text: 'partidas 85.17, 85.18' }, '85171301'), true);
  assert.equal(mentionsHeading(NOTES[0], '85'), false);
  const grouped = groupNationalNotes(NOTES, '85171301');
  assert.equal(grouped.mentioning, 1);
  assert.equal(grouped.chapter.find((note) => note.note_number === '10').mentions_heading, true);
});

test('the source link comes from the pipeline registry and points to the DOF', () => {
  assert.match(NATIONAL_NOTES_SOURCE_URL, /^https:\/\/dof\.gob\.mx\//);
});
