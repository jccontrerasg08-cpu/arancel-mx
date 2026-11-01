// Style: la ficha conserva la evidencia como contenido principal y ofrece el estimador como una salida contextual, no como navegación adicional.
import { lazy, Suspense, useEffect, useMemo, useRef, useState } from 'react';
import { Link, useLocation, useNavigate, useParams } from 'react-router-dom';

import {
  DOCUMENTATION_LINKS,
  EDITORIAL_PAGES,
  editorialPage,
  FALLBACK_CHAPTERS,
  FALLBACK_SECTIONS,
  MOA_GROUPS,
  OFFICIAL_LINKS,
  WIKI_REFERENCES,
} from './content.js';
import { useLocale } from './locale.jsx';
import { applyPageMeta, describeRecord, setRecordMeta } from './page-meta.js';
import { asExampleFicha, exampleRecordFor, formatCode, searchExampleRecords, VERIFIED_EXAMPLES } from './verified-examples.js';
import { displayRate, selectPrimarySearchResults } from './tariff.js';
import { createStaticApi } from './static-api.js';

const REPOSITORY = 'https://github.com/jccontrerasg08-cpu/arancel-mx';
const RECORDS_KEY = 'arancel-mx-research-records';

// Same-origin static data tree: GitHub Pages behind a Vercel rewrite in
// production, the FastAPI app's /data/v1 route locally (decision 0002).
export const DATA_BASE = '/data/v1';
const dataClient = createStaticApi({ base: DATA_BASE });

function api(path, signal) {
  return dataClient.request(path, signal);
}

// A generic row ("Los demás.") only makes sense under its heading and
// subheading, so each result carries the descriptions of its HS4 and HS6
// ancestors. Missing context never hides a result.
async function withHierarchyContext(results, signal) {
  return Promise.all(results.map(async (item) => {
    const record = item.record || item;
    if (!record.code || record.code.length <= 4) return item;
    // Ancestors live in the chapter file the search already loaded.
    const widths = [4, 6, 8].filter((width) => width < record.code.length);
    const ancestors = await Promise.all(
      widths.map((width) => api(`/v1/lookup/${record.code.slice(0, width)}`, signal).catch(() => null)),
    );
    const context = ancestors
      .filter((entry) => entry && entry.description)
      .map((entry) => entry.description.replace(/[.:]$/u, ''));
    return context.length ? { ...item, context } : item;
  }));
}

const chapterDataUrl = (code) => `${DATA_BASE}/records/${String(code).slice(0, 2)}.json`;

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

// Clipboard API first; a hidden textarea covers contexts where it is blocked.
async function copyText(text) {
  try {
    await navigator.clipboard.writeText(text);
    return true;
  } catch {
    const field = document.createElement('textarea');
    field.value = text;
    field.setAttribute('readonly', '');
    field.style.position = 'fixed';
    field.style.opacity = '0';
    document.body.appendChild(field);
    field.select();
    try { return document.execCommand('copy'); } catch { return false; } finally { field.remove(); }
  }
}
const HOME_TILE_ICONS = {
  explore: <><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></>,
  learn: <><path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H20v16H6.5A2.5 2.5 0 0 0 4 21.5Z"/><path d="M4 21.5V5.5"/><path d="M9 8h7"/></>,
  data: <path d="M4 20V10M10 20V4M16 20v-7M22 20H2"/>,
  trust: <><path d="M12 3 4 6v6c0 4.5 3.2 8 8 9 4.8-1 8-4.5 8-9V6Z"/><path d="m9 12 2 2 4-4"/></>,
};

// Compact landing: one search, verified examples as shortcuts and four color-coded entry points.
export function HomePage() {
  const [query, setQuery] = useState('');
  const [releaseVersion, setReleaseVersion] = useState(null);
  const navigate = useNavigate();
  const { copy } = useLocale();
  const visibleReleaseVersion = releaseVersion || VERIFIED_EXAMPLES[0].dataset_version;
  useEffect(() => {
    const controller = new AbortController();
    api('/v1/meta', controller.signal)
      .then((metadata) => setReleaseVersion(metadata.dataset_version || null))
      .catch(() => {});
    return () => controller.abort();
  }, []);
  const submit = (event) => {
    event.preventDefault();
    navigate(`/app${query.trim() ? `?q=${encodeURIComponent(query.trim())}` : ''}`);
  };
  return <>
    <section className="home-hero" aria-labelledby="home-title">
      <p className="release-pill" data-testid="release-pill"><span aria-hidden="true"/>release {visibleReleaseVersion} · {copy.home.verified}</p>
      <h1 id="home-title">{copy.home.title}<span>{copy.home.titleEmphasis}</span></h1>
      <p className="home-hero__lead">{copy.home.description}</p>
      <form className="hero-search" onSubmit={submit}><label className="sr-only" htmlFor="home-query">{copy.home.searchLabel}</label><div className="inline-form"><input id="home-query" type="search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder={copy.home.searchPlaceholder}/><button className="button primary" type="submit">{copy.home.submit}</button></div></form>
      <div className="home-chips"><span>{copy.home.tryWith}</span>{VERIFIED_EXAMPLES.map((example) => <Link key={example.code} className="chip" viewTransition to={`/app?q=${encodeURIComponent(formatCode(example.code))}`} title={example.description}>{formatCode(example.code)}</Link>)}</div>
      <dl className="home-stats">{copy.home.metrics.map(([value, label]) => <div key={label}><dt>{label}</dt><dd>{value}</dd></div>)}</dl>
    </section>
    <section className="home-start" aria-labelledby="home-start-title"><h2 id="home-start-title">{copy.home.startTitle}</h2><div className="home-tiles">{copy.home.tiles.map(([description, href, id]) => <Link key={id} className={`home-tile home-tile--${id}`} to={href} viewTransition><span className="home-tile__badge"><svg viewBox="0 0 24 24" aria-hidden="true">{HOME_TILE_ICONS[id]}</svg><strong>{copy.navGroups[id]}</strong></span><p>{description}</p></Link>)}</div></section>
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
  const suggestionGeneration = useRef(0);

  useEffect(() => setQuery(initial), [initial]);
  useEffect(() => {
    if (!initial) return;
    const controller = new AbortController();
    setState({ kind: 'loading', results: [] });
    api(`/v1/search?q=${encodeURIComponent(initial)}&limit=10`, controller.signal)
      .then((results) => withHierarchyContext(selectPrimarySearchResults(results, initial), controller.signal))
      .then((primaryResults) => {
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
      suggestionGeneration.current += 1;
      setSuggestions([]);
      return undefined;
    }
    const generation = ++suggestionGeneration.current;
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      api(`/v1/search?q=${encodeURIComponent(candidate)}&limit=5`, controller.signal)
        .then((results) => {
          if (generation === suggestionGeneration.current) setSuggestions(selectPrimarySearchResults(results, candidate).slice(0, 5));
        })
        .catch(() => {
          if (generation === suggestionGeneration.current) setSuggestions(searchExampleRecords(candidate).slice(0, 5));
        });
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
    if (event.key === 'Escape') {
      suggestionGeneration.current += 1;
      setSuggestions([]);
      setActiveSuggestion(-1);
      return;
    }
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
      {state.kind === 'results' && <><p className="status">{state.fallback ? copy.fallback : copy.activeRelease}</p><section className="result-list" aria-label={copy.results}><h2>{state.results.length} {copy.verifiedResults}</h2>{state.results.map((item) => { const record = item.record || item; return <article data-testid="result-card" key={record.code}><div><span>{item.match_kind || 'verified match'}</span><h3><code>{formatCode(record.code)}</code></h3>{item.context?.length > 0 && <p data-testid="result-context" className="result-context" lang="es-MX" title={item.context.join(' › ')}>{item.context.join(' › ')}</p>}<p lang={language === 'en' ? 'es-MX' : undefined}>{record.description}</p><small>{record.dataset_version || 'active release'} · {record.level}</small></div><Link className="button" to={`/app/record/${record.code}`}>{copy.inspect}</Link></article>; })}</section><section data-testid="hierarchy-card" className="example-note"><h2>{copy.tree}</h2><p>{state.results[0] && (state.results[0].record || state.results[0]).code}</p><p data-testid="tree-filter-status">{formatCode(initial)}</p></section></>}
      {state.kind === 'idle' && <><h2>{copy.ready}</h2><aside data-testid="example-fraction" className="example-note"><strong>{copy.example}</strong><p>{copy.exampleDescription}</p><div className="hero-actions"><button className="button" type="button" onClick={() => navigate('/app?q=teléfonos')}>{copy.try}</button><Link to="/chapters">{copy.browse}</Link></div></aside></>}
      {state.kind === 'empty' && <aside className="example-note"><strong>{copy.emptyTitle}</strong><p>{copy.emptyDescription}</p><Link to="/chapters">{copy.browse}</Link></aside>}
    </section>
  </>;
}

// Long legal descriptions stay in the DOM but fold to two lines until the reader asks for more.
function HierarchyItem({ label, description, language }) {
  const [expanded, setExpanded] = useState(false);
  const long = description.length > 150;
  return <li><strong>{label}</strong> <span className={long && !expanded ? 'is-clamped' : undefined}>{description}</span>{long && <button className="text-button" type="button" aria-expanded={expanded} onClick={() => setExpanded((current) => !current)}>{expanded ? localize(language, 'Ver menos', 'Show less') : localize(language, 'Ver completo', 'Show full text')}</button>}</li>;
}
export function RecordPage() {
  const { code } = useParams();
  const { pathname } = useLocation();
  const { language } = useLocale();
  const [state, setState] = useState({ kind: 'loading' });
  const [retry, setRetry] = useState(0);
  const [saved, setSaved] = useState(false);
  const [snapshots, setSnapshots] = useState(() => { try { return JSON.parse(localStorage.getItem('arancel-mx-fichas-locales') || '[]'); } catch { return []; } });
  const [treeFilter, setTreeFilter] = useState('');
  const [copied, setCopied] = useState(false);
  useEffect(() => {
    if (!copied) return undefined;
    const timer = window.setTimeout(() => setCopied(false), 2000);
    return () => window.clearTimeout(timer);
  }, [copied]);
  const copy = language === 'en' ? { breadcrumb: 'Breadcrumb', home: 'Home', explore: 'Explore', copyCode: 'Copy code', copied: 'Copied', levels: ['Chapter', 'Heading', 'Subheading', 'Fraction', 'NICO'], loading: 'Retrieving verified hierarchy and recorded evidence…', unavailable: 'The verified release is temporarily unavailable.', retry: 'Retry', explorer: 'Return to Explorer', ready: 'Verified record ready.', eyebrow: 'VERIFIED RECORD', context: 'Release context, not advice.', fallback: 'Recorded presentation example while the verified release is temporarily unavailable.', unit: 'Unit', release: 'Release', validity: 'Rate in force', validitySince: 'since', validityUntil: 'until', validityUnknown: 'No dated range recorded', estimate: 'Estimate import contributions', estimateTitle: 'Estimate after selecting a fraction or NICO.', estimateDescription: 'This hierarchy level provides context, but the estimator needs an 8-digit fraction or a 10-digit NICO.', compatible: 'Find a compatible fraction', saved: 'Saved locally', save: 'Save locally', export: 'Export snapshots', tree: 'Progressive decision tree', filter: 'Filter this hierarchy by a parent code', filterHint: 'Use a prefix such as 8517 to narrow this visible path; this does not run a new search.', provenance: 'Recorded provenance', noProvenance: 'No provenance entries are currently available.', jumpLabel: 'Record sections', jumpSummary: 'Summary', jumpTree: 'Hierarchy', jumpProvenance: 'Provenance', source: 'Official source' } : { breadcrumb: 'Ruta de navegación', home: 'Inicio', explore: 'Explorar', copyCode: 'Copiar código', copied: 'Copiado', levels: ['Capítulo', 'Partida', 'Subpartida', 'Fracción', 'NICO'], loading: 'Recuperando jerarquía verificada y evidencia registrada…', unavailable: 'La release verificada no está disponible temporalmente.', retry: 'Reintentar', explorer: 'Volver al Explorador', ready: 'Registro verificado listo.', eyebrow: 'REGISTRO VERIFICADO', context: 'Contexto de release, no asesoría.', fallback: 'Ejemplo de presentación registrada mientras la release verificada no está disponible.', unit: 'Unidad', release: 'Release', validity: 'Vigencia de la tasa', validitySince: 'desde', validityUntil: 'hasta', validityUnknown: 'Sin fecha registrada', estimate: 'Estimar contribuciones de importación', estimateTitle: 'Estima después de seleccionar una fracción o NICO.', estimateDescription: 'Este nivel jerárquico aporta contexto, pero el estimador requiere una fracción de 8 dígitos o un NICO de 10 dígitos.', compatible: 'Buscar una fracción compatible', saved: 'Guardado localmente', save: 'Guardar localmente', export: 'Exportar fichas', tree: 'Árbol de decisión progresivo', filter: 'Filtrar esta jerarquía por un código padre', filterHint: 'Usa un prefijo como 8517 para acotar este camino visible; no realiza una búsqueda nueva.', provenance: 'Procedencia registrada', noProvenance: 'No hay entradas de procedencia disponibles actualmente.', jumpLabel: 'Secciones de la ficha', jumpSummary: 'Resumen', jumpTree: 'Jerarquía', jumpProvenance: 'Procedencia', source: 'Fuente oficial' };
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
  // Once the record is known, the tab title and the shared preview name the fraction.
  useEffect(() => {
    if (state.kind !== 'ready') return;
    const loaded = state.ficha.record || state.ficha;
    const digits = String(loaded.code || '').replace(/[.\s-]/g, '');
    const withRates = loaded.level === 'fraccion8' || digits.length === 8;
    const meta = { path: pathname, ...describeRecord({ code: state.ficha.formatted_code || formatCode(loaded.code), description: loaded.description, rates: withRates ? `IGI ${localizedRate(loaded.igi, language)} · IGE ${localizedRate(loaded.ige, language)}` : '', language }) };
    setRecordMeta(meta);
    applyPageMeta({ pathname, title: meta.title, summary: meta.summary, locale: language === 'en' ? 'en_US' : 'es_MX' });
  }, [state, language, pathname]);
  if (state.kind === 'loading') return <><p className="status" role="status">{copy.loading}</p><div className="record-skeleton" aria-hidden="true"><span className="skeleton"/><span className="skeleton"/><div><span className="skeleton"/><span className="skeleton"/><span className="skeleton"/><span className="skeleton"/></div></div></>;
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
  const levelByLength = { 2: 0, 4: 1, 6: 2, 8: 3, 10: 4 };
  const ancestors = hierarchy.map((entry) => String(entry.code || entry).replace(/\D/g, '')).filter((entryCode) => entryCode && entryCode !== normalizedRecordCode);
  const copyCode = () => { copyText(formattedCode).then((done) => { if (done) setCopied(true); }); };
  return <section data-testid="result-card" className="record-page"><p className="sr-only" role="status" aria-live="polite">{copy.ready}</p><nav className="breadcrumb" aria-label={copy.breadcrumb}><ol><li><Link to="/">{copy.home}</Link></li><li><Link to="/app">{copy.explore}</Link></li>{ancestors.map((entryCode) => <li key={entryCode}><Link to={`/app/record/${entryCode}`}>{copy.levels[levelByLength[entryCode.length]]} {formatCode(entryCode)}</Link></li>)}<li aria-current="page">{formattedCode}</li></ol></nav><p className="eyebrow">{copy.eyebrow}</p><div className="record-heading"><h1>{formattedCode}</h1><button type="button" className={copied ? 'button is-copied' : 'button'} onClick={copyCode}>{copied ? copy.copied : copy.copyCode}</button><span className="sr-only" aria-live="polite">{copied ? copy.copied : ''}</span></div><p lang={language === 'en' ? 'es-MX' : undefined}>{record.description}</p><nav className="record-jump" aria-label={copy.jumpLabel}><a href="#record-summary">{copy.jumpSummary}</a><a href="#record-hierarchy">{copy.jumpTree}</a><a href="#record-provenance">{copy.jumpProvenance}</a></nav><h2 id="record-summary">{copy.context}</h2>{state.fallback && <p className="example-note">{copy.fallback}</p>}<div className={`metric-grid record-metrics${hasRates ? '' : ' record-metrics--compact'}`}>{hasRates && <><article className="metric-tile metric-tile--explore"><strong>{localizedRate(record.igi, language)}</strong><span>IGI</span></article><article className="metric-tile metric-tile--data"><strong>{localizedRate(record.ige, language)}</strong><span>IGE</span></article></>}<article className="metric-tile metric-tile--learn"><strong>{record.unit_name || '—'}</strong><span>{copy.unit}</span></article>{hasRates && <article data-testid="rate-validity" className="metric-tile metric-tile--trust"><strong>{record.effective_from ? `${copy.validitySince} ${record.effective_from}${record.effective_to ? ` ${copy.validityUntil} ${record.effective_to}` : ''}` : copy.validityUnknown}</strong><span>{copy.validity}</span></article>}<article className="metric-tile"><strong>{record.dataset_version || '—'}</strong><span>{copy.release}</span></article></div><div className="record-actions">{hasSupportedEstimateCode ? <a data-testid="open-estimate" className="button primary" href={`/trade?code=${encodeURIComponent(record.code)}`}>{copy.estimate}</a> : <aside data-testid="estimate-guidance" className="estimate-guidance"><strong>{copy.estimateTitle}</strong><p>{copy.estimateDescription}</p><Link className="button" to={`/app?q=${encodeURIComponent(record.code)}`}>{copy.compatible}</Link></aside>}<div className="record-actions__secondary"><button className="button" onClick={save}>{saved ? copy.saved : copy.save}</button><button data-testid="export-snapshots" className="button" type="button" onClick={exportSnapshots} disabled={!snapshots.length}>{copy.export}</button><a className="button" href={chapterDataUrl(record.code)} target="_blank" rel="noreferrer">API JSON</a></div></div><ul data-testid="snapshot-list" aria-live="polite" className="snapshot-list">{snapshots.map((snapshot) => <li key={snapshot.code}>{formatCode(snapshot.code)} · {snapshot.dataset_version}</li>)}</ul><section data-testid="hierarchy-card" id="record-hierarchy"><h2>{copy.tree}</h2><label htmlFor="tree-query">{copy.filter}</label><p className="field-hint">{copy.filterHint}</p><div className="inline-form"><input data-testid="search-input" id="tree-query" type="search" value={treeFilter} onChange={(event) => setTreeFilter(event.target.value)} placeholder="p. ej. 8517"/></div><p data-testid="tree-filter-status">{formatCode(treeFilter || record.code)}</p><ol className="hierarchy">{visibleHierarchy.map((entry) => { const entryCode = String(entry.code || entry); const label = entryCode.length === 2 ? 'Capítulo HS2' : entryCode.length === 4 ? 'Partida · familia HS4' : entryCode.length === 6 ? 'Subpartida · HS6' : 'Fracción o NICO'; return <HierarchyItem key={entryCode} label={`${label} · ${formatCode(entryCode)}`} description={entry.description || ''} language={language}/>; })}</ol></section><section id="record-provenance"><h2>{copy.provenance}</h2>{provenance.length ? <ul>{provenance.map((entry, index) => <li key={entry.source_url || index}><External href={entry.source_url || '#'}>{entry.source_name || copy.source}</External></li>)}</ul> : <p>{copy.noProvenance}</p>}</section></section>;
}

export function ChaptersPage() {
  const navigate = useNavigate();
  const [sections, setSections] = useState(FALLBACK_SECTIONS);
  const [chapters, setChapters] = useState(FALLBACK_CHAPTERS);
  const [openSections, setOpenSections] = useState(new Set());
  const [openChapters, setOpenChapters] = useState(new Set());
  const [query, setQuery] = useState('');
  const [indexState, setIndexState] = useState('loading');
  const [loadedFamilies, setLoadedFamilies] = useState({});
  useEffect(() => {
    let active = true;
    setIndexState('loading');
    Promise.all([api('/v1/sections'), api('/v1/chapters')])
      .then(([nextSections, nextChapters]) => {
        if (!active) return;
        // Rows are keyed by section and chapter code, so replacing the packaged
        // fallback keeps the controls a person already focused.
        if (nextSections.length) setSections(nextSections.map((section) => ({ ...section, roman: /^sección/i.test(section.roman) ? section.roman : `Sección ${section.roman}` })));
        if (nextChapters.length) setChapters(nextChapters);
        setIndexState('ready');
      })
      .catch(() => {
        if (active) setIndexState('fallback');
      });
    return () => { active = false; };
  }, []);
  // HS4 families come from each chapter's data file the first time it is opened.
  useEffect(() => {
    const pending = [...openChapters].filter((code) => !loadedFamilies[code]);
    if (!pending.length) return undefined;
    let active = true;
    pending.forEach((code) => {
      fetch(chapterDataUrl(code))
        .then((response) => (response.ok ? response.json() : Promise.reject(new Error('families unavailable'))))
        .then((records) => {
          if (active) setLoadedFamilies((current) => ({ ...current, [code]: records.filter((record) => record.level === 'hs4').map((record) => ({ code: formatCode(record.code), description: record.description })) }));
        })
        .catch(() => {});
    });
    return () => { active = false; };
  }, [loadedFamilies, openChapters]);
  const filtered = useMemo(() => chapters.filter((chapter) => `${chapter.code} ${chapter.description}`.toLowerCase().includes(query.toLowerCase())), [chapters, query]);
  useEffect(() => {
    if (!query.trim()) return;
    const matchingSections = new Set(sections.filter((section) => filtered.some((chapter) => Number(chapter.code) >= section.chapter_from && Number(chapter.code) <= section.chapter_to)).map((section) => section.roman));
    setOpenSections(matchingSections);
    setOpenChapters(new Set(filtered.slice(0, 8).map((chapter) => chapter.code)));
  }, [filtered, query, sections]);
  const toggle = (setter, key) => setter((current) => { const next = new Set(current); next.has(key) ? next.delete(key) : next.add(key); return next; });
  return <><PageHero page={EDITORIAL_PAGES['/chapters']}><Link className="button" to="/changes">Ver evidencia de fracciones</Link></PageHero><section className="workspace"><label htmlFor="chapter-query">Buscar capítulo, código o descripción</label><input id="chapter-query" type="search" value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Buscar capítulo, código o descripción"/><p className="status" role="status">{query.trim() ? `${filtered.length} capítulos coinciden y se expandieron mientras escribes.` : indexState === 'loading' ? 'Cargando el índice verificado de capítulos…' : indexState === 'fallback' ? 'Índice verificado no disponible. Se muestra la navegación incluida en el paquete.' : 'Índice verificado de capítulos cargado.'}</p><div className="accordion">{sections.map((section) => { const isOpen = openSections.has(section.roman); const rows = filtered.filter((chapter) => Number(chapter.code) >= section.chapter_from && Number(chapter.code) <= section.chapter_to); return <article key={section.roman}><button aria-expanded={isOpen} onClick={() => toggle(setOpenSections, section.roman)}><span>{section.roman} · {section.name}</span><span>{section.chapter_from}–{section.chapter_to} · {rows.length} visibles</span></button>{isOpen && <div className="accordion-panel">{rows.length ? rows.map((chapter) => { const isChapterOpen = openChapters.has(chapter.code); const families = loadedFamilies[chapter.code] || chapter.families || [{ code: `${chapter.code}.01`, description: 'Consultar familia HS4 en la release verificada' }]; return <article key={chapter.code}><button aria-expanded={isChapterOpen} onClick={() => toggle(setOpenChapters, chapter.code)}>Capítulo {chapter.code} · {chapter.description}</button>{isChapterOpen && <div className="accordion-panel">{families.map((family) => <button key={family.code} className="family-action" onClick={() => navigate(`/app?q=${encodeURIComponent(family.code)}`)}>Partida · familia HS4 {family.code} · {family.description}</button>)}</div>}</article>; }) : <p>Ningún capítulo verificado coincide con este filtro.</p>}</div>}</article>; })}</div></section></>;
}

const DofChangesPage = lazy(() => import('./dof-changes-page.jsx'));

export function ChangesPage() {
  const { language } = useLocale();
  return <Suspense fallback={<p className="status" role="status">{localize(language, 'Cargando los cambios publicados en el DOF…', 'Loading the changes published in the DOF…')}</p>}><DofChangesPage /></Suspense>;
}
export function MoaPage() { return <><PageHero page={EDITORIAL_PAGES['/moa']}><div className="hero-actions"><External href={OFFICIAL_LINKS.anamMoa}>Abrir Manual de ANAM</External><External href={OFFICIAL_LINKS.anamMoaPdf}>Ver documento enlazado por ANAM</External><External href={OFFICIAL_LINKS.anamMoaNotice}>Leer aviso oficial</External></div></PageHero><section className="card-grid">{MOA_GROUPS.map(([number, title, description, href]) => <article key={number}><span>{number}</span><h2>{title}</h2><p>{description}</p><External href={href}>Abrir fuente oficial</External></article>)}</section><section className="source-strip"><h2>Marco jurídico y versión</h2><External href={OFFICIAL_LINKS.law}>Ley Aduanera</External><External href={OFFICIAL_LINKS.anamNormativity}>Normatividad ANAM</External></section></>;
}

export function WikiPage() { return <><PageHero page={EDITORIAL_PAGES['/wiki']}><div className="hero-actions"><External href={OFFICIAL_LINKS.anamNormativity}>Abrir normatividad ANAM</External><External href={OFFICIAL_LINKS.anamGlossary}>Abrir glosario ANAM</External></div></PageHero><section className="card-grid">{WIKI_REFERENCES.map(([category, title, description, href]) => <article key={title}><span>{category}</span><h2>{title}</h2><p>{description}</p><External href={href}>Abrir fuente</External></article>)}</section><aside className="example-note"><h2>Cómo usar esta wiki</h2><p>Lee la fuente primaria completa y verifica su vigencia antes de usarla como contexto.</p><Link to="/glossary">Explorar glosario</Link></aside></>;
}

export function TradeContextPage() { return <><PageHero page={EDITORIAL_PAGES['/trade-context']}><External href={OFFICIAL_LINKS.inegi}>Abrir explicación completa de INEGI</External></PageHero><section className="flow-diagram" aria-label="Trade context"><article><strong>Importaciones</strong><span>Compra al exterior</span></article><span aria-hidden="true">+</span><article><strong>Exportaciones</strong><span>Venta al exterior</span></article><span aria-hidden="true">→</span><article><strong>Balanza</strong><span>Diferencia</span></article></section><section className="card-grid"><article><h2>Importaciones</h2><p>Mercancías adquiridas desde el exterior.</p></article><article><h2>Exportaciones</h2><p>Mercancías vendidas hacia otros mercados.</p></article><article><h2>Balanza comercial</h2><p>Relación entre importaciones y exportaciones.</p></article><article><h2>Entidades y socios</h2><p>Contexto por territorio y contraparte comercial.</p></article></section><aside className="example-note"><p>INEGI · BCMM 2013–2023 · ETEF 2024</p><p>Estados Unidos en 2023: 42.7% de importaciones y 79.4% de exportaciones.</p><External href={OFFICIAL_LINKS.inegi}>Consultar tablas, gráficas y mapa originales</External></aside></>;
}

export function DocumentationPage() {
  const { language } = useLocale();
  const t = (spanish, english) => localize(language, spanish, english);
  const [query, setQuery] = useState('');
  const links = DOCUMENTATION_LINKS.filter(([title]) => title.toLowerCase().includes(query.toLowerCase()));
  return <><PageHero page={editorialPage('/documentation', language)}><External href={OFFICIAL_LINKS.pypi}>{t('Instalar desde PyPI', 'Install from PyPI')}</External></PageHero><section className="workspace"><label htmlFor="docs-query">{t('Buscar en la documentación', 'Search documentation')}</label><input id="docs-query" value={query} onChange={(event) => setQuery(event.target.value)} placeholder={t('Buscar en la documentación', 'Search documentation')}/>{links.length ? <section className="card-grid">{links.map(([title, path]) => <article key={path}><h2>{title}</h2><p>{t('Lee el contrato público mantenido en el repositorio.', 'Read the maintained public contract in the repository.')}</p><External href={`${REPOSITORY}/blob/main/${path}`}>{t('Abrir documento', 'Open document')}</External></article>)}</section> : <aside className="empty-state" role="status"><h2>{t('Ninguna documentación coincide con', 'No documentation matches')} “{query}”.</h2><button className="button" onClick={() => setQuery('')}>{t('Borrar búsqueda', 'Clear search')}</button></aside>}</section></>;
}

export function TrustPage() {
  const { language } = useLocale();
  const t = (spanish, english) => localize(language, spanish, english);
  const steps = [['01', t('Fuentes registradas', 'Registered sources'), t('Cada fuente tiene un rol declarado y una procedencia registrada.', 'Each source has a declared role and recorded provenance.')], ['02', t('Conciliación de evidencia', 'Evidence reconciliation'), t('Los datos publicados se comparan con su evidencia.', 'Published data is compared against its evidence.')], ['03', t('Build que falla cerrado', 'Fail-closed build'), t('Si falta evidencia requerida, la release se detiene.', 'When required evidence is incomplete, the release stops.')], ['04', t('Verificación independiente', 'Independent verification'), t('Los artefactos exponen manifests, checksums e identidades de release.', 'Artifacts expose manifests, checksums and release identities.')]];
  return <><PageHero page={editorialPage('/trust', language)}><External href={`${REPOSITORY}/blob/main/docs/production-certification.md`}>{t('Leer la guía de verificación', 'Read verification guide')}</External></PageHero><section className="card-grid">{steps.map(([number, title, description]) => <article key={number}><span>{number}</span><h2>{title}</h2><p>{description}</p></article>)}</section><External href={OFFICIAL_LINKS.releases}>{t('Consultar releases públicas', 'Inspect public releases')}</External></>;
}

export function RecordsPage() {
  const { language } = useLocale();
  const t = (spanish, english) => localize(language, spanish, english);
  const [code, setCode] = useState('');
  const [records, setRecords] = useState(() => { try { return JSON.parse(localStorage.getItem(RECORDS_KEY) || '[]'); } catch { return []; } });
  const [status, setStatus] = useState('');
  const check = async (event) => { event.preventDefault(); const clean = code.replace(/\D/g, ''); if (!clean) return setStatus(t('Ingresa una fracción, NICO o código verificado.', 'Enter a verified fraction, NICO, or code.')); try { const record = await api(`/v1/lookup/${clean}`); const next = [{ ...record, savedAt: new Date().toISOString() }, ...records.filter((item) => item.code !== record.code)].slice(0, 50); localStorage.setItem(RECORDS_KEY, JSON.stringify(next)); setRecords(next); setStatus(`${t('Se preparó', 'Prepared')} ${record.code} ${t('para investigación local.', 'for local research.')}`); } catch { setStatus(t('Registro no disponible. Revisa el código verificado e inténtalo de nuevo.', 'Record unavailable. Check the verified code and try again.')); } };
  return <><PageHero page={editorialPage('/records', language)} /><section className="metric-grid"><article><strong>{records.length}</strong><span>{t('Guardados', 'Saved')}</span></article><article><strong>{records.length}</strong><span>{t('Listos para consultar', 'Ready to inspect')}</span></article><article><strong>{t('Solo local', 'Local only')}</strong><span>{t('No se comparte', 'Not shared')}</span></article></section><section className="workspace"><form onSubmit={check}><label htmlFor="record-query">{t('Código arancelario verificado', 'Verified tariff code')}</label><div className="inline-form"><input id="record-query" value={code} onChange={(event) => setCode(event.target.value)} placeholder={t('Fracción, NICO o código verificado', 'Fraction, NICO, or verified code')}/><button className="button primary">{t('Comprobar registro verificado', 'Check verified record')}</button></div></form><p role="status" aria-live="polite">{status}</p>{records.length ? <section className="result-list">{records.map((record) => <article key={record.code}><div><h2>{record.code}</h2><p>{record.description}</p></div><Link className="button" to={`/app/record/${record.code}`}>{t('Consultar', 'Inspect')}</Link></article>)}</section> : <aside className="empty-state"><h2>{t('Aún no hay registros locales', 'No local records yet')}</h2><p>{t('Comprueba un código verificado para preparar tu investigación local.', 'Check a verified code to prepare local research.')}</p></aside>}</section></>;
}
export function TradeDeskPage() { return <section className="empty-state"><h1>Mesa de comercio exterior</h1><p>Esta ruta conserva una superficie independiente con simulación orientativa, T-MEC, RRNA y trazabilidad local.</p><a className="button primary" href="/trade">Abrir mesa</a></section>; }

// Secondary entry points (kept as routes for old links); each one points at the real pages.
const MARKETING_COPY = {
  '/features': { eyebrow: ['SUPERFICIES DEL PRODUCTO', 'PRODUCT SURFACES'], title: ['Construye sobre datos arancelarios verificables.', 'Build on verifiable tariff data.'], description: ['Explora las superficies públicas del producto, sus límites documentados y los artefactos de cada release.', 'Explore the public product surfaces, documented limits and release artifacts.'], action: ['/documentation', 'Leer la documentación', 'Read documentation'] },
  '/pricing': { eyebrow: ['RELEASES ABIERTOS', 'OPEN DATA RELEASES'], title: ['Releases públicos, artefactos inspeccionables.', 'Public releases, inspectable artifacts.'], description: ['Los datos centrales y los materiales de verificación se pueden revisar abiertamente.', 'The core data and verification materials remain openly inspectable.'], action: ['/trust', 'Leer el modelo de confianza', 'Read trust model'] },
  '/analytics': { eyebrow: ['CONTEXTO DEL RELEASE', 'RELEASE ANALYTICS'], title: ['Contexto del release sin puntajes opacos.', 'Release context without opaque scoring.'], description: ['Revisa un release a través de evidencia visible y del rol de cada fuente.', 'Inspect a release through visible evidence and source roles.'], action: ['/changes', 'Ver los cambios del DOF', 'Inspect release evidence'] },
  '/community': { eyebrow: ['COMUNIDAD ABIERTA', 'OPEN COMMUNITY'], title: ['Contribuye con evidencia visible.', 'Contribute through visible evidence.'], description: ['Usa el repositorio público para revisar, discutir y mejorar el contrato de datos abiertos.', 'Use the public repository to review, discuss and improve the open data contract.'], action: ['/documentation', 'Abrir la documentación', 'Open documentation'] },
};

function MarketingPage({ path }) {
  const { language } = useLocale();
  const t = (spanish, english) => localize(language, spanish, english);
  const page = MARKETING_COPY[path];
  const [href, actionEs, actionEn] = page.action;
  const disclaimer = t('Consulta la release, el repositorio y la documentación antes de basar una integración en estos materiales.', 'Check the release, the repository and the documentation before basing an integration on these materials.');
  return <><PageHero page={{ eyebrow: t(...page.eyebrow), title: t(...page.title), description: t(...page.description), disclaimer }}><Link className="button primary" to={href}>{t(actionEs, actionEn)}</Link></PageHero><section className="card-grid"><article><h2>{t('Evidencia del release', 'Release evidence')}</h2><p>{t('Inspecciona artefactos versionados, manifest y checksums.', 'Inspect versioned artifacts, the manifest and checksums.')}</p><External href={OFFICIAL_LINKS.releases}>{t('Abrir releases', 'Open releases')}</External></article><article><h2>{t('Contrato de fuentes', 'Source contract')}</h2><p>{t('Revisa los límites de la API pública y de los datos verificados.', 'Review the limits of the public API and of the verified data.')}</p><Link to="/documentation">{t('Leer la documentación', 'Read documentation')}</Link></article><article><h2>{t('Participación abierta', 'Open participation')}</h2><p>{t('El trabajo se organiza en el repositorio público y sus discusiones.', 'The work is organised in the public repository and its discussions.')}</p><External href={OFFICIAL_LINKS.github}>{t('Abrir GitHub', 'Open GitHub')}</External></article></section></>;
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
  '/features': () => <MarketingPage path="/features" />,
  '/pricing': () => <MarketingPage path="/pricing" />,
  '/analytics': () => <MarketingPage path="/analytics" />,
  '/community': () => <MarketingPage path="/community" />,
};
