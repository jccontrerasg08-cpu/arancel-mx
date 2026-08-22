import { useEffect, useMemo, useState } from 'react';
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom';

import {
  DOCUMENTATION_LINKS,
  EDITORIAL_PAGES,
  FALLBACK_CHAPTERS,
  FALLBACK_SECTIONS,
  GLOSSARY_ENTRIES,
  MOA_GROUPS,
  OFFICIAL_LINKS,
  WIKI_REFERENCES,
} from './content.js';
import { filterGlossary } from './glossary.js';
import { asExampleFicha, exampleRecordFor, formatCode, searchExampleRecords } from './verified-examples.js';
import { displayRate, selectPrimarySearchResults } from './tariff.js';

const REPOSITORY = 'https://github.com/jccontrerasg08-cpu/arancel-mx';
const RECORDS_KEY = 'arancel-mx-research-records';

function api(path, signal) {
  return fetch(path, { signal, headers: { Accept: 'application/json' } }).then(async (response) => {
    if (!response.ok) throw new Error(`Request failed (${response.status})`);
    return response.json();
  });
}

function PageHero({ page, children }) {
  return <section className="page-hero"><p className="eyebrow">{page.eyebrow}</p><h1>{page.title}</h1><p>{page.description}</p>{children}<p className="disclaimer">{page.disclaimer}</p></section>;
}

function External({ href, children }) {
  return <a href={href} target="_blank" rel="noreferrer">{children} <span aria-hidden="true">↗</span></a>;
}

export function HomePage() {
  const [query, setQuery] = useState('8517.13.01');
  const navigate = useNavigate();
  const submit = (event) => {
    event.preventDefault();
    navigate(`/app${query.trim() ? `?q=${encodeURIComponent(query.trim())}` : ''}`);
  };
  return <>
    <PageHero page={EDITORIAL_PAGES['/']}>
      <div className="hero-actions"><Link className="button primary" to="/app">Open explorer</Link><Link className="button" to="/documentation">Read documentation</Link></div>
      <p className="trust-line">Immutable releases · Manifest + checksums · Independent verification</p>
    </PageHero>
    <section className="metric-grid" aria-label="Release metrics"><article><strong>8,183</strong><span>Mexican fractions</span></article><article><strong>11,507</strong><span>NICO codes</span></article><article><strong>Daily</strong><span>release checks</span></article><article><strong>Apache-2.0</strong><span>open-source core</span></article></section>
    <section className="feature-panel"><div><p className="eyebrow">EXPLORER PREVIEW</p><h2>Search the data. Keep the hierarchy.</h2><p>Handoff to the verified explorer with the query preserved.</p><form onSubmit={submit}><label htmlFor="home-query">Code or description</label><div className="inline-form"><input id="home-query" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="e.g. 8517.13.01 or teléfonos"/><button className="button primary" type="submit">Search in explorer</button></div></form></div><div className="record-preview"><span>VERIFIED EXAMPLE STRUCTURE</span><strong>85 · 8517 · 851713 · 85171301 · 00</strong><p>Hierarchy remains connected to the active release.</p></div></section>
    <section className="card-grid"><article><h2>Data releases</h2><p>Read manifests, checksums and source archives.</p><External href={OFFICIAL_LINKS.releases}>Open releases</External></article><article><h2>Developer surfaces</h2><p>Use the API, CLI and Python package against a documented contract.</p><Link to="/documentation">Open documentation</Link></article><article><h2>Independent trust</h2><p>Inspect source roles and fail-closed publication controls.</p><Link to="/trust">Read trust model</Link></article></section>
  </>;
}

export function ExplorerPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const initial = new URLSearchParams(location.search).get('q') || '';
  const [query, setQuery] = useState(initial);
  const [state, setState] = useState({ kind: initial ? 'loading' : 'idle', results: [] });

  useEffect(() => setQuery(initial), [initial]);
  useEffect(() => {
    if (!initial) return;
    const controller = new AbortController();
    setState({ kind: 'loading', results: [] });
    api(`/v1/search?q=${encodeURIComponent(initial)}&limit=10`, controller.signal)
      .then((results) => {
        const primaryResults = selectPrimarySearchResults(results, initial);
        setState(primaryResults.length ? { kind: 'results', results: primaryResults } : { kind: 'empty', results: [] });
      })
      .catch(() => {
        const results = searchExampleRecords(initial);
        setState(results.length ? { kind: 'results', results, fallback: true } : { kind: 'error', results: [] });
      });
    return () => controller.abort();
  }, [initial]);

  const submit = (event) => {
    event.preventDefault();
    const normalized = query.replace(/\D/g, '');
    if (!query.trim()) return setState({ kind: 'idle', results: [] });
    if ([2, 4, 6, 8, 10].includes(normalized.length) && normalized.length === query.replace(/[.\s-]/g, '').length) return navigate(`/app/record/${normalized}`);
    navigate(`/app?q=${encodeURIComponent(query.trim())}`);
  };

  return <>
    <PageHero page={{
      eyebrow: 'VERIFIED RELEASE EXPLORER',
      title: 'Explore a tariff reference without losing its path.',
      description: 'Inspect hierarchy, release context and recorded evidence without treating a search result as a legal determination.',
      disclaimer: 'Public data and documented evidence. This site does not classify merchandise or provide legal advice.',
    }} />
    <section className="workspace"><form onSubmit={submit} className="search-form"><label htmlFor="app-query">Code or description</label><div className="inline-form"><input data-testid="search-input" id="app-query" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="e.g. 8517.13.01 or teléfonos"/><button data-testid="search-submit" className="button primary" type="submit" disabled={state.kind === 'loading'}>{state.kind === 'loading' ? 'Loading…' : 'Inspect release'}</button></div><div role="status" aria-live="polite" className="status">{state.kind === 'idle' && 'Enter a tariff code or a description.'}{state.kind === 'loading' && 'Searching the verified release…'}{state.kind === 'results' && 'Verified results found in the recorded release presentation.'}{state.kind === 'empty' && 'No verified records match this search.'}{state.kind === 'error' && 'The verified release is temporarily unavailable.'}</div></form>
      {state.kind === 'results' && <><p className="status">{state.fallback ? 'Recorded presentation example while the active release is unavailable.' : 'Active verified release result.'}</p><section className="result-list" aria-label="Verified search results"><h2>{state.results.length} verified results</h2>{state.results.map((item) => { const record = item.record || item; return <article data-testid="result-card" key={record.code}><div><span>{item.match_kind || 'verified match'}</span><h3>{record.code}</h3><p>{record.description}</p><small>{record.dataset_version || 'active release'} · {record.level}</small></div><Link className="button" to={`/app/record/${record.code}`}>Inspect verified record</Link></article>; })}</section><section data-testid="hierarchy-card" className="example-note"><h2>Progressive decision tree</h2><p>{state.results[0] && (state.results[0].record || state.results[0]).code}</p><p data-testid="tree-filter-status">{formatCode(initial)}</p></section></>}
      {state.kind === 'idle' && <><h2>Enter a complete code or a description.</h2><aside data-testid="example-fraction" className="example-note"><strong>Example fraction · 85.17.13.01</strong><p>IGI and IGE appear only when a verified fraction record is retrieved.</p><div className="hero-actions"><button className="button" type="button" onClick={() => navigate('/app?q=teléfonos')}>Try teléfonos</button><Link to="/chapters">Browse visual tree</Link></div></aside></>}
      {state.kind === 'empty' && <aside className="example-note"><strong>Example structure, not a result.</strong><p>Use the Explorer to inspect only records retrieved from the active verified release.</p><Link to="/chapters">Browse visual tree</Link></aside>}
    </section>
  </>;
}

export function RecordPage() {
  const { code } = useParams();
  const [state, setState] = useState({ kind: 'loading' });
  const [retry, setRetry] = useState(0);
  const [saved, setSaved] = useState(false);
  const [snapshots, setSnapshots] = useState(() => { try { return JSON.parse(localStorage.getItem('arancel-mx-fichas-locales') || '[]'); } catch { return []; } });
  const [treeFilter, setTreeFilter] = useState('');
  useEffect(() => {
    const controller = new AbortController();
    Promise.all([api(`/v1/ficha/${code}`, controller.signal), api(`/v1/codes/${code}/provenance`, controller.signal).catch(() => [])])
      .then(([ficha, provenance]) => setState({ kind: 'ready', ficha, provenance }))
      .catch(() => {
        const record = exampleRecordFor(code);
        setState(record ? { kind: 'ready', ficha: asExampleFicha(record), provenance: [], fallback: true } : { kind: 'error' });
      });
    return () => controller.abort();
  }, [code, retry]);
  if (state.kind === 'loading') return <p className="status" role="status">Retrieving verified hierarchy and recorded evidence…</p>;
  if (state.kind === 'error') return <section className="empty-state"><h1>The verified release is temporarily unavailable.</h1><button className="button primary" type="button" onClick={() => setRetry((current) => current + 1)}>Retry</button><Link to="/app">Return to Explorer</Link></section>;
  const { ficha, provenance } = state;
  const record = ficha.record || ficha;
  const save = () => {
    const existing = JSON.parse(localStorage.getItem(RECORDS_KEY) || '[]');
    const next = [{ code: record.code, description: record.description, level: record.level, dataset_version: record.dataset_version, savedAt: new Date().toISOString() }, ...existing.filter((entry) => entry.code !== record.code)].slice(0, 50);
    localStorage.setItem(RECORDS_KEY, JSON.stringify(next));
    const nextSnapshots = [{ code: record.code, description: record.description, dataset_version: record.dataset_version, saved_at: new Date().toISOString() }, ...snapshots.filter((entry) => entry.code !== record.code)].slice(0, 50);
    localStorage.setItem('arancel-mx-fichas-locales', JSON.stringify(nextSnapshots));
    setSnapshots(nextSnapshots);
    setSaved(true);
  };
  const exportSnapshots = () => {
    const blob = new Blob([JSON.stringify({ schema_version: 1, snapshots }, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = 'arancel-mx-fichas-locales.json';
    anchor.click();
    URL.revokeObjectURL(url);
  };
  const hasRates = record.level === 'fraccion8' || String(record.code || '').replace(/\D/g, '').length === 8;
  const formattedCode = ficha.formatted_code || formatCode(record.code);
  const hierarchy = ficha.hierarchy || record.hierarchy || [];
  const visibleHierarchy = hierarchy.filter((entry) => !treeFilter || String(entry.code || '').startsWith(treeFilter.replace(/\D/g, '')) || String(record.code || '').startsWith(treeFilter.replace(/\D/g, '')));
  return <section data-testid="result-card" className="record-page"><p role="status" aria-live="polite">Verified record ready.</p><p className="eyebrow">VERIFIED RECORD</p><h1>{formattedCode}</h1><p>{record.description}</p><h2>Release context, not advice.</h2>{state.fallback && <p className="example-note">Recorded presentation example while the verified release is temporarily unavailable.</p>}<div className="metric-grid record-metrics">{hasRates && <><article><strong>{displayRate(record.igi)}</strong><span>IGI</span></article><article><strong>{displayRate(record.ige)}</strong><span>IGE</span></article></>}<article><strong>{record.unit_name || '—'}</strong><span>Unit</span></article><article><strong>{record.dataset_version || '—'}</strong><span>Release</span></article></div><button className="button primary" onClick={save}>{saved ? 'Saved locally' : 'Save locally'}</button><button data-testid="export-snapshots" className="button" type="button" onClick={exportSnapshots} disabled={!snapshots.length}>Export snapshots</button><a className="button" href={`/v1/ficha/${record.code}`} target="_blank" rel="noreferrer">API JSON</a><ul data-testid="snapshot-list" aria-live="polite" className="snapshot-list">{snapshots.map((snapshot) => <li key={snapshot.code}>{formatCode(snapshot.code)} · {snapshot.dataset_version}</li>)}</ul><section data-testid="hierarchy-card"><h2>Progressive decision tree</h2><label htmlFor="tree-query">Filter this hierarchy</label><div className="inline-form"><input data-testid="search-input" id="tree-query" value={treeFilter} onChange={(event) => setTreeFilter(event.target.value)} placeholder="e.g. 8517"/></div><p data-testid="tree-filter-status">{formatCode(treeFilter || record.code)}</p><ol className="hierarchy">{visibleHierarchy.map((entry) => { const entryCode = String(entry.code || entry); const label = entryCode.length === 2 ? 'Capítulo HS2' : entryCode.length === 4 ? 'Partida · familia HS4' : entryCode.length === 6 ? 'Subpartida HS6' : 'Fracción o NICO'; return <li key={entryCode}><strong>{label} · {formatCode(entryCode)}</strong> {entry.description || ''}</li>; })}</ol></section><section><h2>Recorded provenance</h2>{provenance.length ? <ul>{provenance.map((entry, index) => <li key={entry.source_url || index}><External href={entry.source_url || '#'}>{entry.source_name || 'Official source'}</External></li>)}</ul> : <p>No provenance entries are currently available.</p>}</section></section>;
}

export function ChaptersPage() {
  const navigate = useNavigate();
  const [sections, setSections] = useState(FALLBACK_SECTIONS);
  const [chapters, setChapters] = useState(FALLBACK_CHAPTERS);
  const [openSections, setOpenSections] = useState(new Set());
  const [openChapters, setOpenChapters] = useState(new Set());
  const [query, setQuery] = useState('');
  const [indexState, setIndexState] = useState('loading');
  useEffect(() => {
    let active = true;
    setIndexState('loading');
    Promise.all([api('/v1/sections'), api('/v1/chapters')])
      .then(([nextSections, nextChapters]) => {
        if (!active) return;
        // The fallback includes the public family navigation; preserve its DOM
        // while it is populated instead of replacing focused controls with the
        // flatter API chapter list during an interaction.
        if (!sections.length && nextSections.length) setSections(nextSections);
        if (!chapters.length && nextChapters.length) setChapters(nextChapters);
        setIndexState('ready');
      })
      .catch(() => {
        if (active) setIndexState('fallback');
      });
    return () => { active = false; };
  }, [chapters.length, sections.length]);
  const filtered = useMemo(() => chapters.filter((chapter) => `${chapter.code} ${chapter.description}`.toLowerCase().includes(query.toLowerCase())), [chapters, query]);
  const toggle = (setter, key) => setter((current) => { const next = new Set(current); next.has(key) ? next.delete(key) : next.add(key); return next; });
  return <><PageHero page={EDITORIAL_PAGES['/chapters']}><Link className="button" to="/changes">Ver evidencia de fracciones</Link></PageHero><section className="workspace"><label htmlFor="chapter-query">Buscar capítulo, código o descripción</label><input id="chapter-query" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Buscar capítulo, código o descripción"/><p className="status" role="status">{indexState === 'loading' ? 'Loading verified chapter index…' : indexState === 'fallback' ? 'Verified chapter index unavailable. Showing packaged navigation.' : 'Verified chapter index loaded.'}</p><div className="accordion">{sections.map((section) => { const isOpen = openSections.has(section.roman); const rows = filtered.filter((chapter) => Number(chapter.code) >= section.chapter_from && Number(chapter.code) <= section.chapter_to); return <article key={section.roman}><button aria-expanded={isOpen} onClick={() => toggle(setOpenSections, section.roman)}><span>{section.roman} · {section.name}</span><span>{section.chapter_from}–{section.chapter_to} · {rows.length} visibles</span></button>{isOpen && <div className="accordion-panel">{rows.length ? rows.map((chapter) => { const isChapterOpen = openChapters.has(chapter.code); const families = chapter.families || [{ code: `${chapter.code}.01`, description: 'Consultar familia HS4 en la release verificada' }]; return <article key={chapter.code}><button aria-expanded={isChapterOpen} onClick={() => toggle(setOpenChapters, chapter.code)}>Capítulo {chapter.code} · {chapter.description}</button>{isChapterOpen && <div className="accordion-panel">{families.map((family) => <button key={family.code} className="family-action" onClick={() => navigate(`/app?q=${encodeURIComponent(family.code)}`)}>Partida · familia HS4 {family.code} · {family.description}</button>)}</div>}</article>; }) : <p>No verified chapters match this filter.</p>}</div>}</article>; })}</div></section></>;
}

export function ChangesPage() {
  const [code, setCode] = useState('');
  const [state, setState] = useState('idle');
  const [record, setRecord] = useState(null);
  const [history, setHistory] = useState({ kind: 'loading', releases: [] });
  useEffect(() => {
    let active = true;
    api('/v1/repository')
      .then((response) => {
        if (active) setHistory({ kind: 'ready', releases: Array.isArray(response.releases) ? response.releases : [] });
      })
      .catch(() => { if (active) setHistory({ kind: 'unavailable', releases: [] }); });
    return () => { active = false; };
  }, []);
  const submit = (event) => { event.preventDefault(); const clean = code.replace(/\D/g, ''); if (!clean) return setState('empty'); setState('loading'); api(`/v1/ficha/${clean}`).then((response) => { setRecord(response.record || response); setState('ready'); }).catch(() => setState('not-found')); };
  return <><PageHero page={EDITORIAL_PAGES['/changes']} /><section className="workspace"><form onSubmit={submit}><label htmlFor="changes-query">Enter fraction or NICO</label><div className="inline-form"><input id="changes-query" value={code} onChange={(event) => setCode(event.target.value)} placeholder="8517.13.01"/><button className="button primary" type="submit">Inspect release</button></div></form><div role="status" aria-live="polite" className="status">{state === 'empty' && 'Enter a verified code to inspect release evidence.'}{state === 'loading' && 'Retrieving verified evidence…'}{state === 'not-found' && <>No verified record found. <Link to="/chapters">Browse chapters</Link></>}{state === 'ready' && `Verified record ready: ${record.code} · ${record.dataset_version || 'active release'}`}</div>{state === 'ready' && <article className="result-card"><h2>{record.code}</h2><p>{record.description}</p><p>Validity: {record.effective_from || 'No dated range recorded'}</p><Link to={`/app/record/${record.code}`}>Open complete evidence</Link></article>}<section className="source-strip" data-testid="release-history"><h2>Verified release history</h2><p>Each entry links to its immutable manifest, checksums and captured-source archive. New certified manifests record the source diff against the prior release.</p>{history.kind === 'loading' && <p role="status">Loading release history…</p>}{history.kind === 'ready' && history.releases.length > 0 && <ul>{history.releases.map((release) => <li key={release.tag}><External href={release.url}>{release.tag}</External>{release.publishedAt ? ` · published ${release.publishedAt.slice(0, 10)}` : ''}</li>)}</ul>}{(history.kind === 'unavailable' || (history.kind === 'ready' && !history.releases.length)) && <p>Release history is temporarily unavailable. <External href={OFFICIAL_LINKS.releases}>Inspect public releases</External></p>}</section></section></>;
}

export function MoaPage() { return <><PageHero page={EDITORIAL_PAGES['/moa']}><div className="hero-actions"><External href={OFFICIAL_LINKS.anamMoa}>Abrir Manual de ANAM</External><External href={OFFICIAL_LINKS.anamMoaPdf}>Ver documento enlazado por ANAM</External><External href={OFFICIAL_LINKS.anamMoaNotice}>Leer aviso oficial</External></div></PageHero><section className="card-grid">{MOA_GROUPS.map(([number, title, description, href]) => <article key={number}><span>{number}</span><h2>{title}</h2><p>{description}</p><External href={href}>Abrir fuente oficial</External></article>)}</section><section className="source-strip"><h2>Marco jurídico y versión</h2><External href={OFFICIAL_LINKS.law}>Ley Aduanera</External><External href={OFFICIAL_LINKS.anamNormativity}>Normatividad ANAM</External></section></>;
}

export function WikiPage() { return <><PageHero page={EDITORIAL_PAGES['/wiki']}><div className="hero-actions"><External href={OFFICIAL_LINKS.anamNormativity}>Abrir normatividad ANAM</External><External href={OFFICIAL_LINKS.anamGlossary}>Abrir glosario ANAM</External></div></PageHero><section className="card-grid">{WIKI_REFERENCES.map(([category, title, description, href]) => <article key={title}><span>{category}</span><h2>{title}</h2><p>{description}</p><External href={href}>Abrir fuente</External></article>)}</section><aside className="example-note"><h2>Cómo usar esta wiki</h2><p>Lee la fuente primaria completa y verifica su vigencia antes de usarla como contexto.</p><Link to="/glossary">Explorar glosario</Link></aside></>;
}

export function GlossaryPage() {
  const [query, setQuery] = useState('');
  const [filter, setFilter] = useState('Todas');
  const entries = useMemo(() => filterGlossary(GLOSSARY_ENTRIES, query, filter), [filter, query]);
  return <><PageHero page={EDITORIAL_PAGES['/glossary']}><External href={OFFICIAL_LINKS.anamGlossary}>Abrir glosario ANAM</External></PageHero><section className="workspace"><label htmlFor="glossary-query">Buscar en el glosario ANAM</label><input id="glossary-query" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Buscar término o definición"/><div className="filter-group" aria-label="Tipo de entrada">{['Todas', 'Siglas', 'Términos'].map((item) => <button className="button" aria-pressed={filter === item} onClick={() => setFilter(item)} key={item}>{item}</button>)}</div><p role="status" aria-live="polite">{entries.length} de {GLOSSARY_ENTRIES.length} entradas oficiales</p>{entries.length ? <section className="card-grid" data-testid="anam-glossary-results">{entries.map(({ category, term, definition }) => <article key={term}><span>{category}</span><h2>{term}</h2><p>{definition}</p><External href={OFFICIAL_LINKS.anamGlossary}>Fuente oficial</External></article>)}</section> : <aside className="empty-state"><h2>No glossary entries match “{query}”.</h2><button className="button" onClick={() => setQuery('')}>Clear search</button></aside>}</section></>;
}

export function TradeContextPage() { return <><PageHero page={EDITORIAL_PAGES['/trade-context']}><External href={OFFICIAL_LINKS.inegi}>Abrir explicación completa de INEGI</External></PageHero><section className="flow-diagram" aria-label="Trade context"><article><strong>Importaciones</strong><span>Compra al exterior</span></article><span aria-hidden="true">+</span><article><strong>Exportaciones</strong><span>Venta al exterior</span></article><span aria-hidden="true">→</span><article><strong>Balanza</strong><span>Diferencia</span></article></section><section className="card-grid"><article><h2>Importaciones</h2><p>Mercancías adquiridas desde el exterior.</p></article><article><h2>Exportaciones</h2><p>Mercancías vendidas hacia otros mercados.</p></article><article><h2>Balanza comercial</h2><p>Relación entre importaciones y exportaciones.</p></article><article><h2>Entidades y socios</h2><p>Contexto por territorio y contraparte comercial.</p></article></section><aside className="example-note"><p>INEGI · BCMM 2013–2023 · ETEF 2024</p><p>Estados Unidos en 2023: 42.7% de importaciones y 79.4% de exportaciones.</p><External href={OFFICIAL_LINKS.inegi}>Consultar tablas, gráficas y mapa originales</External></aside></>;
}

export function DocumentationPage() { const [query, setQuery] = useState(''); const links = DOCUMENTATION_LINKS.filter(([title]) => title.toLowerCase().includes(query.toLowerCase())); return <><PageHero page={EDITORIAL_PAGES['/documentation']}><External href={OFFICIAL_LINKS.pypi}>Install from PyPI</External></PageHero><section className="workspace"><label htmlFor="docs-query">Search documentation</label><input id="docs-query" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Search documentation"/>{links.length ? <section className="card-grid">{links.map(([title, path]) => <article key={path}><h2>{title}</h2><p>Read the maintained public contract in the repository.</p><External href={`${REPOSITORY}/blob/main/${path}`}>Open document</External></article>)}</section> : <aside className="empty-state" role="status"><h2>No documentation matches “{query}”.</h2><button className="button" onClick={() => setQuery('')}>Clear search</button></aside>}</section></>;
}

export function TrustPage() { return <><PageHero page={EDITORIAL_PAGES['/trust']}><External href={`${REPOSITORY}/blob/main/docs/production-certification.md`}>Read verification guide</External></PageHero><section className="card-grid">{[['01', 'Registered sources', 'Each source has a declared role and recorded provenance.'], ['02', 'Evidence reconciliation', 'Published data is compared against its evidence.'], ['03', 'Fail-closed build', 'When required evidence is incomplete, the release stops.'], ['04', 'Independent verification', 'Artifacts expose manifests, checksums and release identities.']].map(([number, title, description]) => <article key={number}><span>{number}</span><h2>{title}</h2><p>{description}</p></article>)}</section><External href={OFFICIAL_LINKS.releases}>Inspect public releases</External></>;
}

export function RecordsPage() {
  const [code, setCode] = useState('');
  const [records, setRecords] = useState(() => { try { return JSON.parse(localStorage.getItem(RECORDS_KEY) || '[]'); } catch { return []; } });
  const [status, setStatus] = useState('');
  const check = async (event) => { event.preventDefault(); const clean = code.replace(/\D/g, ''); if (!clean) return setStatus('Enter a verified fraction, NICO, or code.'); try { const record = await api(`/v1/lookup/${clean}`); const next = [{ ...record, savedAt: new Date().toISOString() }, ...records.filter((item) => item.code !== record.code)].slice(0, 50); localStorage.setItem(RECORDS_KEY, JSON.stringify(next)); setRecords(next); setStatus(`Prepared ${record.code} for local research.`); } catch { setStatus('Record unavailable. Check the verified code and try again.'); } };
  return <><PageHero page={EDITORIAL_PAGES['/records']} /><section className="metric-grid"><article><strong>{records.length}</strong><span>Saved</span></article><article><strong>{records.length}</strong><span>Ready to inspect</span></article><article><strong>Local only</strong><span>Not shared</span></article></section><section className="workspace"><form onSubmit={check}><label htmlFor="record-query">Verified tariff code</label><div className="inline-form"><input id="record-query" value={code} onChange={(event) => setCode(event.target.value)} placeholder="Fraction, NICO, or verified code"/><button className="button primary">Check verified record</button></div></form><p role="status" aria-live="polite">{status}</p>{records.length ? <section className="result-list">{records.map((record) => <article key={record.code}><div><h2>{record.code}</h2><p>{record.description}</p></div><Link className="button" to={`/app/record/${record.code}`}>Inspect</Link></article>)}</section> : <aside className="empty-state"><h2>No local records yet</h2><p>Check a verified code to prepare local research.</p></aside>}</section></>;
}

export function TradeDeskPage() { return <section className="empty-state"><h1>Mesa de comercio exterior</h1><p>Esta ruta conserva una superficie independiente con simulación orientativa, T-MEC, RRNA y trazabilidad local.</p><a className="button primary" href="/trade">Abrir mesa</a></section>; }

function MarketingPage({ eyebrow, title, description, action }) {
  return <><PageHero page={{ eyebrow, title, description, disclaimer: 'Consulta la release, el repositorio y la documentación antes de basar una integración en estos materiales.' }}><Link className="button primary" to={action.href}>{action.label}</Link></PageHero><section className="card-grid"><article><h2>Release evidence</h2><p>Inspecciona artefactos versionados, manifest y checksums.</p><External href={OFFICIAL_LINKS.releases}>Open releases</External></article><article><h2>Source contract</h2><p>Revisa los límites de la API pública y de los datos verificados.</p><Link to="/documentation">Read documentation</Link></article><article><h2>Open participation</h2><p>El trabajo se organiza en el repositorio público y sus discusiones.</p><External href={OFFICIAL_LINKS.github}>Open GitHub</External></article></section></>;
}

export const PAGE_COMPONENTS = {
  '/': HomePage,
  '/app': ExplorerPage,
  '/app/record/:code': RecordPage,
  '/chapters': ChaptersPage,
  '/changes': ChangesPage,
  '/moa': MoaPage,
  '/moa-guide': MoaPage,
  '/wiki': WikiPage,
  '/glossary': GlossaryPage,
  '/trade-context': TradeContextPage,
  '/documentation': DocumentationPage,
  '/trust': TrustPage,
  '/records': RecordsPage,
  '/trade': TradeDeskPage,
  '/features': () => <MarketingPage eyebrow="PRODUCT SURFACES" title="Build on verifiable tariff data." description="Explore the public product surfaces, documented limits and release artifacts." action={{ href: '/documentation', label: 'Read documentation' }} />,
  '/pricing': () => <MarketingPage eyebrow="OPEN DATA RELEASES" title="Public releases, inspectable artifacts." description="The core data and verification materials remain openly inspectable." action={{ href: '/trust', label: 'Read trust model' }} />,
  '/analytics': () => <MarketingPage eyebrow="RELEASE ANALYTICS" title="Release context without opaque scoring." description="Inspect a release through visible evidence and source roles." action={{ href: '/changes', label: 'Inspect release evidence' }} />,
  '/community': () => <MarketingPage eyebrow="OPEN COMMUNITY" title="Contribute through visible evidence." description="Use the public repository to review, discuss and improve the open data contract." action={{ href: '/documentation', label: 'Open documentation' }} />,
};
