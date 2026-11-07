import data from './trade-balance.json';
import { useLocale } from './locale.jsx';
import { formatMillions, formatPercent, summarizeBalance } from './trade-balance.js';

export function TradeBalance() {
  const { language } = useLocale();
  const t = (spanish, english) => (language === 'en' ? english : spanish);
  const summary = summarizeBalance(data.years);
  const { first, last, largestSurplus, largestDeficit } = summary;
  const nearBalance = Math.abs(last.balance) < last.exports * 0.01;
  const money = (value, options) => formatMillions(value, language, options);
  const facts = [
    largestSurplus && [money(largestSurplus.balance, { sign: true }), t(`El mayor superávit fue en ${largestSurplus.year}, en millones de dólares.`, `The largest surplus was in ${largestSurplus.year}, in millions of dollars.`)],
    largestDeficit && [money(largestDeficit.balance), t(`El mayor déficit fue en ${largestDeficit.year}, en millones de dólares.`, `The largest deficit was in ${largestDeficit.year}, in millions of dollars.`)],
    [money(last.balance, { sign: true }), nearBalance ? t(`En ${last.year} el comercio quedó casi en equilibrio: exportaciones e importaciones, en millones de dólares, apenas se diferenciaron.`, `In ${last.year} trade was almost balanced: exports and imports, in millions of dollars, barely differed.`) : t(`Fue la balanza de ${last.year}, en millones de dólares.`, `That was the ${last.year} balance, in millions of dollars.`)],
    [formatPercent(summary.exportGrowth, language), t(`Es lo que crecieron las exportaciones entre ${first.year} y ${last.year}; las importaciones crecieron ${formatPercent(summary.importGrowth, language)}.`, `That is how much exports grew between ${first.year} and ${last.year}; imports grew ${formatPercent(summary.importGrowth, language)}.`)],
  ].filter(Boolean);
  return (
    <section className="trade-balance" aria-labelledby="trade-balance-title" data-testid="trade-balance">
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
      <p className="trade-balance__source">{t('Fuente: ', 'Source: ')}<a href={data.source_url} target="_blank" rel="noreferrer">{data.source} <span aria-hidden="true">↗</span></a>. {t('A = cifras ajustadas por INEGI. Una balanza positiva es superávit; negativa, déficit. Es contexto histórico y no determina una fracción ni una operación.', 'A = figures adjusted by INEGI. A positive balance is a surplus; a negative one, a deficit. This is historical context and does not determine a fraction or an operation.')}</p>
    </section>
  );
}
