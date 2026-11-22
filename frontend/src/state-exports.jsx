import { useState } from 'react';

import { useLocale } from './locale.jsx';
import data from './state-exports.json';
import { formatChange, formatMillions, tileIntensity, topConcentration } from './trade-balance.js';

// A tile map: one square per state, placed roughly where the state is, shaded by its share of national exports.
// Equal squares keep Colima or Mexico City as visible as Chihuahua; the table below holds every number.
export function StateExports() {
  const { language } = useLocale();
  const t = (spanish, english) => (language === 'en' ? english : spanish);
  const [selected, setSelected] = useState(null);
  const states = data.states;
  const maxShare = Math.max(...states.map((state) => state.share));
  const { top, share: topShare } = topConcentration(states, 5, data.total_millions);
  const columns = Math.max(...states.map((state) => state.col)) + 1;
  const pct = (value) => value.toLocaleString(language === 'en' ? 'en-US' : 'es-MX', { minimumFractionDigits: 1, maximumFractionDigits: 1 });
  const active = states.find((state) => state.cve_ent === selected) ?? top[0];
  const growing = [...states].sort((a, b) => b.yoy - a.yoy)[0];
  return (
    <section className="state-exports" aria-labelledby="state-exports-title" data-testid="state-exports">
      <p className="eyebrow">{t('INEGI · EXPORTACIONES POR ENTIDAD FEDERATIVA', 'INEGI · EXPORTS BY STATE')}</p>
      <h2 id="state-exports-title">{t(`${top.length} estados venden ${pct(topShare)} % de lo que exporta México`, `${top.length} states sell ${pct(topShare)}% of what Mexico exports`)}</h2>
      <p className="trade-balance__headline">{t(`${top.map((state) => state.name).join(', ')}. Solo Chihuahua aporta ${pct(top[0].share)} % del total.`, `${top.map((state) => state.name).join(', ')}. Chihuahua alone accounts for ${pct(top[0].share)}% of the total.`)}</p>
      <p>{t(`Origen de las exportaciones en el ${data.period}. Cada cuadro es un estado; entre más oscuro, mayor su parte del total. Elige un estado para ver su cifra.`, `Origin of exports in ${data.period_en}. Each tile is a state; the darker it is, the larger its share of the total. Pick a state to see its figure.`)}</p>
      <div className="state-exports__layout">
        <ol className="state-grid" style={{ gridTemplateColumns: `repeat(${columns}, minmax(0, 1fr))` }} aria-label={t('Mapa de cuadros de México por estado', 'Tile map of Mexico by state')}>
          {states.map((state) => (
            <li key={state.cve_ent} style={{ gridColumn: state.col + 1, gridRow: state.row + 1 }}>
              <button type="button" className={`state-tile${active.cve_ent === state.cve_ent ? ' is-active' : ''}${tileIntensity(state.share, maxShare) > 0.5 ? ' is-strong' : ''}`} style={{ '--tile': tileIntensity(state.share, maxShare).toFixed(3) }} aria-pressed={active.cve_ent === state.cve_ent} aria-label={`${state.name}: ${pct(state.share)} %`} onClick={() => setSelected(state.cve_ent)}>
                <b>{state.abbr}</b><small>{pct(state.share)}</small>
              </button>
            </li>
          ))}
        </ol>
        <aside className="state-card" aria-live="polite">
          <h3>{active.name}</h3>
          <strong>{formatMillions(active.millions, language)} <small>{t('millones de dólares', 'million dollars')}</small></strong>
          <p>{t(`${pct(active.share)} % del total nacional; lugar ${active.rank} de 32.`, `${pct(active.share)}% of the national total; rank ${active.rank} of 32.`)}</p>
          <p className={active.yoy >= 0 ? 'is-surplus' : 'is-deficit'}>{formatChange(active.yoy / 100, language)} {t('frente al mismo trimestre del año anterior', 'against the same quarter a year earlier')}</p>
          <p className="state-card__hint">{t(`Mayor alza anual del trimestre: ${growing.name} (${formatChange(growing.yoy / 100, language)}).`, `Largest yearly rise this quarter: ${growing.name} (${formatChange(growing.yoy / 100, language)}).`)}</p>
        </aside>
      </div>
      <details className="state-exports__table">
        <summary>{t('Ver la tabla de los 32 estados', 'See the table of all 32 states')}</summary>
        <div className="data-table-wrap">
          <table className="data-table">
            <caption>{t(`Exportaciones por entidad federativa, ${data.period}, millones de dólares`, `Exports by state, ${data.period_en}, millions of US dollars`)}</caption>
            <thead><tr><th scope="col">{t('Lugar', 'Rank')}</th><th scope="col">{t('Estado', 'State')}</th><th scope="col" className="is-numeric">{t('Millones de dólares', 'Million dollars')}</th><th scope="col" className="is-numeric">{t('Participación', 'Share')}</th><th scope="col" className="is-numeric">{t('Var. anual', 'Yearly chg.')}</th></tr></thead>
            <tbody>
              {[...states].sort((a, b) => a.rank - b.rank).map((state) => (
                <tr key={state.cve_ent}>
                  <td>{state.rank}</td>
                  <th scope="row">{state.name}</th>
                  <td className="is-numeric">{formatMillions(state.millions, language)}</td>
                  <td className="is-numeric">{pct(state.share)} %</td>
                  <td className={state.yoy >= 0 ? 'is-numeric is-surplus' : 'is-numeric is-deficit'}>{formatChange(state.yoy / 100, language)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
      <p className="trade-balance__source">{t('Fuente: ', 'Source: ')}<a href={data.source_url} target="_blank" rel="noreferrer">{data.source} <span aria-hidden="true">↗</span></a>. {t('Publicado el 30 de septiembre de 2026; cifras preliminares. ', 'Published on 30 September 2026; preliminary figures. ')}{t(data.note, 'The total differs from the Merchandise Trade Balance: ETEF leaves out trade and services and operations not linked to the RENEM business register.')} {t(data.grid, 'Tile grid drawn for this page: one tile per state, placed roughly where the state is; it is not a map to scale.')} <a href={data.programme_url} target="_blank" rel="noreferrer">{t('Ver el programa', 'See the programme')} <span aria-hidden="true">↗</span></a></p>
    </section>
  );
}
