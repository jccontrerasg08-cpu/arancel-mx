import { useEffect, useMemo, useRef, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';

import { findPaletteCommands } from './palette-commands.js';
import { useLocale } from './locale.jsx';
import { DATA_BASE } from './pages.jsx';
import { createStaticApi } from './static-api.js';
import { selectPrimarySearchResults } from './tariff.js';
import { formatCode, searchExampleRecords, VERIFIED_EXAMPLES } from './verified-examples.js';

const dataClient = createStaticApi({ base: DATA_BASE });

export const OPEN_SEARCH_EVENT = 'arancel:open-search';
export const shortcutLabel = () => (/Mac|iPhone|iPad/.test(navigator.platform) ? '⌘K' : 'Ctrl K');

const LEVEL_NAMES = {
  es: { 2: 'Capítulo', 4: 'Partida', 6: 'Subpartida', 8: 'Fracción', 10: 'NICO' },
  en: { 2: 'Chapter', 4: 'Heading', 6: 'Subheading', 8: 'Fraction', 10: 'NICO' },
};

const isTyping = (target) => /^(INPUT|TEXTAREA|SELECT)$/.test(target?.tagName || '') || Boolean(target?.isContentEditable);

// Quick search combines local destinations with the explorer's verified records.
export function CommandPalette() {
  const { language, copy } = useLocale();
  const navigate = useNavigate();
  const location = useLocation();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [search, setSearch] = useState(null);
  const [active, setActive] = useState(0);
  const inputRef = useRef(null);
  const closeRef = useRef(null);
  const returnFocus = useRef(null);
  const t = (spanish, english) => (language === 'en' ? english : spanish);
  const levels = LEVEL_NAMES[language === 'en' ? 'en' : 'es'];

  useEffect(() => {
    const show = () => {
      returnFocus.current = document.activeElement;
      setOpen(true);
    };
    const onKeyDown = (event) => {
      if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'k') {
        event.preventDefault();
        setOpen((current) => {
          if (!current) returnFocus.current = document.activeElement;
          return !current;
        });
      } else if (event.key === '/' && !event.ctrlKey && !event.metaKey && !event.altKey && !isTyping(event.target)) {
        event.preventDefault();
        show();
      }
    };
    window.addEventListener('keydown', onKeyDown);
    window.addEventListener(OPEN_SEARCH_EVENT, show);
    return () => {
      window.removeEventListener('keydown', onKeyDown);
      window.removeEventListener(OPEN_SEARCH_EVENT, show);
    };
  }, []);

  useEffect(() => setOpen(false), [location.pathname, location.search]);

  useEffect(() => {
    if (open) {
      setQuery('');
      setSearch(null);
      setActive(0);
      inputRef.current?.focus();
    } else if (returnFocus.current instanceof HTMLElement) {
      returnFocus.current.focus();
    }
  }, [open]);

  const candidate = query.trim();
  useEffect(() => {
    if (!open || !candidate) return undefined;
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      dataClient.request(`/v1/search?q=${encodeURIComponent(candidate)}&limit=8`, controller.signal)
        .then((found) => selectPrimarySearchResults(found, candidate).slice(0, 8))
        .catch(() => searchExampleRecords(candidate).slice(0, 8))
        .then((results) => {
          if (!controller.signal.aborted) setSearch({ candidate, results });
        });
    }, 150);
    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [open, candidate]);

  const loading = Boolean(candidate && search?.candidate !== candidate);
  const items = useMemo(() => {
    const commands = findPaletteCommands(candidate, copy.navigation);
    const source = candidate ? (search?.candidate === candidate ? search.results : []) : VERIFIED_EXAMPLES;
    const records = source.map((entry) => entry.record || entry).filter((record) => record?.code);
    return [...commands, ...records];
  }, [candidate, copy.navigation, search]);
  const activeIndex = Math.min(active, Math.max(items.length - 1, 0));

  if (!open) return null;

  const choose = (index) => {
    const item = items[index];
    setOpen(false);
    if (item?.standalone) window.location.assign(item.href);
    else if (item?.href) navigate(item.href);
    else if (item?.code) navigate(`/app/record/${item.code}`);
    else if (candidate) navigate(`/app?q=${encodeURIComponent(candidate)}`);
  };
  const onKeyDown = (event) => {
    if (event.key === 'Escape') {
      event.preventDefault();
      setOpen(false);
    } else if (event.key === 'ArrowDown') {
      event.preventDefault();
      setActive((current) => Math.min(current + 1, Math.max(items.length - 1, 0)));
    } else if (event.key === 'ArrowUp') {
      event.preventDefault();
      setActive((current) => Math.max(current - 1, 0));
    } else if (event.key === 'Enter' && event.target === inputRef.current) {
      event.preventDefault();
      choose(items.length ? activeIndex : -1);
    } else if (event.key === 'Tab') {
      const first = inputRef.current;
      const last = closeRef.current;
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }
  };
  const onQueryChange = (event) => {
    const value = event.target.value;
    setQuery(value);
    setActive(0);
    if (value.trim() !== candidate) setSearch(null);
  };
  const searching = Boolean(candidate);
  const levelName = (code) => levels[String(code).replace(/\D/g, '').length] || '';

  return <div className="palette-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) setOpen(false); }}>
    <div className="palette" role="dialog" aria-modal="true" aria-label={t('Búsqueda rápida', 'Quick search')} onKeyDown={onKeyDown}>
      <div className="palette__bar">
        <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg>
        <input ref={inputRef} type="search" role="combobox" aria-expanded="true" aria-controls="palette-list" aria-activedescendant={items.length ? `palette-option-${activeIndex}` : undefined} aria-label={t('Código, descripción o comando', 'Code, description or command')} autoComplete="off" value={query} onChange={onQueryChange} placeholder={t('Código, descripción o comando…', 'Code, description or command…')}/>
        <button ref={closeRef} type="button" className="palette__close" onClick={() => setOpen(false)}>{t('Cerrar', 'Close')}</button>
      </div>
      <p className="palette__label">{searching ? t('Resultados', 'Results') : t('Módulos y ejemplos verificados', 'Modules and verified examples')}</p>
      <ul id="palette-list" role="listbox" aria-label={t('Resultados', 'Results')} aria-busy={loading && !items.length}>
        {loading && !items.length && [0, 1, 2].map((row) => <li key={row} className="palette__skeleton" aria-hidden="true"><span/><span/></li>)}
        {items.map((item, index) => <li key={item.href || item.code} id={`palette-option-${index}`} role="option" aria-selected={index === activeIndex} className={index === activeIndex ? 'is-active' : undefined} onMouseEnter={() => setActive(index)} onClick={() => choose(index)}>
          {item.href
            ? <span><strong>{item.label}</strong><small>{t('Ir a una página', 'Go to a page')}</small></span>
            : <><code>{formatCode(item.code)}</code><span><strong>{item.description}</strong><small>{levelName(item.code)}</small></span></>}
        </li>)}
      </ul>
      {searching && !loading && !items.length && <p className="palette__empty">{t('Sin resultados. Pulsa Enter para buscar en el explorador.', 'No results. Press Enter to search in the explorer.')}</p>}
      <p className="palette__hint"><kbd>↑</kbd><kbd>↓</kbd> {t('moverse', 'move')} · <kbd>Enter</kbd> {t('abrir', 'open')} · <kbd>Esc</kbd> {t('cerrar', 'close')}</p>
      <div className="sr-only" aria-live="polite">{searching && (!loading || items.length) ? `${items.length} ${t('resultados', 'results')}` : ''}</div>
    </div>
  </div>;
}
