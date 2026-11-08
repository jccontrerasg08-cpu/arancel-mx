import { useEffect, useState } from 'react';

import { buildTradeBalance, parseSeries } from '../../scripts/trade-balance-lib.mjs';
import { useLocale } from './locale.jsx';
import snapshot from './trade-balance.json';
import { formatMillions, formatPercent, summarizeBalance } from './trade-balance.js';

export const LIVE_ENDPOINT = '/api/trade_balance';

// Shows the saved copy at once, then replaces it with figures computed from INEGI's monthly series (through the
// api/trade_balance.py function, which holds the token). If the function is missing or fails, the copy stays.
function useTradeBalance() {
  const [state, setState] = useState({ data: snapshot, live: false });
  useEffect(() => {
    const controller = new AbortController();
    fetch(LIVE_ENDPOINT, { signal: controller.signal, headers: { accept: 'application/json' } })
      .then((response) => (response.ok ? response.json() : Promise.reject(new Error('unavailable'))))
      .then((payload) => setState({ data: { ...snapshot, ...buildTradeBalance(parseSeries(payload), new Date().toISOString().slice(0, 10)) }, live: true }))
      .catch(() => {});
    return () => controller.abort();
  }, []);
  return state;
}

export function TradeBalance() {
  const { data, live } = useTradeBalance();
  const { language } = useLocale();
  const t = (spanish, english) => (language === 'en' ? english : spanish);
  const summary = summarizeBalance(data.years);
  const { first, last, largestSurplus, largestDeficit } = summary;
  const { latest } = data;
  const previousYear = Number(latest.months.at(-1).month.slice(0, 4)) - 1;
  const change = (percent, up, down) => `${percent >= 0 ? up : down} ${Math.abs(percent).toLocaleString(language === 'en' ? 'en-US' : 'es-MX', { maximumFractionDigits: 1 })} %`;
  const nearBalance = Math.abs(last.balance) < last.exports * 0.01;
  const money = (value, options) => formatMillions(value, language, options);
  const facts = [
    largestSurplus && [money(largestSurplus.balance, { sign: true }), t(`El mayor superávit fue en ${largestSurplus.year}, en millones de dólares.`, `The largest surplus was in ${largestSurplus.year}, in millions of dollars.`)],
    largestDeficit && [money(largestDeficit.balance), t(`El mayor déficit fue en ${largestDeficit.year}, en millones de dólares.`, `The largest deficit was in ${largestDeficit.year}, in millions of dollars.`)],
    [money(last.balance, { sign: true }), nearBalance ? t(`En ${last.year} el comercio quedó casi en equilibrio: exportaciones e importaciones, en millones de dólares, apenas se diferenciaron.`, `In ${last.year} trade was almost balanced: exports and imports, in millions of dollars, barely differed.`) : t(`Fue la balanza de ${last.year}, en millones de dólares.`, `That was the ${last.year} balance, in millions of dollars.`)],
    [formatPercent(summary.exportGrowth, language), t(`Es lo que crecieron las exportaciones entre ${first.year} y ${last.year}; las importaciones crecieron ${formatPercent(summary.importGrowth, language)}.`, `That is how much exports grew between ${first.year} and ${last.year}; imports grew ${formatPercent(summary.importGrowth, language)}.`)],
  ].filter(Boolean);
  return (
    <section className="trade-balance" aria-labelledby="trade-balance-title" data-testid="trade-balance" data-live={live ? 'true' : 'false'}>
      <p className="eyebrow">{t('INEGI · BALANZA COMERCIAL DE MERCANCÍAS', 'INEGI · MERCHANDISE TRADE BALANCE')}</p>
      <h2 id="trade-balance-title">{t(`Exportaciones e importaciones, ${first.year}–${last.year}`, `Exports and imports, ${first.year}–${last.year}`)}</h2>
      <p>{t('Cuánto vendió México al exterior, cuánto compró y la diferencia de cada año. Cifras en millones de dólares.', 'How much Mexico sold abroad, how much it bought and the difference each year. Figures in millions of US dollars.')}</p>
      <div className="trade-balance__facts">
        {facts.map(([figure, text]) => <article key={text}><strong>{figure}</strong><p>{text}</p></article>)}
      </div>
      <figure className="trade-balance__chart">
        <figcaption>{t('Exportaciones (verde) e importaciones (ámbar) por año', 'Exports (green) and imports (amber) per year')}</figcaption>
        <div className="trade-balance__bars" aria-hidden="true">
          {data.years.map((entry) => (
            <div key={entry.year} className="trade-balance__year">
              <span className="trade-balance__pair">
                <span className="trade-balance__bar trade-balance__bar--exports" style={{ height: `${(entry.exports / summary.peak) * 100}%` }} />
                <span className="trade-balance__bar trade-balance__bar--imports" style={{ height: `${(entry.imports / summary.peak) * 100}%` }} />
              </span>
              <b>{entry.year}</b>
              <small className={entry.balance >= 0 ? 'is-surplus' : 'is-deficit'}>{money(entry.balance / 1000, { sign: true })}k</small>
            </div>
          ))}
        </div>
      </figure>
      <div className="data-table-wrap">
        <table className="data-table">
          <caption>{t('Balanza comercial anual, millones de dólares', 'Annual trade balance, millions of US dollars')}</caption>
          <thead><tr><th scope="col">{t('Año', 'Year')}</th><th scope="col" className="is-numeric">{t('Exportaciones', 'Exports')}</th><th scope="col" className="is-numeric">{t('Importaciones', 'Imports')}</th><th scope="col" className="is-numeric">{t('Balanza', 'Balance')}</th></tr></thead>
          <tbody>
            {[...data.years].reverse().map((entry) => (
              <tr key={entry.year}>
                <th scope="row">{entry.year}{entry.adjusted ? <sup title={t('Cifras ajustadas', 'Adjusted figures')}> A</sup> : null}</th>
                <td className="is-numeric">{money(entry.exports)}</td>
                <td className="is-numeric">{money(entry.imports)}</td>
                <td className={entry.balance >= 0 ? 'is-numeric is-surplus' : 'is-numeric is-deficit'}>{money(entry.balance, { sign: true })}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <div className="trade-balance__latest" data-testid="trade-balance-latest">
        <h3>{t(latest.label, latest.label_en)} <span>{t(latest.note, 'Preliminary figures')}</span></h3>
        <p>{t(`Lo que va del año: exportaciones ${money(latest.exports)}, importaciones ${money(latest.imports)} y una balanza de ${money(latest.balance, { sign: true })} millones de dólares. Frente al mismo periodo de ${previousYear}, las exportaciones ${change(latest.exports_growth, 'crecieron', 'cayeron')} y las importaciones ${change(latest.imports_growth, 'crecieron', 'cayeron')}.`, `Year to date: exports ${money(latest.exports)}, imports ${money(latest.imports)} and a balance of ${money(latest.balance, { sign: true })} million dollars. Against the same period of ${previousYear}, exports ${change(latest.exports_growth, 'grew', 'fell')} and imports ${change(latest.imports_growth, 'grew', 'fell')}.`)}</p>
        <div className="data-table-wrap">
          <table className="data-table">
            <caption>{t('Últimos meses publicados, millones de dólares', 'Latest published months, millions of US dollars')}</caption>
            <thead><tr><th scope="col">{t('Mes', 'Month')}</th><th scope="col" className="is-numeric">{t('Exportaciones', 'Exports')}</th><th scope="col" className="is-numeric">{t('Importaciones', 'Imports')}</th><th scope="col" className="is-numeric">{t('Balanza', 'Balance')}</th></tr></thead>
            <tbody>
              {[...latest.months].reverse().map((entry) => (
                <tr key={entry.month}>
                  <th scope="row">{new Date(`${entry.month}-15T12:00:00Z`).toLocaleDateString(language === 'en' ? 'en-US' : 'es-MX', { month: 'long', year: 'numeric', timeZone: 'UTC' })}</th>
                  <td className="is-numeric">{money(entry.exports)}</td>
                  <td className="is-numeric">{money(entry.imports)}</td>
                  <td className={entry.balance >= 0 ? 'is-numeric is-surplus' : 'is-numeric is-deficit'}>{money(entry.balance, { sign: true })}</td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="trade-balance__source">{live ? t('Datos en vivo de la API del INEGI, consultados el ', 'Live data from the INEGI API, retrieved on ') : t('Copia guardada de la API del INEGI del ', 'Saved copy of the INEGI API data from ')}<time dateTime={latest.retrieved}>{new Date(`${latest.retrieved}T12:00:00Z`).toLocaleDateString(language === 'en' ? 'en-US' : 'es-MX', { day: 'numeric', month: 'long', year: 'numeric', timeZone: 'UTC' })}</time>. <a href={latest.source_url} target="_blank" rel="noreferrer">{t('Ver en INEGI', 'View at INEGI')} <span aria-hidden="true">↗</span></a></p>
      </div>
      <p className="trade-balance__source">{t('Fuente: ', 'Source: ')}<a href={data.source_url} target="_blank" rel="noreferrer">{data.source} <span aria-hidden="true">↗</span></a>. {t('A = cifras ajustadas por INEGI. Una balanza positiva es superávit; negativa, déficit. Es contexto histórico y no determina una fracción ni una operación.', 'A = figures adjusted by INEGI. A positive balance is a surplus; a negative one, a deficit. This is historical context and does not determine a fraction or an operation.')}</p>
    </section>
  );
}
