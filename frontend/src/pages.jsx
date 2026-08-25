// Style: la ficha conserva la evidencia como contenido principal y ofrece el estimador como una salida contextual, no como navegación adicional.
import { useEffect, useMemo, useState } from 'react';
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom';

import {
  DOCUMENTATION_LINKS,
  EDITORIAL_PAGES,
  FALLBACK_CHAPTERS,
  FALLBACK_SECTIONS,
  MOA_GROUPS,
  OFFICIAL_LINKS,
  WIKI_REFERENCES,
} from './content.js';
import { useLocale } from './locale.jsx';
import { asExampleFicha, exampleRecordFor, formatCode, searchExampleRecords, VERIFIED_EXAMPLES } from './verified-examples.js';
import { displayRate, selectPrimarySearchResults } from './tariff.js';

const REPOSITORY = 'https://github.com/jccontrerasg08-cpu/arancel-mx';
const RECORDS_KEY = 'arancel-mx-research-records';

function api(path, signal) {
  return fetch(path, { signal, headers: { Accept: 'application/json' } }).then(async (response) => {
    if (!response.ok) throw new Error(`Request failed (${response.status})`);
    return response.json();
  });
}

function PageHero({ page, children, className = '' }) {
  return <section className={`page-hero ${className}`}><p className="eyebrow">{page.eyebrow}</p><h1>{page.title}</h1><p>{page.description}</p>{children}<p className="disclaimer">{page.disclaimer}</p></section>;
}

function External({ href, children }) {
  return <a href={href} target="_blank" rel="noreferrer">{children} <span aria-hidden="true">↗</span></a>;
}

const localize = (language, spanish, english) => language === 'en' ? english : spanish;

const exampleKind = (example) => example.level === 'hs2' ? 'HS' : example.level === 'nico10' ? 'NICO' : 'Fracción';
const localizedRate = (rate, language) => {
  const value = displayRate(rate);
  return language === 'es' && value === 'Consult release' ? 'Consultar release' : value;
};

function randomExample(current) {
  if (VERIFIED_EXAMPLES.length < 2) return current;
  const candidates = VERIFIED_EXAMPLES.map((_, index) => index).filter((index) => index !== current);
  return candidates[Math.floor(Math.random() * candidates.length)];
}

// Visual direction: Spanish-first evidence hero; each calm card change preserves an inspectable tariff example.
export function HomePage() {
  const [query, setQuery] = useState('');
  const [activeExample, setActiveExample] = useState(0);
  const [manualPause, setManualPause] = useState(false);
  const [insideEvidence, setInsideEvidence] = useState(false);
  const [releaseVersion, setReleaseVersion] = useState(null);
  const navigate = useNavigate();
  const { copy, language } = useLocale();
  const example = VERIFIED_EXAMPLES[activeExample];
  const visibleReleaseVersion = releaseVersion || example.dataset_version;
  useEffect(() => {
    const controller = new AbortController();
    api('/v1/meta', controller.signal)
      .then((metadata) => setReleaseVersion(metadata.dataset_version || null))
      .catch(() => {});
    return () => controller.abort();
  }, []);
  useEffect(() => {
    if (manualPause || insideEvidence || window.matchMedia('(prefers-reduced-motion: reduce)').matches) return undefined;
    const timer = window.setInterval(() => setActiveExample((current) => randomExample(current)), 5600);
    return () => window.clearInterval(timer);
  }, [insideEvidence, manualPause]);
  const submit = (event) => {
    event.preventDefault();
    navigate(`/app${query.trim() ? `?q=${encodeURIComponent(query.trim())}` : ''}`);
  };
  return <>
    <section className="home-hero" aria-labelledby="home-title"><div className="home-hero__copy"><p className="eyebrow">{copy.home.eyebrow}</p><p className="home-hero__kicker">{copy.home.kicker}</p><h1 id="home-title">{copy.home.title}<span>{copy.home.titleEmphasis}</span></h1><p>{copy.home.description}</p><form className="hero-search" onSubmit={submit}><label htmlFor="home-query">{copy.home.searchLabel}</label><div className="inline-form"><input id="home-query" type="search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder={copy.home.searchPlaceholder}/><button className="button primary" type="submit">{copy.home.submit}</button></div></form><p className="trust-line">{copy.home.trust}</p></div><aside data-testid="example-rotator" className="evidence-card" aria-label={copy.home.evidenceTitle} onMouseEnter={() => setInsideEvidence(true)} onMouseLeave={() => setInsideEvidence(false)} onFocusCapture={() => setInsideEvidence(true)} onBlurCapture={(event) => { if (!event.currentTarget.contains(event.relatedTarget)) setInsideEvidence(false); }}><img className="evidence-card__image" src="/assets/visuals/evidence-ledger.jpg" alt=""/><div className="evidence-card__chrome"><span/><span/><span/><code>release / {visibleReleaseVersion}</code></div><div className="evidence-card__body"><p className="eyebrow">{copy.home.evidenceEyebrow}</p><div className="evidence-card__heading"><div><h2>{copy.home.evidenceTitle}</h2><p>{copy.home.evidenceDescription}</p></div><button className="evidence-card__pause" type="button" aria-pressed={manualPause} onClick={() => setManualPause((current) => !current)}>{manualPause ? copy.home.resume : copy.home.pause}</button></div><article className="evidence-card__record" key={`${language}-${example.code}`}><div><span>{exampleKind(example)}</span><strong>{formatCode(example.code)}</strong></div><p>{example.description}</p><dl><div><dt>{copy.home.release}</dt><dd>{visibleReleaseVersion}</dd></div><div><dt>{copy.home.level}</dt><dd>{exampleKind(example)}</dd></div><div><dt>{copy.home.source}</dt><dd>{copy.home.sourceValue}</dd></div></dl><p className="evidence-card__note">{language === 'en' ? copy.home.officialDescription : ''}</p><button className="button" type="button" onClick={() => navigate(`/app?q=${encodeURIComponent(formatCode(example.code))}`)}>{copy.home.inspect}</button></article><div className="evidence-card__controls" aria-label={copy.home.evidenceTitle}>{VERIFIED_EXAMPLES.map((entry, index) => <button key={entry.code} type="button" className={index === activeExample ? 'is-active' : ''} aria-label={`${copy.home.show} ${formatCode(entry.code)}`} aria-pressed={index === activeExample} onClick={() => setActiveExample(index)}>{entry.level === 'hs2' ? 'HS' : entry.level === 'nico10' ? 'NICO' : '8D'}</button>)}</div></div></aside></section>
    <section className="metric-grid" aria-label={copy.home.evidenceTitle}>{copy.home.metrics.map(([value, label]) => <article key={label}><strong>{value}</strong><span>{label}</span></article>)}</section>
    <section className="card-grid">{copy.home.cards.map(([title, description, action], index) => <article key={title}><h2>{title}</h2><p>{description}</p>{index === 0 ? <External href={OFFICIAL_LINKS.releases}>{action}</External> : <Link to={index === 1 ? '/documentation' : '/trust'}>{action}</Link>}</article>)}</section>
  </>;
}

export function ExplorerPage() {
  const location = useLocation();
  const navigate = useNavigate();
  const { language } = useLocale();
  const initial = new URLSearchParams(location.search).get('q') || '';
  const [query, setQuery] = useState(initial);
  const [state, setState] = useState({ kind: initial ? 'loading' : 'idle', results: [] });
  const [suggestions, setSuggestions] = useState([]);
  const [activeSuggestion, setActiveSuggestion] = useState(-1);
  const [attempt, setAttempt] = useState(0);

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
  }, [attempt, initial]);
  useEffect(() => {
    const candidate = query.trim();
    if (initial || !candidate) {
      setSuggestions([]);
      return undefined;
    }
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      api(`/v1/search?q=${encodeURIComponent(candidate)}&limit=5`, controller.signal)
        .then((results) => setSuggestions(selectPrimarySearchResults(results, candidate).slice(0, 5)))
        .catch(() => setSuggestions(searchExampleRecords(candidate).slice(0, 5)));
    }, 180);
    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [query, initial]);
  useEffect(() => setActiveSuggestion(-1), [suggestions, query]);

  const submit = (event) => {
    event.preventDefault();
    const normalized = query.replace(/\D/g, '');
    if (!query.trim()) return setState({ kind: 'idle', results: [] });
    if ([2, 4, 6, 8, 10].includes(normalized.length) && normalized.length === query.replace(/[.\s-]/g, '').length) return navigate(`/app/record/${normalized}`);
    navigate(`/app?q=${encodeURIComponent(query.trim())}`);
  };
  const selectSuggestion = (index) => {
    const record = suggestions[index]?.record || suggestions[index];
    if (record) navigate(`/app/record/${record.code}`);
  };
  const onQueryKeyDown = (event) => {
    if (!suggestions.length) return;
    if (event.key === 'ArrowDown') {
      event.preventDefault();
      setActiveSuggestion((current) => Math.min(current + 1, suggestions.length - 1));
    } else if (event.key === 'ArrowUp') {
      event.preventDefault();
      setActiveSuggestion((current) => Math.max(current - 1, 0));
    } else if (event.key === 'Enter' && activeSuggestion >= 0) {
      event.preventDefault();
      selectSuggestion(activeSuggestion);
    } else if (event.key === 'Escape') {
      setSuggestions([]);
      setActiveSuggestion(-1);
    }
  };
  const copy = {
    hero: language === 'en' ? { eyebrow: 'VERIFIED RELEASE EXPLORER', title: 'Explore a tariff reference without losing its path.', description: 'Inspect hierarchy, release context and recorded evidence without treating a search result as a legal determination.', disclaimer: 'Public data and documented evidence. This site does not classify merchandise or provide legal advice.' } : { eyebrow: 'EXPLORADOR DE RELEASES VERIFICADOS', title: 'Explora una referencia arancelaria sin perder su camino.', description: 'Revisa jerarquía, contexto de release y evidencia registrada sin tratar un resultado de búsqueda como una determinación legal.', disclaimer: 'Datos públicos y evidencia documentada. Este sitio no clasifica mercancías ni proporciona asesoría legal.' },
    label: localize(language, 'Código o descripción', 'Code or description'), placeholder: localize(language, 'p. ej. 8517.13.01 o teléfonos', 'e.g. 8517.13.01 or phones'), submit: localize(language, 'Consultar release', 'Inspect release'), loading: localize(language, 'Buscando…', 'Searching…'), idle: localize(language, 'Ingresa un código arancelario o una descripción.', 'Enter a tariff code or a description.'), searching: localize(language, 'Buscando en la release verificada…', 'Searching the verified release…'), results: localize(language, 'Resultados verificados encontrados en la release registrada.', 'Verified results found in the recorded release presentation.'), empty: localize(language, 'No hay registros verificados que coincidan. Prueba 2, 4, 6, 8 o 10 dígitos, o una descripción más concreta.', 'No verified records match this search. Try 2, 4, 6, 8, or 10 digits, or a more specific description.'), error: localize(language, 'La release verificada no está disponible temporalmente.', 'The verified release is temporarily unavailable.'), retry: localize(language, 'Reintentar', 'Retry'), suggestions: localize(language, 'Rutas verificadas posibles', 'Possible verified paths'), noSuggestions: localize(language, 'Ninguna ruta verificada coincide con el texto actual.', 'No verified path matches the current text.'), verifiedResults: localize(language, 'resultados verificados', 'verified results'), inspect: localize(language, 'Ver ficha verificada', 'Inspect verified record'), activeRelease: localize(language, 'Resultado de la release verificada activa.', 'Active verified release result.'), fallback: localize(language, 'Ejemplo de presentación registrada mientras la release activa no está disponible.', 'Recorded presentation example while the active release is unavailable.'), tree: localize(language, 'Árbol de decisión progresivo', 'Progressive decision tree'), ready: localize(language, 'Ingresa un código completo o una descripción.', 'Enter a complete code or a description.'), example: localize(language, 'Fracción de ejemplo · 85.17.13.01', 'Example fraction · 85.17.13.01'), exampleDescription: localize(language, 'IGI e IGE aparecen sólo cuando se recupera una fracción verificada.', 'IGI and IGE appear only when a verified fraction record is retrieved.'), try: localize(language, 'Probar teléfonos', 'Try phones'), browse: localize(language, 'Explorar árbol visual', 'Browse visual tree'), emptyTitle: localize(language, 'Estructura de ejemplo, no un resultado.', 'Example structure, not a result.'), emptyDescription: localize(language, 'Usa el Explorador para revisar sólo registros recuperados desde la release verificada activa.', 'Use the Explorer to inspect only records retrieved from the active verified release.')
  };

  return <>
    <PageHero className="page-hero--explorer" page={{
      ...copy.hero,
    }} />
    <section className="workspace"><form onSubmit={submit} className="search-form"><label htmlFor="app-query">{copy.label}</label><div className="inline-form"><input data-testid="search-input" id="app-query" type="search" role="combobox" aria-autocomplete="list" aria-expanded={!initial && query.trim().length > 0 && suggestions.length > 0} aria-controls="live-suggestions-list" aria-activedescendant={activeSuggestion >= 0 ? `suggestion-${activeSuggestion}` : undefined} autoComplete="off" value={query} onKeyDown={onQueryKeyDown} onChange={(event) => setQuery(event.target.value)} placeholder={copy.placeholder}/><button data-testid="search-submit" className="button primary" type="submit" disabled={state.kind === 'loading'}>{state.kind === 'loading' ? copy.loading : copy.submit}</button></div><div role="status" aria-live="polite" className="status">{state.kind === 'idle' && copy.idle}{state.kind === 'loading' && copy.searching}{state.kind === 'results' && copy.results}{state.kind === 'empty' && copy.empty}{state.kind === 'error' && <>{copy.error} <button type="button" className="text-button" onClick={() => setAttempt((current) => current + 1)}>{copy.retry}</button></>}</div></form>
      {!initial && query.trim() && <section data-testid="live-suggestions" className="live-suggestions" aria-label={copy.suggestions}><p>{copy.suggestions}</p>{suggestions.length ? <div id="live-suggestions-list" role="listbox">{suggestions.map((item, index) => { const record = item.record || item; return <button id={`suggestion-${index}`} key={record.code} role="option" aria-selected={index === activeSuggestion} className={index === activeSuggestion ? 'is-active' : ''} type="button" onMouseEnter={() => setActiveSuggestion(index)} onClick={() => selectSuggestion(index)}><strong>{formatCode(record.code)}</strong><span lang={language === 'en' ? 'es-MX' : undefined}>{record.description}</span></button>; })}</div> : <small>{copy.noSuggestions}</small>}</section>}
      {state.kind === 'results' && <><p className="status">{state.fallback ? copy.fallback : copy.activeRelease}</p><section className="result-list" aria-label={copy.results}><h2>{state.results.length} {copy.verifiedResults}</h2>{state.results.map((item) => { const record = item.record || item; return <article data-testid="result-card" key={record.code}><div><span>{item.match_kind || 'verified match'}</span><h3><code>{formatCode(record.code)}</code></h3><p lang={language === 'en' ? 'es-MX' : undefined}>{record.description}</p><small>{record.dataset_version || 'active release'} · {record.level}</small></div><Link className="button" to={`/app/record/${record.code}`}>{copy.inspect}</Link></article>; })}</section><section data-testid="hierarchy-card" className="example-note"><h2>{copy.tree}</h2><p>{state.results[0] && (state.results[0].record || state.results[0]).code}</p><p data-testid="tree-filter-status">{formatCode(initial)}</p></section></>}
      {state.kind === 'idle' && <><h2>{copy.ready}</h2><aside data-testid="example-fraction" className="example-note"><strong>{copy.example}</strong><p>{copy.exampleDescription}</p><div className="hero-actions"><button className="button" type="button" onClick={() => navigate('/app?q=teléfonos')}>{copy.try}</button><Link to="/chapters">{copy.browse}</Link></div></aside></>}
      {state.kind === 'empty' && <aside className="example-note"><strong>{copy.emptyTitle}</strong><p>{copy.emptyDescription}</p><Link to="/chapters">{copy.browse}</Link></aside>}
    </section>
  </>;
}

export function RecordPage() {
  const { code } = useParams();
  const { language } = useLocale();
  const [state, setState] = useState({ kind: 'loading' });
  const [retry, setRetry] = useState(0);
  const [saved, setSaved] = useState(false);
  const [snapshots, setSnapshots] = useState(() => { try { return JSON.parse(localStorage.getItem('arancel-mx-fichas-locales') || '[]'); } catch { return []; } });
  const [treeFilter, setTreeFilter] = useState('');
  const copy = language === 'en' ? { loading: 'Retrieving verified hierarchy and recorded evidence…', unavailable: 'The verified release is temporarily unavailable.', retry: 'Retry', explorer: 'Return to Explorer', ready: 'Verified record ready.', eyebrow: 'VERIFIED RECORD', context: 'Release context, not advice.', fallback: 'Recorded presentation example while the verified release is temporarily unavailable.', unit: 'Unit', release: 'Release', estimate: 'Estimate import contributions', estimateTitle: 'Estimate after selecting a fraction or NICO.', estimateDescription: 'This hierarchy level provides context, but the estimator needs an 8-digit fraction or a 10-digit NICO.', compatible: 'Find a compatible fraction', saved: 'Saved locally', save: 'Save locally', export: 'Export snapshots', tree: 'Progressive decision tree', filter: 'Filter this hierarchy by a parent code', filterHint: 'Use a prefix such as 8517 to narrow this visible path; this does not run a new search.', provenance: 'Recorded provenance', noProvenance: 'No provenance entries are currently available.', source: 'Official source' } : { loading: 'Recuperando jerarquía verificada y evidencia registrada…', unavailable: 'La release verificada no está disponible temporalmente.', retry: 'Reintentar', explorer: 'Volver al Explorador', ready: 'Registro verificado listo.', eyebrow: 'REGISTRO VERIFICADO', context: 'Contexto de release, no asesoría.', fallback: 'Ejemplo de presentación registrada mientras la release verificada no está disponible.', unit: 'Unidad', release: 'Release', estimate: 'Estimar contribuciones de importación', estimateTitle: 'Estima después de seleccionar una fracción o NICO.', estimateDescription: 'Este nivel jerárquico aporta contexto, pero el estimador requiere una fracción de 8 dígitos o un NICO de 10 dígitos.', compatible: 'Buscar una fracción compatible', saved: 'Guardado localmente', save: 'Guardar localmente', export: 'Exportar fichas', tree: 'Árbol de decisión progresivo', filter: 'Filtrar esta jerarquía por un código padre', filterHint: 'Usa un prefijo como 8517 para acotar este camino visible; no realiza una búsqueda nueva.', provenance: 'Procedencia registrada', noProvenance: 'No hay entradas de procedencia disponibles actualmente.', source: 'Fuente oficial' };
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
  if (state.kind === 'loading') return <p className="status" role="status">{copy.loading}</p>;
  if (state.kind === 'error') return <section className="empty-state"><h1>{copy.unavailable}</h1><button className="button primary" type="button" onClick={() => setRetry((current) => current + 1)}>{copy.retry}</button><Link to="/app">{copy.explorer}</Link></section>;
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
  const normalizedRecordCode = String(record.code || '').replace(/[.\s-]/g, '');
  const hasRates = record.level === 'fraccion8' || normalizedRecordCode.length === 8;
  const hasSupportedEstimateCode = /^\d{8}(?:\d{2})?$/.test(normalizedRecordCode);
  const formattedCode = ficha.formatted_code || formatCode(record.code);
  const hierarchy = ficha.hierarchy || record.hierarchy || [];
  const visibleHierarchy = hierarchy.filter((entry) => !treeFilter || String(entry.code || '').startsWith(treeFilter.replace(/\D/g, '')) || String(record.code || '').startsWith(treeFilter.replace(/\D/g, '')));
  return <section data-testid="result-card" className="record-page"><p role="status" aria-live="polite">{copy.ready}</p><p className="eyebrow">{copy.eyebrow}</p><h1>{formattedCode}</h1><p lang={language === 'en' ? 'es-MX' : undefined}>{record.description}</p><h2>{copy.context}</h2>{state.fallback && <p className="example-note">{copy.fallback}</p>}<div className="metric-grid record-metrics">{hasRates && <><article><strong>{localizedRate(record.igi, language)}</strong><span>IGI</span></article><article><strong>{localizedRate(record.ige, language)}</strong><span>IGE</span></article></>}<article><strong>{record.unit_name || '—'}</strong><span>{copy.unit}</span></article><article><strong>{record.dataset_version || '—'}</strong><span>{copy.release}</span></article></div><div className="record-actions">{hasSupportedEstimateCode ? <a data-testid="open-estimate" className="button primary" href={`/trade?code=${encodeURIComponent(record.code)}`}>{copy.estimate}</a> : <aside data-testid="estimate-guidance" className="estimate-guidance"><strong>{copy.estimateTitle}</strong><p>{copy.estimateDescription}</p><Link className="button" to={`/app?q=${encodeURIComponent(record.code)}`}>{copy.compatible}</Link></aside>}<div className="record-actions__secondary"><button className="button" onClick={save}>{saved ? copy.saved : copy.save}</button><button data-testid="export-snapshots" className="button" type="button" onClick={exportSnapshots} disabled={!snapshots.length}>{copy.export}</button><a className="button" href={`/v1/ficha/${record.code}`} target="_blank" rel="noreferrer">API JSON</a></div></div><ul data-testid="snapshot-list" aria-live="polite" className="snapshot-list">{snapshots.map((snapshot) => <li key={snapshot.code}>{formatCode(snapshot.code)} · {snapshot.dataset_version}</li>)}</ul><section data-testid="hierarchy-card"><h2>{copy.tree}</h2><label htmlFor="tree-query">{copy.filter}</label><p className="field-hint">{copy.filterHint}</p><div className="inline-form"><input data-testid="search-input" id="tree-query" type="search" value={treeFilter} onChange={(event) => setTreeFilter(event.target.value)} placeholder="p. ej. 8517"/></div><p data-testid="tree-filter-status">{formatCode(treeFilter || record.code)}</p><ol className="hierarchy">{visibleHierarchy.map((entry) => { const entryCode = String(entry.code || entry); const label = entryCode.length === 2 ? 'Capítulo HS2' : entryCode.length === 4 ? 'Partida · familia HS4' : entryCode.length === 6 ? 'Subpartida · HS6' : 'Fracción o NICO'; return <li key={entryCode}><strong>{label} · {formatCode(entryCode)}</strong> {entry.description || ''}</li>; })}</ol></section><section><h2>{copy.provenance}</h2>{provenance.length ? <ul>{provenance.map((entry, index) => <li key={entry.source_url || index}><External href={entry.source_url || '#'}>{entry.source_name || copy.source}</External></li>)}</ul> : <p>{copy.noProvenance}</p>}</section></section>;
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
  useEffect(() => {
    if (!query.trim()) return;
    const matchingSections = new Set(sections.filter((section) => filtered.some((chapter) => Number(chapter.code) >= section.chapter_from && Number(chapter.code) <= section.chapter_to)).map((section) => section.roman));
    setOpenSections(matchingSections);
    setOpenChapters(new Set(filtered.slice(0, 8).map((chapter) => chapter.code)));
  }, [filtered, query, sections]);
  const toggle = (setter, key) => setter((current) => { const next = new Set(current); next.has(key) ? next.delete(key) : next.add(key); return next; });
  return <><PageHero page={EDITORIAL_PAGES['/chapters']}><Link className="button" to="/changes">Ver evidencia de fracciones</Link></PageHero><section className="workspace"><label htmlFor="chapter-query">Buscar capítulo, código o descripción</label><input id="chapter-query" type="search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Buscar capítulo, código o descripción"/><p className="status" role="status">{query.trim() ? `${filtered.length} matching chapters expanded while you type.` : indexState === 'loading' ? 'Loading verified chapter index…' : indexState === 'fallback' ? 'Verified chapter index unavailable. Showing packaged navigation.' : 'Verified chapter index loaded.'}</p><div className="accordion">{sections.map((section) => { const isOpen = openSections.has(section.roman); const rows = filtered.filter((chapter) => Number(chapter.code) >= section.chapter_from && Number(chapter.code) <= section.chapter_to); return <article key={section.roman}><button aria-expanded={isOpen} onClick={() => toggle(setOpenSections, section.roman)}><span>{section.roman} · {section.name}</span><span>{section.chapter_from}–{section.chapter_to} · {rows.length} visibles</span></button>{isOpen && <div className="accordion-panel">{rows.length ? rows.map((chapter) => { const isChapterOpen = openChapters.has(chapter.code); const families = chapter.families || [{ code: `${chapter.code}.01`, description: 'Consultar familia HS4 en la release verificada' }]; return <article key={chapter.code}><button aria-expanded={isChapterOpen} onClick={() => toggle(setOpenChapters, chapter.code)}>Capítulo {chapter.code} · {chapter.description}</button>{isChapterOpen && <div className="accordion-panel">{families.map((family) => <button key={family.code} className="family-action" onClick={() => navigate(`/app?q=${encodeURIComponent(family.code)}`)}>Partida · familia HS4 {family.code} · {family.description}</button>)}</div>}</article>; }) : <p>No verified chapters match this filter.</p>}</div>}</article>; })}</div></section></>;
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
