import { useMemo, useState } from 'react';

import { EDITORIAL_PAGES, OFFICIAL_LINKS } from './content.js';
import { GLOSSARY_ENTRIES } from './glossary-data.js';
import { filterGlossary, glossaryLetter } from './glossary.js';

const LETTERS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ'.split('');

function External({ href, children }) {
  return <a href={href} target="_blank" rel="noreferrer">{children} <span aria-hidden="true">↗</span></a>;
}

function GlossaryHero() {
  const page = EDITORIAL_PAGES['/glossary'];
  return <section className="page-hero"><p className="eyebrow">{page.eyebrow}</p><h1>{page.title}</h1><p>{page.description}</p><External href={OFFICIAL_LINKS.anamGlossary}>Abrir glosario ANAM</External><p className="disclaimer">{page.disclaimer}</p></section>;
}

function GlossaryCard({ category, term, definition }) {
  const [expanded, setExpanded] = useState(false);
  const long = definition.length > 260;
  return <article><span>{category}</span><h2>{term}</h2><p className={long && !expanded ? 'is-clamped' : undefined}>{definition}</p>{long && <button className="text-button" type="button" aria-expanded={expanded} onClick={() => setExpanded((current) => !current)}>{expanded ? 'Ver menos' : 'Ver definición completa'}</button>}<External href={OFFICIAL_LINKS.anamGlossary}>Fuente oficial</External></article>;
}

export default function GlossaryPage() {
  const [query, setQuery] = useState('');
  const [filter, setFilter] = useState('Todas');
  const [letter, setLetter] = useState('');
  const available = useMemo(() => new Set(filterGlossary(GLOSSARY_ENTRIES, query, filter).map(({ term }) => glossaryLetter(term))), [filter, query]);
  const activeLetter = available.has(letter) ? letter : '';
  const entries = useMemo(() => filterGlossary(GLOSSARY_ENTRIES, query, filter, activeLetter), [activeLetter, filter, query]);
  const letters = available.has('#') ? ['#', ...LETTERS] : LETTERS;

  return <><GlossaryHero/><section className="workspace"><label htmlFor="glossary-query">Buscar en el glosario ANAM</label><input id="glossary-query" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Buscar término o definición"/><div className="filter-group" aria-label="Tipo de entrada">{['Todas', 'Siglas', 'Términos'].map((item) => <button className="button" aria-pressed={filter === item} onClick={() => setFilter(item)} key={item}>{item}</button>)}</div><nav className="letter-rail" aria-label="Índice alfabético"><button className="button" type="button" aria-pressed={!activeLetter} onClick={() => setLetter('')}>Todas las letras</button>{letters.map((item) => <button className="button" type="button" key={item} disabled={!available.has(item)} aria-pressed={activeLetter === item} onClick={() => setLetter(item)}>{item}</button>)}</nav><p role="status" aria-live="polite">{entries.length} de {GLOSSARY_ENTRIES.length} entradas oficiales</p>{entries.length ? <section className="card-grid" data-testid="anam-glossary-results">{entries.map((entry) => <GlossaryCard key={entry.term} {...entry}/>)}</section> : <aside className="empty-state"><h2>No glossary entries match “{query}”.</h2><button className="button" onClick={() => setQuery('')}>Clear search</button></aside>}</section></>;
}