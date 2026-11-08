import { useState } from 'react';
import { Link } from 'react-router-dom';

import { OFFICIAL_LINKS } from './content.js';
import { useLocale } from './locale.jsx';

const SNICE_LIGIE = 'https://www.snice.gob.mx/cs/avi/snice/ligie.info22.html';
const LIGIE_TEXT = 'https://www.diputados.gob.mx/LeyesBiblio/pdf/LIGIE_2022.pdf';

// The five levels of a Mexican tariff code, read left to right. The facts come from the LIGIE text
// (DOF 2022-06-07) and from the SNICE page "LIGIE: Acerca de".
const LEVELS = [
  { digits: '85', size: 2, es: ['Capítulo', 'Agrupa las mercancías por su naturaleza. El 85 reúne las máquinas, aparatos y material eléctrico.'], en: ['Chapter', 'Groups goods by their nature. Chapter 85 holds electrical machinery, apparatus and equipment.'] },
  { digits: '17', size: 4, es: ['Partida', 'Cuatro dígitos. La 85.17 es la de teléfonos, incluidos los teléfonos inteligentes, y otros aparatos de comunicación.'], en: ['Heading', 'Four digits. Heading 85.17 covers telephones, smartphones included, and other communication apparatus.'] },
  { digits: '13', size: 6, es: ['Subpartida', 'Seis dígitos: el nivel del Sistema Armonizado, la nomenclatura internacional que comparten los países. La 85.17.13 son los teléfonos inteligentes.'], en: ['Subheading', 'Six digits: the Harmonized System level, the international nomenclature countries share. 85.17.13 is smartphones.'] },
  { digits: '01', size: 8, es: ['Fracción arancelaria', 'Ocho dígitos: el nivel propio de México, donde la Tarifa fija el IGI y el IGE de la mercancía.'], en: ['Tariff fraction', 'Eight digits: Mexico’s own level, where the Tariff sets the import (IGI) and export (IGE) rates.'] },
  { digits: 'NN', size: 10, es: ['NICO', 'Diez dígitos: el número de identificación comercial que publica la Secretaría de Economía para afinar la fracción. Aquí se muestra como NN porque cambia con cada fracción.'], en: ['NICO', 'Ten digits: the trade identification number the Ministry of Economy publishes to refine a fraction. Shown as NN because it differs for each fraction.'] },
];

function CodeAnatomy({ t, language }) {
  const [active, setActive] = useState(0);
  const level = LEVELS[active][language === 'en' ? 'en' : 'es'];
  return (
    <section className="learn-anatomy" aria-labelledby="learn-anatomy-title">
      <h2 id="learn-anatomy-title">{t('Cómo se lee un código', 'How to read a code')}</h2>
      <p>{t('Cada par de dígitos añade precisión. Elige una parte del código de ejemplo 8517.13.01 para ver qué significa.', 'Each pair of digits adds precision. Pick a part of the example code 8517.13.01 to see what it means.')}</p>
      <div className="learn-code" role="group" aria-label={t('Partes del código', 'Parts of the code')}>
        {LEVELS.map((entry, index) => (
          <button key={entry.size} type="button" className={index === active ? 'learn-code__part is-active' : 'learn-code__part'} aria-pressed={index === active} onClick={() => setActive(index)}>
            <strong>{entry.digits}</strong>
            <span>{entry[language === 'en' ? 'en' : 'es'][0]}</span>
          </button>
        ))}
      </div>
      <p className="learn-code__detail" role="status" aria-live="polite"><strong>{level[0]} · {LEVELS[active].size} {t('dígitos', 'digits')}.</strong> {level[1]}</p>
    </section>
  );
}

export default function LearnPage() {
  const { language } = useLocale();
  const t = (spanish, english) => (language === 'en' ? english : spanish);
  const paths = [
    [t('Glosario', 'Glossary'), t('Siglas y definiciones de ANAM, con su atribución.', 'Acronyms and definitions from ANAM, with attribution.'), '/glossary'],
    [t('Guía MOA', 'MOA guide'), t('Un mapa de lectura del Manual de Operación Aduanera.', 'A reading map of the Customs Operation Manual.'), '/moa'],
    [t('Wiki de normatividad', 'Regulation wiki'), t('Los instrumentos oficiales, agrupados por quien los emite.', 'Official instruments, grouped by their issuer.'), '/wiki'],
    [t('Contexto comercial', 'Trade context'), t('Importaciones, exportaciones y balanza: series oficiales del INEGI.', 'Imports, exports and balance: official INEGI series.'), '/trade-context'],
    [t('Cifras del arancel', 'Tariff figures'), t('Cuántas fracciones tiene cada capítulo y datos curiosos.', 'How many fractions each chapter has, plus fun facts.'), '/data'],
    [t('Cambios en el DOF', 'DOF changes'), t('Cada decreto que modificó la Tarifa, con su fecha y sus fracciones.', 'Every decree that changed the Tariff, with its date and fractions.'), '/changes'],
    [t('Estimador de importación', 'Import estimator'), t('Aritmética sobre valores y tasas que tú declaras.', 'Arithmetic on values and rates you declare.'), '/trade'],
  ];
  const concepts = [
    [t('¿Qué es la LIGIE y qué es la TIGIE?', 'What are the LIGIE and the TIGIE?'), t('La Ley de los Impuestos Generales de Importación y de Exportación (LIGIE) tiene dos artículos: el primero define la Tarifa, conocida como TIGIE, y el segundo fija las Reglas Generales y Complementarias para interpretarla. La vigente se publicó en el DOF el 7 de junio de 2022 y entró en vigor el 12 de diciembre de 2022, con lo que abrogó la de 2020.', 'The General Import and Export Tax Law (LIGIE) has two articles: the first defines the Tariff, known as TIGIE, and the second sets the General and Complementary Rules to interpret it. The current one was published in the DOF on 7 June 2022 and took effect on 12 December 2022, repealing the 2020 law.')],
    [t('¿Qué es el Sistema Armonizado?', 'What is the Harmonized System?'), t('Es la nomenclatura internacional de seis dígitos con la que se clasifican las mercancías en casi todo el mundo. La Organización Mundial de Aduanas la revisa cada cinco años en promedio; la LIGIE de 2022 aplica la séptima enmienda, vigente desde el 1 de enero de 2022.', 'It is the six-digit international nomenclature used to classify goods almost everywhere. The World Customs Organization reviews it about every five years; the 2022 LIGIE applies the seventh amendment, in force since 1 January 2022.')],
    [t('¿Qué significan IGI, IGE y “Ex.”?', 'What do IGI, IGE and “Ex.” mean?'), t('IGI es el Impuesto General de Importación e IGE el de Exportación; la Tarifa los expresa como porcentaje por fracción. “Ex.” indica que la mercancía está exenta.', 'IGI is the General Import Tax and IGE the General Export Tax; the Tariff states them as a percentage per fraction. “Ex.” means the good is exempt.')],
    [t('¿Cómo se decide en qué partida va una mercancía?', 'How is the heading of a good decided?'), t('Con las Reglas Generales de interpretación. La primera establece que los títulos de Secciones y Capítulos solo son indicativos: la clasificación la determinan los textos de las partidas y las Notas de Sección o de Capítulo. Este sitio no clasifica mercancías.', 'With the General Rules of interpretation. The first says that Section and Chapter titles are indicative only: classification is set by the heading texts and the Section or Chapter Notes. This site does not classify goods.')],
    [t('¿Qué son las Notas Nacionales y los NICO?', 'What are the National Notes and the NICO?'), t('La Secretaría de Economía publica en el DOF los números de identificación comercial (NICO), sus tablas de correlación y las Notas Nacionales, que se suman a las notas de la Tarifa.', 'The Ministry of Economy publishes in the DOF the trade identification numbers (NICO), their correlation tables and the National Notes, which add to the Tariff’s own notes.')],
    [t('¿Por qué cambia una tasa?', 'Why does a rate change?'), t('Porque un decreto publicado en el DOF modifica la Tarifa, crea un programa sectorial o fija un arancel-cupo. La página de cambios lista cada publicación con su fecha y el documento oficial.', 'Because a decree published in the DOF changes the Tariff, creates a sector program or sets a tariff-rate quota. The changes page lists each publication with its date and the official document.')],
  ];
  const sources = [
    [t('LIGIE: Acerca de (SNICE, Secretaría de Economía)', 'LIGIE: About (SNICE, Ministry of Economy)'), SNICE_LIGIE],
    [t('Texto de la LIGIE (Cámara de Diputados)', 'LIGIE text (Chamber of Deputies)'), LIGIE_TEXT],
    [t('Manual de Operación Aduanera (ANAM)', 'Customs Operation Manual (ANAM)'), OFFICIAL_LINKS.anamMoa],
    [t('Comercio exterior (INEGI Cuéntame)', 'Foreign trade (INEGI Cuéntame)'), OFFICIAL_LINKS.inegi],
  ];
  return (
    <>
      <section className="page-hero">
        <p className="eyebrow">{t('APRENDER · GUÍA PARA EMPEZAR', 'LEARN · START HERE')}</p>
        <h1>{t('Aprende a leer el arancel de México.', 'Learn to read Mexico’s tariff.')}</h1>
        <p>{t('De qué está hecho un código, qué ley lo define y dónde seguir leyendo, con la fuente oficial a la vista.', 'What a code is made of, which law defines it and where to keep reading, with the official source in view.')}</p>
        <div className="hero-actions"><Link className="button primary" to="/app">{t('Buscar una fracción', 'Search a fraction')}</Link><Link className="button" to="/glossary">{t('Ver el glosario', 'Open the glossary')}</Link></div>
        <p className="disclaimer">{t('Es material educativo: no clasifica mercancías ni sustituye la consulta a la autoridad.', 'This is educational material: it does not classify goods or replace asking the authority.')}</p>
      </section>
      <CodeAnatomy t={t} language={language} />
      <section aria-labelledby="learn-concepts-title">
        <h2 id="learn-concepts-title">{t('Conceptos clave', 'Key concepts')}</h2>
        <div className="learn-faq">
          {concepts.map(([question, answer]) => <details key={question}><summary>{question}</summary><p>{answer}</p></details>)}
        </div>
      </section>
      <section aria-labelledby="learn-paths-title">
        <h2 id="learn-paths-title">{t('Sigue aprendiendo', 'Keep learning')}</h2>
        <div className="card-grid learn-paths">
          {paths.map(([title, summary, href]) => <article key={href}><h3>{title}</h3><p>{summary}</p>{href === '/trade' ? <a href={href}>{t('Abrir', 'Open')}</a> : <Link to={href}>{t('Abrir', 'Open')}</Link>}</article>)}
        </div>
      </section>
      <section className="source-strip" aria-labelledby="learn-sources-title">
        <h2 id="learn-sources-title">{t('Fuentes oficiales', 'Official sources')}</h2>
        <ul>{sources.map(([label, href]) => <li key={href}><a href={href} target="_blank" rel="noreferrer">{label} <span aria-hidden="true">↗</span></a></li>)}</ul>
      </section>
    </>
  );
}
