// Markdown export of one record page, built only from data the page already loaded from the verified release.
// Nothing is computed or inferred: a value the release does not publish is written as such, never as 0 or "none".
import { nomAnnexState } from './nom-state.js';

const MARKDOWN_SPECIAL = /[\\`*_[\]<>|~]/g;

// Escape text so it renders literally and cannot inject links, HTML or table cells.
export const escapeMarkdown = (value) => String(value ?? '').replace(/\r?\n/g, ' ').replace(MARKDOWN_SPECIAL, (character) => `\\${character}`);

// Only plain http(s) links are written; anything else is dropped rather than trusted.
export const safeUrl = (value) => {
  try {
    const url = new URL(String(value));
    return url.protocol === 'https:' || url.protocol === 'http:' ? url.href : null;
  } catch {
    return null;
  }
};

const link = (label, href) => {
  const url = safeUrl(href);
  return url ? `[${escapeMarkdown(label)}](<${url.replace(/>/g, '%3E')}>)` : escapeMarkdown(label);
};

const COPY = {
  es: {
    title: 'Ficha arancelaria',
    disclaimer: 'Ficha de consulta generada con datos de una release verificada de arancel-mx. No es una clasificación arancelaria oficial, no determina contribuciones ni el cumplimiento de regulaciones y no sustituye la consulta del DOF y de la autoridad competente.',
    release: 'Release de datos',
    generated: 'Generada el',
    code: 'Código',
    description: 'Descripción',
    unit: 'Unidad de medida',
    igi: 'IGI (importación)',
    ige: 'IGE (exportación)',
    validity: 'Vigencia de la tasa publicada',
    notPublished: 'No publicado en esta release',
    hierarchy: 'Jerarquía',
    sources: 'Fuentes registradas',
    noSources: 'La release no registra fuentes para este código.',
    nom: 'NOM del Anexo 2.4.1',
    nomListed: 'Normas que el anexo lista para esta fracción. Esto señala qué revisar; no determina si el producto está sujeto.',
    nomStates: {
      not_listed: 'La fracción no aparece en el Anexo 2.4.1 tal como se leyó en esta release. Otras regulaciones pueden aplicar.',
      not_listed_carried: 'La fracción no aparece en el Anexo 2.4.1 leído en una release anterior, porque el anexo vigente no se pudo leer. Anexo leído en la release',
      unavailable: 'Los datos del Anexo 2.4.1 no están disponibles en esta release.',
      unknown: 'La release no indica si incluye el Anexo 2.4.1; no se puede saber si la fracción aparece.',
    },
    scope: 'acotación',
    page: 'página',
    from: 'desde',
    to: 'hasta',
  },
  en: {
    title: 'Tariff record',
    disclaimer: 'Reference record generated from a verified arancel-mx release. It is not an official tariff classification, does not determine duties or regulatory compliance, and does not replace the DOF or the competent authority.',
    release: 'Data release',
    generated: 'Generated on',
    code: 'Code',
    description: 'Description',
    unit: 'Unit of measure',
    igi: 'IGI (import duty)',
    ige: 'IGE (export duty)',
    validity: 'Validity of the published rate',
    notPublished: 'Not published in this release',
    hierarchy: 'Hierarchy',
    sources: 'Recorded sources',
    noSources: 'The release records no sources for this code.',
    nom: 'NOM in Annex 2.4.1',
    nomListed: 'Standards the annex lists for this fraction. This points to what to check; it does not determine whether the product is subject.',
    nomStates: {
      not_listed: 'The fraction is not listed in Annex 2.4.1 as read in this release. Other regulations may still apply.',
      not_listed_carried: 'The fraction is not listed in Annex 2.4.1 as read in an earlier release, because the current annex could not be read. Annex read in release',
      unavailable: 'Annex 2.4.1 data is not available in this release.',
      unknown: 'The release does not say whether it includes Annex 2.4.1, so it cannot tell whether the fraction is listed.',
    },
    scope: 'limit',
    page: 'page',
    from: 'from',
    to: 'to',
  },
};

const present = (value) => value !== null && value !== undefined && String(value).trim() !== '';

export function fichaMarkdown({ record, hierarchy = [], provenance = [], regulations = null, generatedAt, language = 'es' }) {
  const t = COPY[language === 'en' ? 'en' : 'es'];
  const code = String(record.code || '').replace(/\D/g, '');
  const value = (field) => (present(record[field]) ? escapeMarkdown(record[field]) : `_${t.notPublished}_`);
  const lines = [
    `# ${t.title} ${escapeMarkdown(record.formatted_code || code)}`,
    '',
    `> ${t.disclaimer}`,
    '',
    `- **${t.release}:** ${present(record.dataset_version) ? `data-${escapeMarkdown(record.dataset_version)}` : `_${t.notPublished}_`}`,
    `- **${t.generated}:** ${escapeMarkdown(generatedAt)}`,
    '',
    `| | |`,
    `|---|---|`,
    `| ${t.code} | ${escapeMarkdown(code)} |`,
    `| ${t.description} | ${value('description')} |`,
    `| ${t.unit} | ${value('unit_name')} |`,
    `| ${t.igi} | ${value('igi')} |`,
    `| ${t.ige} | ${value('ige')} |`,
    `| ${t.validity} | ${present(record.effective_from) ? `${t.from} ${escapeMarkdown(record.effective_from)}${present(record.effective_to) ? ` ${t.to} ${escapeMarkdown(record.effective_to)}` : ''}` : `_${t.notPublished}_`} |`,
  ];
  const ancestors = hierarchy.filter((entry) => entry && present(entry.code) && String(entry.code).replace(/\D/g, '') !== code);
  if (ancestors.length) {
    lines.push('', `## ${t.hierarchy}`, '');
    for (const entry of ancestors) lines.push(`- ${escapeMarkdown(entry.code)}${present(entry.description) ? ` — ${escapeMarkdown(entry.description)}` : ''}`);
  }
  const state = nomAnnexState(regulations, code);
  if (state !== 'not_a_fraction') {
    lines.push('', `## ${t.nom}`, '');
    if (state === 'listed') {
      lines.push(t.nomListed, '');
      for (const item of regulations.requirements) {
        const source = regulations.sources?.[item.source_document_id];
        const details = [present(item.scope) ? `${t.scope}: ${escapeMarkdown(item.scope)}` : null, present(item.annex_page) ? `${t.page} ${escapeMarkdown(item.annex_page)}` : null].filter(Boolean).join('; ');
        lines.push(`- ${source ? link(item.nom, source.source_url) : escapeMarkdown(item.nom)}${details ? ` (${details})` : ''}`);
      }
    } else {
      lines.push(state === 'not_listed_carried' ? `${t.nomStates[state]} ${escapeMarkdown(regulations.annex.carried_from)}.` : t.nomStates[state]);
    }
  }
  lines.push('', `## ${t.sources}`, '');
  const sources = provenance.filter((entry) => entry && (present(entry.source_url) || present(entry.source_name)));
  if (sources.length) for (const entry of sources) lines.push(`- ${link(entry.source_name || entry.source_url, entry.source_url)}`);
  else lines.push(t.noSources);
  return `${lines.join('\n')}\n`;
}
