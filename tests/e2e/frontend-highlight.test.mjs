import assert from 'node:assert/strict';
import test from 'node:test';

import { highlightSegments, highlightTerms } from '../../frontend/src/highlight.js';

const marked = (segments) => segments.filter((segment) => segment.match).map((segment) => segment.text);

test('marks query words ignoring accents and case, keeping the text as written', () => {
  const segments = highlightSegments('Teléfonos móviles y los de otras redes inalámbricas.', 'telefonos MOVILES');
  assert.deepEqual(marked(segments), ['Teléfonos', 'móviles']);
  assert.equal(segments.map((segment) => segment.text).join(''), 'Teléfonos móviles y los de otras redes inalámbricas.');
});

test('marks every occurrence and folds ß like search does', () => {
  assert.deepEqual(marked(highlightSegments('Leche y leche en polvo', 'leche')), ['Leche', 'leche']);
  assert.deepEqual(marked(highlightSegments('Straße', 'strasse')), ['Straße']);
});

test('ignores one-letter words and punctuation in the query', () => {
  assert.deepEqual(highlightTerms('a de "café," x'), ['cafe', 'de']);
  assert.deepEqual(marked(highlightSegments('Café de olla', 'a')), []);
});

test('returns plain text segments, never markup', () => {
  const segments = highlightSegments('<img src=x onerror=alert(1)> café', 'cafe img');
  assert.deepEqual(marked(segments), ['img', 'café']);
  assert.equal(segments.map((segment) => segment.text).join(''), '<img src=x onerror=alert(1)> café');
});

test('empty text or query gives the text unchanged', () => {
  assert.deepEqual(highlightSegments('Caballos', ''), [{ text: 'Caballos', match: false }]);
  assert.deepEqual(highlightSegments('', 'caballos'), []);
  assert.deepEqual(highlightSegments(null, 'x'), []);
});
