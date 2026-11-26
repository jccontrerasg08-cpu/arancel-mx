import { useEffect, useState } from 'react';
import { Link } from 'react-router-dom';

import { OFFICIAL_LINKS } from './content.js';
import { useLocale } from './locale.jsx';
import { loadReleaseDiff, RELEASE_DIFF_EVENTS } from './release-diff.js';
import { formatCode } from './verified-examples.js';

const PAGE_SIZE = 25;

export default function ReleaseDiffPanel({ base }) {
  const { language } = useLocale();
  const english = language === 'en';
  const t = (es, en) => (english ? en : es);
  const [state, setState] = useState({ kind: 'loading' });
  const [attempt, setAttempt] = useState(0);
  const [event, setEvent] = useState('');
  const [page, setPage] = useState(0);

  useEffect(() => {
    const controller = new AbortController();
    setState({ kind: 'loading' });
    loadReleaseDiff(base, { signal: controller.signal })
      .then((result) => { if (!controller.signal.aborted) setState(result); })
      .catch(() => { if (!controller.signal.aborted) setState({ kind: 'error' }); });
    return () => controller.abort();
  }, [base, attempt]);

  const changes = state.report?.changes ?? [];
  const visible = event ? changes.filter((change) => change.event === event) : changes;
  const options = new Set(changes.map((change) => change.event));
  const start = page * PAGE_SIZE;
  const end = Math.min(start + PAGE_SIZE, visible.length);
  const label = (id) => RELEASE_DIFF_EVENTS[id][english ? 1 : 0];
  const release = (version) => <a href={`${OFFICIAL_LINKS.releases}/tag/data-${version}`}><code>data-{version}</code></a>;
  const value = (text) => text ?? <em>{t('Sin valor registrado', 'No recorded value')}</em>;

  return <section className="data-section" aria-labelledby="release-diff-heading">
    <h2 id="release-diff-heading">{t('Cambios entre releases', 'Changes between releases')}</h2>
    {state.kind === 'loading' && <p aria-live="polite">{t('Cargando comparación…', 'Loading comparison…')}</p>}
    {state.kind === 'unavailable' && <p>{t('La comparación de releases aún no está publicada.', 'The release comparison has not been published yet.')}</p>}
    {state.kind === 'error' && <><p role="alert">{t('No se pudo cargar la comparación.', 'The comparison could not be loaded.')}</p><button className="button secondary" type="button" onClick={() => setAttempt((count) => count + 1)}>{t('Reintentar comparación', 'Retry comparison')}</button></>}
    {state.kind === 'ready' && <>
      <p>{t('Anterior', 'Previous')} {release(state.from)} <span aria-hidden="true">→</span> {t('Posterior', 'Later')} {release(state.to)}</p>
      <p>{t('Las dos releases se verificaron al publicar la comparación. Consulta el DOF para confirmar la fecha en que surte efecto un cambio normativo.', 'Both releases were verified when the comparison was published. Consult the DOF to confirm when a legal change takes effect.')} <Link to="/changes">{t('Ver decretos', 'See decrees')}</Link></p>
      {changes.length === 0 && <p>{t('No se encontraron cambios en los registros arancelarios comparados.', 'No changes were found in the tariff records compared.')}</p>}
      {changes.length > 0 && <>
        <label>{t('Tipo de cambio', 'Change type')}{' '}
          <select value={event} onChange={(e) => { setEvent(e.target.value); setPage(0); }}>
            <option value="">{t('Todos', 'All')}</option>
            {Object.keys(RELEASE_DIFF_EVENTS).filter((id) => options.has(id)).map((id) => <option key={id} value={id}>{label(id)}</option>)}
          </select>
        </label>
        <p aria-live="polite">{start + 1}–{end} {t('de', 'of')} {visible.length} {t('cambios', 'changes')}</p>
        <div className="data-table-wrap"><table className="data-table">
          <caption>{t('Registros arancelarios modificados', 'Changed tariff records')}</caption>
          <thead><tr>{[t('Código', 'Code'), t('Cambio', 'Change'), t('Antes', 'Before'), t('Después', 'After')].map((name) => <th scope="col" key={name}>{name}</th>)}</tr></thead>
          <tbody>{visible.slice(start, end).map((change) => <tr key={`${change.code}-${change.event}`}>
            <th scope="row"><code>{formatCode(change.code)}</code></th>
            <td>{label(change.event)}{change.event !== 'row_removed' && <><br/><Link to={`/app/record/${change.code}`}>{t('Ficha actual', 'Current record')}</Link></>}</td>
            <td>{value(change.old_value)}</td>
            <td>{value(change.new_value)}</td>
          </tr>)}</tbody>
        </table></div>
        {visible.length > PAGE_SIZE && <div className="button-row">
          <button className="button secondary" type="button" disabled={page === 0} onClick={() => setPage((current) => current - 1)}>{t('Anterior', 'Previous')}</button>
          <button className="button secondary" type="button" disabled={end === visible.length} onClick={() => setPage((current) => current + 1)}>{t('Siguiente', 'Next')}</button>
        </div>}
      </>}
      <dl>
        {[['nom', 'NOM', 'NOM'], ['national_notes', 'Notas Nacionales', 'National Notes']].map(([key, es, en]) => {
          const result = state.report.auxiliary?.[key];
          return <div key={key}><dt>{t(es, en)}</dt><dd>{result?.status === 'compared' && Array.isArray(result.changes)
            ? `${result.changes.length} ${t('cambios', 'changes')}`
            : t('Comparación no disponible', 'Comparison unavailable')}</dd></div>;
        })}
      </dl>
      <p><a href={`${base}/${state.path}`}>{t('Abrir reporte JSON', 'Open JSON report')}</a></p>
    </>}
  </section>;
}
