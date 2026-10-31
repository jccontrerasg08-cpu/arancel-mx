import { useEffect, useMemo, useRef, useState } from 'react';
import { useLocation, useNavigate } from 'react-router-dom';

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

// Quick search: Ctrl/⌘+K or "/" opens it from any page. It reuses the explorer's
// verified search, so a result always leads to a verified record.
export function CommandPalette() {
  const { language } = useLocale();
  const navigate = useNavigate();
  const location = useLocation();
  const [open, setOpen] = useState(false);
  const [query, setQuery] = useState('');
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [active, setActive] = useState(0);
  const inputRef = useRef(null);
  const closeRef = useRef(null);
  const returnFocus = useRef(null);
  const generation = useRef(0);
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
      setResults([]);
      setActive(0);
      inputRef.current?.focus();
    } else if (returnFocus.current instanceof HTMLElement) {
      returnFocus.current.focus();
    }
  }, [open]);

  useEffect(() => {
    const candidate = query.trim();
    const current = ++generation.current;
    if (!open || !candidate) {
      setResults([]);
      setLoading(false);
      return undefined;
    }
    setLoading(true);
    const controller = new AbortController();
    const timer = window.setTimeout(() => {
      dataClient.request(`/v1/search?q=${encodeURIComponent(candidate)}&limit=8`, controller.signal)
        .then((found) => selectPrimarySearchResults(found, candidate).slice(0, 8))
        .catch(() => searchExampleRecords(candidate).slice(0, 8))
        .then((found) => {
          if (current !== generation.current) return;
          setResults(found);
          setLoading(false);
        });
    }, 150);
    return () => {
      window.clearTimeout(timer);
      controller.abort();
    };
  }, [open, query]);

  const items = useMemo(() => {
    const source = query.trim() ? results : VERIFIED_EXAMPLES;
    return source.map((entry) => entry.record || entry).filter((record) => record?.code);
  }, [query, results]);
  useEffect(() => setActive(0), [items]);

  if (!open) return null;

  const choose = (index) => {
    const record = items[index];
    if (record) navigate(`/app/record/${record.code}`);
    else if (query.trim()) navigate(`/app?q=${encodeURIComponent(query.trim())}`);
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
      choose(items.length ? active : -1);
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
  const searching = Boolean(query.trim());
  const levelName = (code) => levels[String(code).replace(/\D/g, '').length] || '';

  return <div className="palette-backdrop" onMouseDown={(event) => { if (event.target === event.currentTarget) setOpen(false); }}>
    <div className="palette" role="dialog" aria-modal="true" aria-label={t('Búsqueda rápida', 'Quick search')} onKeyDown={onKeyDown}>
      <div className="palette__bar">
        <svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg>
        <input ref={inputRef} type="search" role="combobox" aria-expanded="true" aria-controls="palette-list" aria-activedescendant={items.length ? `palette-option-${active}` : undefined} aria-label={t('Código o descripción', 'Code or description')} autoComplete="off" value={query} onChange={(event) => setQuery(event.target.value)} placeholder={t('Código o descripción…', 'Code or description…')}/>
        <button ref={closeRef} type="button" className="palette__close" onClick={() => setOpen(false)}>{t('Cerrar', 'Close')}</button>
      </div>
      <p className="palette__label">{searching ? t('Resultados verificados', 'Verified results') : t('Ejemplos verificados', 'Verified examples')}</p>
      <ul id="palette-list" role="listbox" aria-label={t('Resultados', 'Results')} aria-busy={loading}>
        {loading && !items.length && [0, 1, 2].map((row) => <li key={row} className="palette__skeleton" aria-hidden="true"><span/><span/></li>)}
        {items.map((record, index) => <li key={record.code} id={`palette-option-${index}`} role="option" aria-selected={index === active} className={index === active ? 'is-active' : undefined} onMouseEnter={() => setActive(index)} onClick={() => choose(index)}>
          <code>{formatCode(record.code)}</code>
          <span><strong>{record.description}</strong><small>{levelName(record.code)}</small></span>
        </li>)}
      </ul>
      {searching && !loading && !items.length && <p className="palette__empty">{t('Ninguna ruta verificada coincide. Pulsa Enter para buscar en el explorador.', 'No verified path matches. Press Enter to search in the explorer.')}</p>}
      <p className="palette__hint"><kbd>↑</kbd><kbd>↓</kbd> {t('moverse', 'move')} · <kbd>Enter</kbd> {t('abrir', 'open')} · <kbd>Esc</kbd> {t('cerrar', 'close')}</p>
      <div className="sr-only" aria-live="polite">{searching && !loading ? `${items.length} ${t('resultados', 'results')}` : ''}</div>
    </div>
  </div>;
}
