import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';

import { editorialPage, OFFICIAL_LINKS } from './content.js';
import { CountUp } from './count-up.jsx';
import { computeStats } from './data-stats.js';
import { useLocale } from './locale.jsx';
import { DATA_BASE } from './pages.jsx';
import { formatCode } from './verified-examples.js';

const load = (file, signal) => fetch(`${DATA_BASE}/${file}`, { signal }).then((response) => (response.ok ? response.json() : Promise.reject(new Error(file))));

const number = (value, language) => value.toLocaleString(language === 'en' ? 'en-US' : 'es-MX');
const short = (text, size = 64) => (text.length > size ? `${text.slice(0, size - 1).trim()}…` : text).replace(/[.:]$/u, '');

function Bar({ value, max }) {
  return <span className="data-bar" aria-hidden="true"><span style={{ width: `${max ? Math.max((value / max) * 100, 2) : 0}%` }}/></span>;
}

function DataTable({ caption, columns, rows }) {
  return <div className="data-table-wrap"><table className="data-table"><caption>{caption}</caption><thead><tr>{columns.map((column) => <th key={column.key} scope="col" className={column.numeric ? 'is-numeric' : undefined}>{column.label}</th>)}</tr></thead><tbody>{rows.map((row) => <tr key={row.key}>{columns.map((column, index) => index === 0 ? <th key={column.key} scope="row">{row[column.key]}</th> : <td key={column.key} className={column.numeric ? 'is-numeric' : undefined}>{row[column.key]}</td>)}</tr>)}</tbody></table></div>;
}

export default function DataPage() {
  const { language } = useLocale();
  const t = (spanish, english) => (language === 'en' ? english : spanish);
  const [state, setState] = useState({ kind: 'loading' });
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    const controller = new AbortController();
    setState({ kind: 'loading' });
    Promise.all([load('meta.json', controller.signal), load('sections.json', controller.signal), load('chapters.json', controller.signal), load('search-index.json', controller.signal)])
      .then(([meta, sections, chapters, index]) => setState({ kind: 'ready', meta, stats: computeStats({ sections, chapters, entries: index.entries || [] }) }))
      .catch((error) => { if (error.name !== 'AbortError') setState({ kind: 'error' }); });
    return () => controller.abort();
  }, [attempt]);
  const stats = state.kind === 'ready' ? state.stats : null;
  const page = editorialPage('/data', language);

  const tiles = useMemo(() => stats && [
    ['learn', stats.sectionRows.length, t('Secciones', 'Sections')],
    ['explore', stats.levels[2], t('Capítulos', 'Chapters')],
    ['data', stats.levels[4], t('Partidas (4 dígitos)', 'Headings (4 digits)')],
    ['trust', stats.levels[6], t('Subpartidas (6 dígitos)', 'Subheadings (6 digits)')],
    ['explore', stats.levels[8], t('Fracciones (8 dígitos)', 'Fractions (8 digits)')],
    ['learn', stats.levels[10], t('NICO (10 dígitos)', 'NICO (10 digits)')],
  ], [stats, language]);

  const facts = useMemo(() => {
    if (!stats) return [];
    const [first] = stats.topChapters;
    const heading = stats.busiestHeading;
    const nico = stats.mostNico;
    const wide = stats.widestSection;
    const list = [];
    if (first) list.push([first.fractions, t(`El capítulo ${first.code} (${short(first.description)}) es el que tiene más fracciones.`, `Chapter ${first.code} (${short(first.description)}) has the most fractions.`)]);
    if (heading.count) list.push([heading.count, t(`La partida ${formatCode(heading.code)} concentra ${heading.count} fracciones, más que cualquier otra.`, `Heading ${formatCode(heading.code)} holds ${heading.count} fractions, more than any other.`)]);
    if (stats.averageNico) list.push([stats.averageNico.toFixed(1), t(`NICO por fracción en promedio: ${number(stats.levels[10], language)} códigos de 10 dígitos sobre ${number(stats.levels[8], language)} fracciones.`, `NICO per fraction on average: ${number(stats.levels[10], language)} 10-digit codes over ${number(stats.levels[8], language)} fractions.`)]);
    if (nico.count) list.push([nico.count, t(`La fracción ${formatCode(nico.code)} es la que se desglosa en más NICO.`, `Fraction ${formatCode(nico.code)} breaks down into the most NICO.`)]);
    if (wide) list.push([String(wide.chapters), t(`La Sección ${wide.roman} (${short(wide.name, 48)}) es la que agrupa más capítulos.`, `Section ${wide.roman} (${short(wide.name, 48)}) groups the most chapters.`)]);
    if (stats.emptyChapters.length) list.push([String(stats.emptyChapters.length), t(`capítulos no tienen fracciones en esta release: ${stats.emptyChapters.join(', ')}.`, `chapters have no fractions in this release: ${stats.emptyChapters.join(', ')}.`)]);
    return list;
  }, [stats, language]);

  const maxChapter = stats ? stats.topChapters[0]?.fractions || 0 : 0;
  const maxSection = stats ? stats.topSections[0]?.fractions || 0 : 0;

  return <>
    <section className="page-hero"><p className="eyebrow">{page.eyebrow}</p><h1>{page.title}</h1><p>{page.description}</p><p className="disclaimer">{page.disclaimer}</p></section>
    {state.kind === 'loading' && <><p className="status" role="status">{t('Calculando cifras de la release verificada…', 'Computing figures from the verified release…')}</p><div className="record-skeleton" aria-hidden="true"><div><span className="skeleton"/><span className="skeleton"/><span className="skeleton"/><span className="skeleton"/></div></div></>}
    {state.kind === 'error' && <section className="empty-state"><h2>{t('Las cifras no están disponibles temporalmente.', 'The figures are temporarily unavailable.')}</h2><button className="button primary" type="button" onClick={() => setAttempt((current) => current + 1)}>{t('Reintentar', 'Retry')}</button></section>}
    {stats && <>
      <section className="stat-tiles" aria-label={t('Cifras principales', 'Key figures')}>{tiles.map(([tone, value, label]) => <article key={label} className={`metric-tile metric-tile--${tone}`}><strong><CountUp value={value} language={language}/></strong><span>{label}</span></article>)}</section>

      <section className="data-section" aria-labelledby="facts-title"><h2 id="facts-title">{t('¿Sabías que…?', 'Did you know…?')}</h2><div className="fact-grid">{facts.map(([value, text]) => <article key={text}><strong>{typeof value === 'number' ? <CountUp value={value} language={language}/> : value}</strong><p>{text}</p></article>)}</div></section>

      <section className="data-section" aria-labelledby="chapters-title"><h2 id="chapters-title">{t('Capítulos con más fracciones', 'Chapters with the most fractions')}</h2>
        <DataTable caption={t('Los 10 capítulos con más fracciones de 8 dígitos', 'The 10 chapters with the most 8-digit fractions')} columns={[{ key: 'chapter', label: t('Capítulo', 'Chapter') }, { key: 'description', label: t('Descripción', 'Description') }, { key: 'fractions', label: t('Fracciones', 'Fractions'), numeric: true }, { key: 'nico', label: 'NICO', numeric: true }, { key: 'bar', label: t('Proporción', 'Share') }]}
          rows={stats.topChapters.map((chapter) => ({ key: chapter.code, chapter: <Link to={`/app/record/${chapter.code}`}>{chapter.code}</Link>, description: short(chapter.description, 90), fractions: number(chapter.fractions, language), nico: number(chapter.nico, language), bar: <Bar value={chapter.fractions} max={maxChapter}/> }))}/>
      </section>

      <section className="data-section" aria-labelledby="sections-title"><h2 id="sections-title">{t('Fracciones por sección', 'Fractions by section')}</h2>
        <DataTable caption={t('Las 8 secciones con más fracciones', 'The 8 sections with the most fractions')} columns={[{ key: 'section', label: t('Sección', 'Section') }, { key: 'name', label: t('Nombre', 'Name') }, { key: 'range', label: t('Capítulos', 'Chapters') }, { key: 'fractions', label: t('Fracciones', 'Fractions'), numeric: true }, { key: 'bar', label: t('Proporción', 'Share') }]}
          rows={stats.topSections.map((section) => ({ key: section.roman, section: section.roman, name: short(section.name, 80), range: section.from === section.to ? section.from : `${section.from}–${section.to}`, fractions: number(section.fractions, language), bar: <Bar value={section.fractions} max={maxSection}/> }))}/>
      </section>

      <section className="data-section" aria-labelledby="levels-title"><h2 id="levels-title">{t('Registros por nivel', 'Records by level')}</h2>
        <DataTable caption={t('Cuántos registros tiene cada nivel de la jerarquía', 'How many records each level of the hierarchy has')} columns={[{ key: 'level', label: t('Nivel', 'Level') }, { key: 'digits', label: t('Dígitos', 'Digits'), numeric: true }, { key: 'count', label: t('Registros', 'Records'), numeric: true }]}
          rows={[[2, t('Capítulo', 'Chapter')], [4, t('Partida', 'Heading')], [6, t('Subpartida', 'Subheading')], [8, t('Fracción', 'Fraction')], [10, 'NICO']].map(([digits, label]) => ({ key: String(digits), level: label, digits: String(digits), count: number(stats.levels[digits], language) }))}/>
      </section>

      <aside className="example-note" data-testid="data-source"><p>{t('Cifras calculadas en tu navegador a partir de la release', 'Figures computed in your browser from release')} <code>{state.meta.dataset_version}</code>. {t('Son descriptivas: cuentan registros del dataset y no determinan la clasificación de una mercancía.', 'They are descriptive: they count dataset records and do not determine how a good is classified.')}</p><p><External href={OFFICIAL_LINKS.releases}>{t('Descargar la release completa', 'Download the full release')}</External> · <Link to="/trade-context">{t('Estadísticas de comercio exterior (INEGI)', 'Foreign-trade statistics (INEGI)')}</Link></p></aside>
    </>}
  </>;
}

function External({ href, children }) {
  return <a href={href} target="_blank" rel="noreferrer">{children} <span aria-hidden="true">↗</span></a>;
}
