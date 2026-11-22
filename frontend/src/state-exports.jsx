import { useState } from 'react';

import { useLocale } from './locale.jsx';
import data from './state-exports.json';
import geometry from './state-map.json';
import { formatChange, formatMillions, tileIntensity, topConcentration } from './trade-balance.js';

const MODES = ['share', 'perPerson', 'change'];
const byKey = new Map(geometry.states.map((shape) => [shape.cve_ent, shape]));
// Quarterly exports (millions of dollars) over the 2020 census population: dollars per inhabitant in that quarter.
export const perPerson = (state) => (state.millions * 1_000_000) / byKey.get(state.cve_ent).population;

// The real outline of each state, shaded by the chosen measure. Every state is a focusable button; the table below
// holds every figure for anyone who cannot use the map.
export function StateExports() {
  const { language } = useLocale();
  const t = (spanish, english) => (language === 'en' ? english : spanish);
  const [mode, setMode] = useState('share');
  const [selected, setSelected] = useState(null);
  const states = data.states;
  const { top, share: topShare } = topConcentration(states, 5, data.total_millions);
  const locale = language === 'en' ? 'en-US' : 'es-MX';
  const pct = (value) => value.toLocaleString(locale, { minimumFractionDigits: 1, maximumFractionDigits: 1 });
  const dollars = (value) => `$${Math.round(value).toLocaleString(locale)}`;
  const active = states.find((state) => state.cve_ent === selected) ?? top[0];
  const growing = [...states].sort((a, b) => b.yoy - a.yoy)[0];
  const maxima = { share: Math.max(...states.map((state) => state.share)), perPerson: Math.max(...states.map(perPerson)), change: Math.max(...states.map((state) => Math.abs(state.yoy)), 1) };
  const measure = (state) => (mode === 'share' ? state.share : mode === 'perPerson' ? perPerson(state) : Math.abs(state.yoy));
  const label = (state) => (mode === 'share' ? `${pct(state.share)} %` : mode === 'perPerson' ? `${dollars(perPerson(state))} ${t('por habitante', 'per person')}` : formatChange(state.yoy / 100, language));
  const modeNames = { share: t('Participación', 'Share'), perPerson: t('Por habitante', 'Per person'), change: t('Cambio anual', 'Yearly change') };
  return (
    <section className="state-exports" aria-labelledby="state-exports-title" data-testid="state-exports">
      <p className="eyebrow">{t('INEGI · EXPORTACIONES POR ENTIDAD FEDERATIVA', 'INEGI · EXPORTS BY STATE')}</p>
      <h2 id="state-exports-title">{t(`${top.length} estados venden ${pct(topShare)} % de lo que exporta México`, `${top.length} states sell ${pct(topShare)}% of what Mexico exports`)}</h2>
      <p className="trade-balance__headline">{t(`${top.map((state) => state.name).join(', ')}. Solo Chihuahua aporta ${pct(top[0].share)} % del total.`, `${top.map((state) => state.name).join(', ')}. Chihuahua alone accounts for ${pct(top[0].share)}% of the total.`)}</p>
      <p>{t(`Origen de las exportaciones en el ${data.period}. Elige qué medir y toca un estado para ver su cifra; entre más oscuro, mayor el valor.`, `Origin of exports in ${data.period_en}. Pick what to measure and select a state to see its figure; the darker, the higher.`)}</p>
      <div className="state-modes" role="group" aria-label={t('Qué mide el mapa', 'What the map measures')}>
        {MODES.map((key) => <button key={key} type="button" className="state-modes__button" aria-pressed={mode === key} onClick={() => setMode(key)}>{modeNames[key]}</button>)}
      </div>
      <div className="state-exports__layout">
        <svg className="state-map" viewBox={`0 0 ${geometry.width} ${geometry.height}`} role="group" aria-label={t('Mapa de México por estado', 'Map of Mexico by state')}>
          {geometry.states.map((shape) => {
            const state = states.find((item) => item.cve_ent === shape.cve_ent);
            const ratio = tileIntensity(measure(state), maxima[mode]);
            const down = mode === 'change' && state.yoy < 0;
            return (
              <path key={shape.cve_ent} d={shape.d} className={`state-shape${down ? ' is-down' : ''}${active.cve_ent === shape.cve_ent ? ' is-active' : ''}`} style={{ '--tile': ratio.toFixed(3) }} role="button" tabIndex={0} aria-pressed={active.cve_ent === shape.cve_ent} aria-label={`${state.name}: ${label(state)}`} onClick={() => setSelected(shape.cve_ent)} onKeyDown={(event) => { if (event.key === 'Enter' || event.key === ' ') { event.preventDefault(); setSelected(shape.cve_ent); } }}>
                <title>{`${state.name}: ${label(state)}`}</title>
              </path>
            );
          })}
        </svg>
        <aside className="state-card" aria-live="polite">
          <h3>{active.name}</h3>
          <strong>{formatMillions(active.millions, language)} <small>{t('millones de dólares', 'million dollars')}</small></strong>
          <p>{t(`${pct(active.share)} % del total nacional; lugar ${active.rank} de 32.`, `${pct(active.share)}% of the national total; rank ${active.rank} of 32.`)}</p>
          <p>{t(`${dollars(perPerson(active))} por habitante en el trimestre.`, `${dollars(perPerson(active))} per person in the quarter.`)}</p>
          <p className={active.yoy >= 0 ? 'is-surplus' : 'is-deficit'}>{formatChange(active.yoy / 100, language)} {t('frente al mismo trimestre del año anterior', 'against the same quarter a year earlier')}</p>
          <p className="state-card__hint">{t(`Mayor alza anual del trimestre: ${growing.name} (${formatChange(growing.yoy / 100, language)}).`, `Largest yearly rise this quarter: ${growing.name} (${formatChange(growing.yoy / 100, language)}).`)}</p>
        </aside>
      </div>
      <details className="state-exports__table">
        <summary>{t('Ver la tabla de los 32 estados', 'See the table of all 32 states')}</summary>
        <div className="data-table-wrap">
          <table className="data-table">
            <caption>{t(`Exportaciones por entidad federativa, ${data.period}, millones de dólares`, `Exports by state, ${data.period_en}, millions of US dollars`)}</caption>
            <thead><tr><th scope="col">{t('Lugar', 'Rank')}</th><th scope="col">{t('Estado', 'State')}</th><th scope="col" className="is-numeric">{t('Millones de dólares', 'Million dollars')}</th><th scope="col" className="is-numeric">{t('Participación', 'Share')}</th><th scope="col" className="is-numeric">{t('Por habitante', 'Per person')}</th><th scope="col" className="is-numeric">{t('Var. anual', 'Yearly chg.')}</th></tr></thead>
            <tbody>
              {[...states].sort((a, b) => a.rank - b.rank).map((state) => (
                <tr key={state.cve_ent}>
                  <td>{state.rank}</td>
                  <th scope="row">{state.name}</th>
                  <td className="is-numeric">{formatMillions(state.millions, language)}</td>
                  <td className="is-numeric">{pct(state.share)} %</td>
                  <td className="is-numeric">{dollars(perPerson(state))}</td>
                  <td className={state.yoy >= 0 ? 'is-numeric is-surplus' : 'is-numeric is-deficit'}>{formatChange(state.yoy / 100, language)}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </details>
      <p className="trade-balance__source">{t('Fuente: ', 'Source: ')}<a href={data.source_url} target="_blank" rel="noreferrer">{data.source} <span aria-hidden="true">↗</span></a>. {t('Publicado el 30 de septiembre de 2026; cifras preliminares. ', 'Published on 30 September 2026; preliminary figures. ')}{t(data.note, 'The total differs from the Merchandise Trade Balance: ETEF leaves out trade and services and operations not linked to the RENEM business register.')} {t(`${geometry.source}, simplificado para esta página. Población: ${geometry.population_source}. «Por habitante» divide las exportaciones del trimestre entre la población del censo de 2020; es un cálculo de este sitio, no una cifra del INEGI.`, `Outlines: ${geometry.source}, simplified for this page. Population: ${geometry.population_source}. “Per person” divides the quarter’s exports by the 2020 census population; it is this site’s calculation, not an INEGI figure.`)} <a href={data.programme_url} target="_blank" rel="noreferrer">{t('Ver el programa', 'See the programme')} <span aria-hidden="true">↗</span></a></p>
    </section>
  );
}
