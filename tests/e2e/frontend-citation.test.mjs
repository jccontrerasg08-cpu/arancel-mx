import assert from 'node:assert/strict';
import test from 'node:test';

import { datasetTag, recordCitation, REPOSITORY_URL } from '../../frontend/src/citation.js';

const record = { code: '85171301', formatted_code: '8517.13.01', level: 'fraccion8', description: 'Teléfonos\n inteligentes.' };
const meta = { dataset_tag: 'data-2026.11.20', dataset_version: '2026.11.20', schema_version: '2', release_verified: true };

test('cites the release tag, its GitHub page, the record and the consultation date', () => {
  const text = recordCitation({ meta, record, pageUrl: 'https://arancel-mx.vercel.app/app/record/85171301', consultedOn: '2026-11-22T17:00:00Z' });
  assert.equal(text, [
    'arancel-mx, dataset data-2026.11.20 (esquema 2, release verificada).',
    'Fracción 8517.13.01 — Teléfonos inteligentes.',
    `${REPOSITORY_URL}/releases/tag/data-2026.11.20`,
    'Consultado el 2026-11-22 en https://arancel-mx.vercel.app/app/record/85171301.',
    'SHA-256 del asset usado: tómalo de SHA256SUMS de esa release.',
  ].join('\n'));
});

test('never calls a release verified unless meta says exactly true', () => {
  const unverified = recordCitation({ meta: { ...meta, release_verified: false }, record, consultedOn: '2026-11-22' });
  assert.match(unverified, /release NO verificada/);
  const unknown = recordCitation({ meta: { dataset_tag: 'data-2026.11.20' }, record, consultedOn: '2026-11-22' });
  assert.match(unknown, /estado de verificación no publicado/);
  assert.doesNotMatch(unknown, /esquema/);
  assert.doesNotMatch(recordCitation({ meta: { ...meta, release_verified: 'true' }, record, consultedOn: '2026-11-22' }), /\(esquema 2, release verificada\)/);
});

test('never writes a hash: it points to SHA256SUMS instead', () => {
  const text = recordCitation({ meta, record, consultedOn: '2026-11-22', language: 'en' });
  assert.doesNotMatch(text, /[0-9a-f]{64}/);
  assert.match(text, /SHA256SUMS/);
  assert.match(text, /^Tariff item 8517\.13\.01/m);
});

test('there is no citation without a well-formed release tag', () => {
  assert.equal(datasetTag({ dataset_version: '2026.11.20' }), 'data-2026.11.20');
  assert.equal(datasetTag({ dataset_tag: 'latest' }), null);
  assert.equal(datasetTag({ dataset_tag: 'data-2026.11.20/../x' }), null);
  assert.equal(datasetTag(null), null);
  assert.equal(recordCitation({ meta: null, record, consultedOn: '2026-11-22' }), null);
  assert.equal(recordCitation({ meta: { dataset_tag: 'latest' }, record, consultedOn: '2026-11-22' }), null);
});
