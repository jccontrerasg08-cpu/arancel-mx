import { useEffect, useMemo, useState } from 'react';
import { Link, useParams } from 'react-router-dom';

import { chaptersOf, dofEditionUrl, formatDate, instrumentCodes, loadDofChanges, operationLabel, rateLabel, SECTION_LABELS } from './dof-changes.js';
import { useLocale } from './locale.jsx';
import { formatCode } from './verified-examples.js';

const PAGE_SIZE = 100;

function External({ href, children }) {
  return <a className="button" href={href} target="_blank" rel="noreferrer">{children} <span aria-hidden="true">↗</span></a>;
}

// One DOF publication: its metadata, links to the DOF and the original document, and the
// fractions it touched with the rates it published.
export default function DofChangeDetail() {
  const { id } = useParams();
  const { language } = useLocale();
  const t = (spanish, english) => (language === 'en' ? english : spanish);
  const [state, setState] = useState({ kind: 'loading' });
  const [filter, setFilter] = useState('');
  const [limit, setLimit] = useState(PAGE_SIZE);
  useEffect(() => {
    let active = true;
    setState({ kind: 'loading' });
    setFilter('');
    setLimit(PAGE_SIZE);
    loadDofChanges().then((data) => { if (active) setState({ kind: 'ready', data }); }).catch(() => { if (active) setState({ kind: 'error' }); });
    return () => { active = false; };
  }, [id]);
  const instruments = state.kind === 'ready' ? state.data.instruments : [];
  const index = instruments.findIndex((entry) => entry.id === id);
  const item = index >= 0 ? instruments[index] : null;
  useEffect(() => {
    if (item) document.title = `arancel-mx — ${formatDate(item.dof_date, language)} · ${SECTION_LABELS[language === 'en' ? 'en' : 'es'][item.section]}`;
  }, [item, language]);
  const digits = filter.replace(/\D/g, '');
  const rows = useMemo(() => (item?.rate_rows || []).filter((row) => !digits || row[0].startsWith(digits)), [item, digits]);
  const codes = useMemo(() => instrumentCodes(item || {}).filter((code) => !digits || code.startsWith(digits)), [item, digits]);

  if (state.kind === 'loading') return <p className="status" role="status">{t('Cargando la publicación…', 'Loading the publication…')}</p>;
  if (state.kind === 'error') return <section className="empty-state"><h1>{t('No se pudo cargar la publicación.', 'The publication could not be loaded.')}</h1><Link className="button primary" to="/changes">{t('Volver a los cambios', 'Back to the changes')}</Link></section>;
  if (!item) return <section className="empty-state"><h1>{t('No hay una publicación con ese identificador.', 'There is no publication with that identifier.')}</h1><Link className="button primary" to="/changes">{t('Ver todas las publicaciones', 'See all publications')}</Link></section>;

  const chapters = chaptersOf(item);
  const newer = index > 0 ? instruments[index - 1] : null;
  const older = index < instruments.length - 1 ? instruments[index + 1] : null;
  const sectionLabel = SECTION_LABELS[language === 'en' ? 'en' : 'es'][item.section];

  return <article className="record-page dof-detail" data-testid="dof-detail">
    <nav className="breadcrumb" aria-label={t('Ruta de navegación', 'Breadcrumb')}><ol><li><Link to="/">{t('Inicio', 'Home')}</Link></li><li><Link to="/changes">{t('Cambios en el DOF', 'DOF changes')}</Link></li><li aria-current="page">{formatDate(item.dof_date, language)}</li></ol></nav>
    <p className="eyebrow">{sectionLabel} · DOF {item.dof_date}</p>
    <h1 className="dof-title" lang="es-MX">{item.title}</h1>
    <p className="dof-chips">{item.operations.map((operation) => <span key={operation}>{operationLabel(operation, language)}</span>)}</p>

    <dl className="dof-facts">
      <div><dt>{t('Publicado en el DOF', 'Published in the DOF')}</dt><dd>{formatDate(item.dof_date, language)}</dd></div>
      <div><dt>{t('Entra en vigor', 'Takes effect')}</dt><dd>{item.entry_into_force ? formatDate(item.entry_into_force, language) : t('Por confirmar', 'To be confirmed')}</dd></div>
      {item.validity_end && <div><dt>{t('Vigente hasta', 'In force until')}</dt><dd>{formatDate(item.validity_end, language)}</dd></div>}
      {chapters.length > 0 && <div><dt>{t('Capítulos que toca', 'Chapters it touches')}</dt><dd>{chapters.slice(0, 12).map((chapter, position) => <span key={chapter}>{position > 0 && ', '}<Link to={`/app/record/${chapter}`}>{chapter}</Link></span>)}{chapters.length > 12 ? '…' : ''}</dd></div>}
    </dl>

    <p className="dof-actions"><External href={dofEditionUrl(item.dof_date)}>{t('Ver en el DOF', 'See in the DOF')}</External><External href={item.pdf}>{t('Documento de la publicación (PDF)', 'Publication document (PDF)')}</External></p>

    {item.rate_rows && <section className="data-section" aria-labelledby="rows-title">
      <h2 id="rows-title">{t('Fracciones y tasas que fija esta publicación', 'Fractions and rates this publication sets')}</h2>
      <p className="field-hint">{t('Son las tasas tal como las publica el instrumento. La tasa vigente hoy puede ser otra: abre la ficha de la fracción para verla.', 'These are the rates as the instrument publishes them. The rate in force today may differ: open the fraction’s record to see it.')}</p>
      <label htmlFor="rows-filter">{t('Filtrar por código o prefijo', 'Filter by code or prefix')}</label>
      <input id="rows-filter" type="search" inputMode="numeric" autoComplete="off" value={filter} onChange={(event) => { setFilter(event.target.value); setLimit(PAGE_SIZE); }} placeholder="8517"/>
      <div className="data-table-wrap"><table className="data-table"><caption>{rows.length === 1 ? t('1 fracción', '1 fraction') : t(`${rows.length.toLocaleString('es-MX')} fracciones`, `${rows.length.toLocaleString('en-US')} fractions`)}</caption><thead><tr><th scope="col">{t('Fracción', 'Fraction')}</th><th scope="col" className="is-numeric">IGI</th><th scope="col" className="is-numeric">IGE</th></tr></thead><tbody>{rows.slice(0, limit).map(([code, igi, ige]) => <tr key={code}><th scope="row"><Link to={`/app/record/${code}`}>{formatCode(code)}</Link></th><td className="is-numeric">{rateLabel(igi)}</td><td className="is-numeric">{rateLabel(ige)}</td></tr>)}</tbody></table></div>
      {rows.length > limit && <p><button className="button" type="button" onClick={() => setLimit((current) => current + PAGE_SIZE)}>{t(`Mostrar ${Math.min(PAGE_SIZE, rows.length - limit)} más`, `Show ${Math.min(PAGE_SIZE, rows.length - limit)} more`)}</button> <span className="status">{t(`Mostrando ${limit} de ${rows.length.toLocaleString('es-MX')}`, `Showing ${limit} of ${rows.length.toLocaleString('en-US')}`)}</span></p>}
      {rows.length === 0 && <p className="status" role="status">{t('Ninguna fracción coincide con ese filtro.', 'No fraction matches that filter.')}</p>}
    </section>}

    {!item.rate_rows && item.codes && <section className="data-section" aria-labelledby="codes-title">
      <h2 id="codes-title">{t('Fracciones que toca esta publicación', 'Fractions this publication touches')}</h2>
      {item.pending_reason && <p className="field-hint" lang="es-MX">{item.pending_reason}</p>}
      <p className="field-hint">{t('El dataset aún no modela las tasas de este instrumento; consulta el documento original para verlas.', 'The dataset does not model this instrument’s rates yet; see the original document for them.')}</p>
      <label htmlFor="rows-filter">{t('Filtrar por código o prefijo', 'Filter by code or prefix')}</label>
      <input id="rows-filter" type="search" inputMode="numeric" autoComplete="off" value={filter} onChange={(event) => { setFilter(event.target.value); setLimit(PAGE_SIZE); }} placeholder="0102"/>
      <p className="code-chips">{codes.slice(0, limit).map((code) => <Link key={code} className="chip" to={`/app/record/${code}`}>{formatCode(code)}</Link>)}</p>
      {codes.length > limit && <p><button className="button" type="button" onClick={() => setLimit((current) => current + PAGE_SIZE)}>{t('Mostrar más', 'Show more')}</button> <span className="status">{t(`Mostrando ${limit} de ${codes.length.toLocaleString('es-MX')}`, `Showing ${limit} of ${codes.length.toLocaleString('en-US')}`)}</span></p>}
    </section>}

    {!item.rate_rows && !item.codes && <aside className="example-note"><p>{item.section === 'original' ? t('Es el texto original de la ley: fija toda la tarifa. Las tasas vigentes están en el explorador.', 'This is the law’s original text: it sets the whole tariff. Current rates are in the explorer.') : t('El dataset aún no registra el detalle por fracción de esta publicación. Consulta el documento original.', 'The dataset does not record this publication’s per-fraction detail yet. See the original document.')}</p>{item.section === 'original' && <p><Link className="button primary" to="/app">{t('Abrir el explorador', 'Open the explorer')}</Link></p>}</aside>}

    <nav className="dof-pager" aria-label={t('Publicaciones vecinas', 'Neighboring publications')}>
      {older ? <Link to={`/changes/${older.id}`} rel="prev">← {formatDate(older.dof_date, language)}</Link> : <span/>}
      {newer ? <Link to={`/changes/${newer.id}`} rel="next">{formatDate(newer.dof_date, language)} →</Link> : <span/>}
    </nav>
  </article>;
}
