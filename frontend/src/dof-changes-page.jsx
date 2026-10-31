import { useEffect, useMemo, useState } from 'react';
import { Link } from 'react-router-dom';

import { editorialPage, OFFICIAL_LINKS } from './content.js';
import { chaptersOf, countFractions, dofEditionUrl, findByCode, formatDate, groupOf, loadDofChanges, operationLabel, rateLabel, SECTION_LABELS } from './dof-changes.js';
import { useLocale } from './locale.jsx';
import { formatCode } from './verified-examples.js';

const GROUPS = [['all', 'Todos', 'All'], ['tariff', 'Decretos de Tarifa', 'Tariff decrees'], ['law', 'Ley y reformas', 'Law and reforms'], ['agreement', 'Acuerdos', 'Agreements']];

function External({ href, children }) {
  return <a href={href} target="_blank" rel="noreferrer">{children} <span aria-hidden="true">↗</span></a>;
}

// Timeline of the DOF publications that changed the tariff, newest first. Each entry opens its
// own page with the fractions it touched, next to links to the DOF and to the original document.
export default function DofChangesPage() {
  const { language } = useLocale();
  const t = (spanish, english) => (language === 'en' ? english : spanish);
  const [state, setState] = useState({ kind: 'loading' });
  const [group, setGroup] = useState('all');
  const [query, setQuery] = useState('');
  const [attempt, setAttempt] = useState(0);
  useEffect(() => {
    let active = true;
    setState({ kind: 'loading' });
    loadDofChanges().then((data) => { if (active) setState({ kind: 'ready', data }); }).catch(() => { if (active) setState({ kind: 'error' }); });
    return () => { active = false; };
  }, [attempt]);
  const page = editorialPage('/changes', language);
  const instruments = state.kind === 'ready' ? state.data.instruments : [];
  const visible = useMemo(() => instruments.filter((item) => group === 'all' || groupOf(item.section) === group), [instruments, group]);
  const matches = useMemo(() => findByCode(instruments, query), [instruments, query]);
  const digits = query.replace(/\D/g, '');

  return <>
    <section className="page-hero"><p className="eyebrow">{page.eyebrow}</p><h1>{page.title}</h1><p>{page.description}</p><p className="disclaimer">{page.disclaimer}</p></section>
    {state.kind === 'loading' && <p className="status" role="status">{t('Cargando los cambios publicados en el DOF…', 'Loading the changes published in the DOF…')}</p>}
    {state.kind === 'error' && <section className="empty-state"><h2>{t('No se pudieron cargar los cambios.', 'The changes could not be loaded.')}</h2><button className="button primary" type="button" onClick={() => setAttempt((current) => current + 1)}>{t('Reintentar', 'Retry')}</button></section>}
    {state.kind === 'ready' && <>
      <section className="workspace" aria-labelledby="code-search-title">
        <h2 id="code-search-title">{t('¿Qué cambios tocaron una fracción?', 'Which changes touched a fraction?')}</h2>
        <label htmlFor="changes-code">{t('Código o prefijo (2 a 8 dígitos)', 'Code or prefix (2 to 8 digits)')}</label>
        <input id="changes-code" type="search" inputMode="numeric" autoComplete="off" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="8517.13.01"/>
        {digits.length >= 2 && <div className="status" role="status" aria-live="polite">{matches.length ? t(`${matches.length} publicaciones del DOF tocan ${formatCode(digits)}.`, `${matches.length} DOF publications touch ${formatCode(digits)}.`) : t(`Ninguna publicación registrada toca ${formatCode(digits)}.`, `No recorded publication touches ${formatCode(digits)}.`)}</div>}
        {matches.length > 0 && <ul className="change-matches">{matches.map(({ instrument, rows, codes, exact }) => <li key={instrument.id}><Link to={`/changes/${instrument.id}`}>{formatDate(instrument.dof_date, language)}</Link> · {operationLabel(instrument.operations[0], language)}
          {exact && rows[0] && <> · IGI {rateLabel(rows[0][1])} · IGE {rateLabel(rows[0][2])}</>}
          {!exact && <> · {t(`${rows.length || codes.length} fracciones`, `${rows.length || codes.length} fractions`)}</>}</li>)}</ul>}
      </section>

      <section className="data-section" aria-labelledby="timeline-title">
        <h2 id="timeline-title">{t('Publicaciones en el DOF', 'DOF publications')}</h2>
        <div className="filter-group" role="group" aria-label={t('Tipo de publicación', 'Publication type')}>{GROUPS.map(([id, spanish, english]) => <button key={id} className="button" type="button" aria-pressed={group === id} onClick={() => setGroup(id)}>{t(spanish, english)}</button>)}</div>
        <p className="status" role="status" aria-live="polite">{t(`${visible.length} de ${instruments.length} publicaciones`, `${visible.length} of ${instruments.length} publications`)}</p>
        <ol className="dof-timeline" data-testid="dof-timeline">{visible.map((item) => {
          const fractions = countFractions(item);
          const chapters = chaptersOf(item);
          return <li key={item.id}>
            <time dateTime={item.dof_date}>{formatDate(item.dof_date, language)}</time>
            <div>
              <h3 style={{ viewTransitionName: `dof-${item.id}` }}><Link to={`/changes/${item.id}`} viewTransition>{item.title}</Link></h3>
              <p className="dof-chips"><span>{SECTION_LABELS[language === 'en' ? 'en' : 'es'][item.section]}</span>{item.operations.slice(0, 3).map((operation) => <span key={operation}>{operationLabel(operation, language)}</span>)}{fractions > 0 && item.section !== 'original' && <span>{fractions === 1 ? t('1 fracción', '1 fraction') : t(`${fractions.toLocaleString('es-MX')} fracciones`, `${fractions.toLocaleString('en-US')} fractions`)}</span>}{chapters.length > 0 && item.section !== 'original' && <span>{t('Cap.', 'Ch.')} {chapters.slice(0, 6).join(', ')}{chapters.length > 6 ? '…' : ''}</span>}</p>
              <p className="dof-actions"><Link className="button" to={`/changes/${item.id}`} viewTransition>{fractions > 0 && item.section !== 'original' ? t('Ver los cambios por fracción', 'See changes by fraction') : t('Ver detalle', 'See details')}</Link><a className="button" href={dofEditionUrl(item.dof_date)} target="_blank" rel="noreferrer">{t('Ver en el DOF', 'See in the DOF')} <span aria-hidden="true">↗</span></a></p>
            </div>
          </li>;
        })}</ol>
      </section>

      <aside className="example-note" data-testid="dof-source"><p>{t('Fuente: instrumentos publicados en el Diario Oficial de la Federación, leídos de su copia en la Cámara de Diputados. “Ver en el DOF” abre la edición de esa fecha; el documento original está en el detalle de cada publicación.', 'Source: instruments published in the Diario Oficial de la Federación, read from their copy at the Cámara de Diputados. “See in the DOF” opens that date’s edition; the original document is in each publication’s details.')} <External href={OFFICIAL_LINKS.dof}>{t('Ir al DOF', 'Go to the DOF')}</External></p></aside>
    </>}
  </>;
}
