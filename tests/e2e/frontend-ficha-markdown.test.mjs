import assert from 'node:assert/strict';
import test from 'node:test';

import { escapeMarkdown, fichaMarkdown, safeUrl } from '../../frontend/src/ficha-markdown.js';

const RECORD = { code: '85171301', formatted_code: '8517.13.01', description: 'Teléfonos inteligentes.', unit_name: 'Pieza', igi: 'Ex.', ige: 'Ex.', effective_from: '2022-12-12', effective_to: null, dataset_version: '2026.11.20' };
const REGULATIONS = {
  annex: { status: 'available' },
  sources: { annex: { source_url: 'https://www.snice.gob.mx/~oracle/SNICE_DOCS/anexo.pdf' } },
  requirements: [{ fraction8: '85171301', numeral: 3, nom: 'NOM-024-SCFI-2013', scope: 'Únicamente: equipos', annex_page: 700, source_document_id: 'annex' }],
};
const base = { record: RECORD, generatedAt: '2026-11-22T10:00:00.000Z', provenance: [{ source_name: 'LIGIE 2022', source_url: 'https://www.diputados.gob.mx/LeyesBiblio/pdf/LIGIE_2022.pdf' }] };

test('the ficha carries the release, the generation date and the literal published values', () => {
  const text = fichaMarkdown({ ...base, regulations: REGULATIONS });
  assert.match(text, /^# Ficha arancelaria 8517\.13\.01\n/);
  assert.match(text, /\*\*Release de datos:\*\* data-2026\.11\.20/);
  assert.match(text, /\*\*Generada el:\*\* 2026-11-22T10:00:00\.000Z/);
  assert.match(text, /\| IGI \(importación\) \| Ex\. \|/);
  assert.match(text, /\| Vigencia de la tasa publicada \| desde 2022-12-12 \|/);
  assert.match(text, /No es una clasificación arancelaria oficial/);
  assert.match(text, /tasas generales de la LIGIE.*no incluye tasas preferenciales/);
});

test('NOM rows keep their scope, page and a link to the annex, and say they do not determine compliance', () => {
  const text = fichaMarkdown({ ...base, regulations: REGULATIONS });
  assert.match(text, /- \[NOM-024-SCFI-2013\]\(<https:\/\/www\.snice\.gob\.mx\/~oracle\/SNICE_DOCS\/anexo\.pdf>\) \(acotación: Únicamente: equipos; página 700\)/);
  assert.match(text, /no determina si el producto está sujeto/);
});

test('missing values are written as not published, never as zero or "no aplica"', () => {
  const text = fichaMarkdown({ ...base, record: { ...RECORD, igi: null, ige: '', effective_from: null }, regulations: { requirements: [] } });
  assert.match(text, /\| IGI \(importación\) \| _No publicado en esta release_ \|/);
  assert.match(text, /\| IGE \(exportación\) \| _No publicado en esta release_ \|/);
  assert.match(text, /\| Vigencia de la tasa publicada \| _No publicado en esta release_ \|/);
  assert.match(text, /no se puede saber si la fracción aparece/);
  assert.doesNotMatch(text, /\| 0 \|/);
});

test('each annex state is written explicitly', () => {
  assert.match(fichaMarkdown({ ...base, regulations: { annex: { status: 'available' }, requirements: [] } }), /no aparece en el Anexo 2\.4\.1 tal como se leyó en esta release/);
  assert.match(fichaMarkdown({ ...base, regulations: { annex: { status: 'carried_forward', carried_from: '2026.11.19' }, requirements: [] } }), /release anterior.*2026\.11\.19\./);
  assert.match(fichaMarkdown({ ...base, regulations: { annex: { status: 'unavailable' }, requirements: [] } }), /no están disponibles en esta release/);
  assert.doesNotMatch(fichaMarkdown({ ...base, record: { ...RECORD, code: '8517' }, regulations: null }), /Anexo 2\.4\.1/);
});

test('text from the data cannot inject links, HTML or table cells', () => {
  const text = fichaMarkdown({ ...base, record: { ...RECORD, description: 'Equipo [clic](javascript:alert(1)) <img src=x onerror=alert(1)> | celda' }, regulations: null });
  assert.match(text, /Equipo \\\[clic\\\]\(javascript:alert\(1\)\) \\<img src=x onerror=alert\(1\)\\> \\\| celda/);
  assert.doesNotMatch(text, /(^|[^\\])<img/);
  assert.equal(escapeMarkdown('a\nb'), 'a b');
});

test('only http(s) links are written; other schemes become plain text', () => {
  assert.equal(safeUrl('javascript:alert(1)'), null);
  assert.equal(safeUrl('not a url'), null);
  assert.equal(safeUrl('https://dof.gob.mx/x'), 'https://dof.gob.mx/x');
  const text = fichaMarkdown({ ...base, provenance: [{ source_name: 'Fuente', source_url: 'javascript:alert(1)' }], regulations: null });
  assert.match(text, /## Fuentes registradas\n\n- Fuente\n/);
});

test('the English ficha uses English labels', () => {
  const text = fichaMarkdown({ ...base, regulations: REGULATIONS, language: 'en' });
  assert.match(text, /^# Tariff record 8517\.13\.01/);
  assert.match(text, /\| IGI \(import duty\) \| Ex\. \|/);
  assert.match(text, /does not determine duties or regulatory compliance/);
});
