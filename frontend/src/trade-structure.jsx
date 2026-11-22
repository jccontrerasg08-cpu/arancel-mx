import { Link } from 'react-router-dom';

import { useLocale } from './locale.jsx';
import structure from './trade-structure.json';
import { formatMillions, partShares } from './trade-balance.js';

// What Mexico sells and buys, by kind of good (INEGI BCMM, year to date). Each bar is one hundred percent of the flow.
function Bar({ title, parts, total, language, tones }) {
  const shares = partShares(parts, total);
  const percent = (value) => value.toLocaleString(language === 'en' ? 'en-US' : 'es-MX', { minimumFractionDigits: 1, maximumFractionDigits: 1 });
  return (
    <figure className="trade-structure__bar">
      <figcaption>{title} <span>{formatMillions(total, language)} {language === 'en' ? 'M USD' : 'mdd'}</span></figcaption>
      <div className="trade-structure__strip" role="img" aria-label={shares.map((part) => `${language === 'en' ? part.en : part.es}: ${percent(part.share)} %`).join('; ')}>
        {shares.map((part, index) => <span key={part.key} className={`trade-structure__segment trade-structure__segment--${tones[index]}`} style={{ flexGrow: part.share }}>{part.share >= 6 ? `${percent(part.share)} %` : ''}</span>)}
      </div>
      <ul className="trade-structure__legend">
        {shares.map((part, index) => <li key={part.key}><i className={`trade-structure__swatch trade-structure__segment--${tones[index]}`} />{language === 'en' ? part.en : part.es} <b>{percent(part.share)} %</b> <small>{formatMillions(part.value, language)}</small></li>)}
      </ul>
    </figure>
  );
}

export function TradeStructure() {
  const { language } = useLocale();
  const t = (spanish, english) => (language === 'en' ? english : spanish);
  const exportShares = partShares(structure.exports.parts, structure.exports.total);
  const importShares = partShares(structure.imports.parts, structure.imports.total);
  const manufacturing = exportShares.find((part) => part.key === 'manufacturing').share;
  const intermediate = importShares.find((part) => part.key === 'intermediate').share;
  const round = (value) => value.toLocaleString(language === 'en' ? 'en-US' : 'es-MX', { maximumFractionDigits: 0 });
  return (
    <section className="trade-structure" aria-labelledby="trade-structure-title" data-testid="trade-structure">
      <p className="eyebrow">{t('INEGI · QUÉ SE VENDE Y QUÉ SE COMPRA', 'INEGI · WHAT IS SOLD AND WHAT IS BOUGHT')}</p>
      <h2 id="trade-structure-title">{t('Las importaciones son sobre todo insumos; las exportaciones, manufacturas', 'Imports are mostly inputs; exports are manufactured goods')}</h2>
      <p className="trade-balance__headline">{t(`${round(intermediate)} de cada 100 dólares que México importa son bienes de uso intermedio, es decir, piezas e insumos que se transforman en el país. ${round(manufacturing)} de cada 100 dólares que exporta son manufacturas.`, `${round(intermediate)} of every 100 dollars Mexico imports are intermediate goods, that is, parts and inputs transformed in the country. ${round(manufacturing)} of every 100 dollars it exports are manufactured goods.`)}</p>
      <p>{t('Por eso el arancel de un insumo importa: lo que se paga al importar una pieza forma parte del costo de lo que luego se exporta. Busca la fracción de tu insumo en el explorador para ver su arancel.', 'That is why the tariff on an input matters: what is paid to import a part becomes part of the cost of what is later exported. Look up your input’s fraction in the explorer to see its tariff.')}</p>
      <div className="trade-structure__grid">
        <Bar title={t('Exportaciones por tipo', 'Exports by type')} parts={structure.exports.parts} total={structure.exports.total} language={language} tones={['brand', 'soft', 'accent', 'mute']} />
        <Bar title={t('Importaciones por tipo de bien', 'Imports by kind of good')} parts={structure.imports.parts} total={structure.imports.total} language={language} tones={['accent', 'soft', 'brand']} />
      </div>
      <p className="trade-balance__source">{t('Periodo: ', 'Period: ')}{t(structure.period, structure.period_en)}. {t('Cifras oportunas, en millones de dólares. ', 'Preliminary figures, in millions of US dollars. ')}<Link to="/app">{t('Buscar una fracción', 'Look up a fraction')} →</Link> · {t('Fuente: ', 'Source: ')}<a href={structure.source_url} target="_blank" rel="noreferrer">{structure.source} <span aria-hidden="true">↗</span></a>. {t('Contexto histórico: no determina una fracción ni una operación.', 'Historical context: it does not determine a fraction or an operation.')}</p>
    </section>
  );
}
