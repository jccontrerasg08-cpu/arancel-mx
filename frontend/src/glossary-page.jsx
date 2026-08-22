import { useMemo, useState } from 'react';

import { EDITORIAL_PAGES, OFFICIAL_LINKS } from './content.js';
import { GLOSSARY_ENTRIES } from './glossary-data.js';
import { filterGlossary } from './glossary.js';

function External({ href, children }) {
  return <a href={href} target="_blank" rel="noreferrer">{children} <span aria-hidden="true">↗</span></a>;
}

function GlossaryHero() {
  const page = EDITORIAL_PAGES['/glossary'];
  return <section className="page-hero"><p className="eyebrow">{page.eyebrow}</p><h1>{page.title}</h1><p>{page.description}</p><External href={OFFICIAL_LINKS.anamGlossary}>Abrir glosario ANAM</External><p className="disclaimer">{page.disclaimer}</p></section>;
}

export default function GlossaryPage() {
  const [query, setQuery] = useState('');
  const [filter, setFilter] = useState('Todas');
  const entries = useMemo(() => filterGlossary(GLOSSARY_ENTRIES, query, filter), [filter, query]);

  return <><GlossaryHero/><section className="workspace"><label htmlFor="glossary-query">Buscar en el glosario ANAM</label><input id="glossary-query" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Buscar término o definición"/><div className="filter-group" aria-label="Tipo de entrada">{['Todas', 'Siglas', 'Términos'].map((item) => <button className="button" aria-pressed={filter === item} onClick={() => setFilter(item)} key={item}>{item}</button>)}</div><p role="status" aria-live="polite">{entries.length} de {GLOSSARY_ENTRIES.length} entradas oficiales</p>{entries.length ? <section className="card-grid" data-testid="anam-glossary-results">{entries.map(({ category, term, definition }) => <article key={term}><span>{category}</span><h2>{term}</h2><p>{definition}</p><External href={OFFICIAL_LINKS.anamGlossary}>Fuente oficial</External></article>)}</section> : <aside className="empty-state"><h2>No glossary entries match “{query}”.</h2><button className="button" onClick={() => setQuery('')}>Clear search</button></aside>}</section></>;
}
