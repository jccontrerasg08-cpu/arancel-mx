import { lazy, Suspense, useEffect, useRef, useState } from 'react';
import { createBrowserRouter, createRoutesFromElements, Link, Outlet, Route, RouterProvider, useLocation } from 'react-router-dom';

import { editorialPage, NAV_GROUPS, NAVIGATION, OFFICIAL_LINKS } from './content.js';
import { CommandPalette, OPEN_SEARCH_EVENT, shortcutLabel } from './command-palette.jsx';
import { LocaleProvider, useLocale } from './locale.jsx';
import { applyPageMeta, DEFAULT_SUMMARY, recordMetaFor } from './page-meta.js';
import { PAGE_COMPONENTS } from './pages.jsx';
import brandLogo from '../../src/arancel_mx/api/static/site/assets/arancel-mx-logo.svg';

const GlossaryPage = lazy(() => import('./glossary-page.jsx'));
const DataPage = lazy(() => import('./data-page.jsx'));
const DofChangeDetail = lazy(() => import('./dof-change-detail.jsx'));

function ThemeToggle() {
  const [theme, setTheme] = useState(() => localStorage.getItem('theme') || 'light');
  const { copy } = useLocale();
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem('theme', theme);
  }, [theme]);
  return <button className="icon-button" type="button" onClick={() => setTheme((current) => current === 'light' ? 'dark' : 'light')} aria-label={theme === 'light' ? copy.header.themeDark : copy.header.themeLight}>{theme === 'light' ? '◐' : '◑'}</button>;
}

function LanguageToggle() {
  const { language, setLanguage, copy } = useLocale();
  return <label className="language-toggle"><span className="sr-only">{copy.header.language}</span><select aria-label={copy.header.language} value={language} onChange={(event) => setLanguage(event.target.value)}><option value="es">ES</option><option value="en">EN</option></select></label>;
}

function useMediaQuery(query) {
  const [matches, setMatches] = useState(() => window.matchMedia(query).matches);
  useEffect(() => {
    const media = window.matchMedia(query);
    const update = () => setMatches(media.matches);
    update();
    media.addEventListener('change', update);
    return () => media.removeEventListener('change', update);
  }, [query]);
  return matches;
}

function NavMenu({ group, pathname }) {
  const { copy } = useLocale();
  const [open, setOpen] = useState(false);
  const rootRef = useRef(null);
  const buttonRef = useRef(null);
  const id = `nav-menu-${group.id}`;
  useEffect(() => setOpen(false), [pathname]);
  useEffect(() => {
    if (!open) return undefined;
    const closeOutside = (event) => { if (!rootRef.current?.contains(event.target)) setOpen(false); };
    const closeWithEscape = (event) => {
      if (event.key !== 'Escape') return;
      setOpen(false);
      buttonRef.current?.focus();
    };
    document.addEventListener('pointerdown', closeOutside);
    document.addEventListener('keydown', closeWithEscape);
    return () => {
      document.removeEventListener('pointerdown', closeOutside);
      document.removeEventListener('keydown', closeWithEscape);
    };
  }, [open]);
  return <div className="nav-menu" ref={rootRef}><button ref={buttonRef} type="button" className={group.items.includes(pathname) ? 'is-active' : ''} aria-expanded={open} aria-controls={id} onClick={() => setOpen((current) => !current)}>{copy.navGroups[group.id]}<span className="nav-menu__chevron" aria-hidden="true"/></button>{open && <ul id={id} className="nav-menu__panel">{group.items.map((href) => <li key={href}><Link to={href} viewTransition className={pathname === href ? 'is-active' : ''} aria-current={pathname === href ? 'page' : undefined}>{copy.navigation[href]}</Link></li>)}</ul>}</div>;
}

function SiteHeader() {
  const [open, setOpen] = useState(false);
  const toggleRef = useRef(null);
  const location = useLocation();
  const { copy } = useLocale();
  const compact = useMediaQuery('(max-width: 900px)');
  const link = (href, label) => <Link key={href} className={location.pathname === href || (href === '/app' && location.pathname.startsWith('/app')) ? 'is-active' : ''} to={href} viewTransition>{label}</Link>;
  useEffect(() => setOpen(false), [location.pathname]);
  useEffect(() => {
    const closeWithEscape = (event) => {
      if (event.key !== 'Escape') return;
      setOpen(false);
      toggleRef.current?.focus();
    };
    window.addEventListener('keydown', closeWithEscape);
    return () => window.removeEventListener('keydown', closeWithEscape);
  }, []);
  const groups = compact
    ? <>{NAV_GROUPS.map((group) => group.href ? link(group.href, copy.navGroups[group.id]) : <div className="nav-section" key={group.id}><p className="nav-section__label">{copy.navGroups[group.id]}</p>{group.items.map((href) => link(href, copy.navigation[href]))}</div>)}{link('/records', copy.navigation['/records'])}</>
    : <>{NAV_GROUPS.map((group) => group.href ? link(group.href, copy.navGroups[group.id]) : <NavMenu key={group.id} group={group} pathname={location.pathname}/>)}</>;
  return <><a className="skip-link" href="#main-content">{copy.header.skip}</a><header className="site-header"><div className="site-header__inner"><Link className="brand-lockup" to="/" aria-label="arancel.mx" viewTransition><img src={brandLogo} alt=""/></Link><button ref={toggleRef} className="nav-toggle" type="button" aria-label={open ? copy.header.close : copy.header.open} aria-expanded={open} aria-controls="site-navigation" onClick={() => setOpen((current) => !current)}><span aria-hidden="true">{open ? '×' : '☰'}</span></button><nav id="site-navigation" className={open ? 'site-nav is-open' : 'site-nav'} aria-label={copy.header.navigation}>{groups}</nav><div className="site-header__actions"><button className="search-trigger" type="button" aria-label={copy.header.searchOpen} onClick={() => window.dispatchEvent(new CustomEvent(OPEN_SEARCH_EVENT))}><svg viewBox="0 0 24 24" aria-hidden="true"><circle cx="11" cy="11" r="7"/><path d="m20 20-3.5-3.5"/></svg><span className="search-trigger__label" aria-hidden="true">{copy.header.search}</span><kbd aria-hidden="true">{shortcutLabel()}</kbd></button><Link className="records-link" to="/records">{copy.navigation['/records']}</Link><LanguageToggle/><ThemeToggle/><a className="github-link" href={OFFICIAL_LINKS.github} target="_blank" rel="noreferrer">GitHub</a></div></div></header></>;
}
function SiteFooter() {
  const { copy } = useLocale();
  return <footer className="site-footer"><div><strong>arancel.mx</strong><p>{copy.footer.description}</p></div><nav aria-label="Footer navigation">{NAVIGATION.slice(0, 9).map(([, href]) => <Link key={href} to={href}>{copy.navigation[href] || href}</Link>)}</nav><div><a href={OFFICIAL_LINKS.github} target="_blank" rel="noreferrer">GitHub</a><a href={OFFICIAL_LINKS.pypi} target="_blank" rel="noreferrer">PyPI · latest</a><p>© 2026 arancel-mx · Apache-2.0</p></div></footer>;
}

function NotFoundPage() {
  return <section className="empty-state"><h1>Page not found</h1><p>The requested public route is not available in this release.</p><Link className="button primary" to="/app">Open explorer</Link></section>;
}

function DeferredGlossaryPage() {
  return <Suspense fallback={<p className="status" role="status">Loading glossary…</p>}><GlossaryPage /></Suspense>;
}

function DeferredDataPage() {
  return <Suspense fallback={<p className="status" role="status">Cargando cifras…</p>}><DataPage /></Suspense>;
}

function DeferredChangeDetail() {
  return <Suspense fallback={<p className="status" role="status">Cargando la publicación…</p>}><DofChangeDetail /></Suspense>;
}

function RoutedPage({ Component }) {
  const location = useLocation();
  const { language, copy } = useLocale();
  useEffect(() => {
    const localizedRoute = ['/', '/app', '/product', '/documentation', '/trust', '/records', '/changes', '/data'].includes(location.pathname) || location.pathname.startsWith('/changes/') || location.pathname.startsWith('/app/record/') || location.pathname.startsWith('/app/chapter/');
    document.documentElement.lang = localizedRoute && language === 'en' ? 'en' : 'es-MX';
    const page = editorialPage(location.pathname, language);
    const record = recordMetaFor(location.pathname);
    applyPageMeta({
      pathname: location.pathname,
      title: record?.title || (location.pathname === '/' ? `${copy.home.title}${copy.home.titleEmphasis}` : page?.title || DEFAULT_SUMMARY),
      summary: record?.summary || page?.description || DEFAULT_SUMMARY,
      locale: language === 'en' && localizedRoute ? 'en_US' : 'es_MX',
    });
  }, [copy.home, language, location.pathname]);
  return <main id="main-content" tabIndex="-1"><Component /></main>;
}

// A data router (rather than <BrowserRouter>) is what lets <Link viewTransition> animate navigation.
function SiteLayout() {
  return <><SiteHeader/><CommandPalette/><Outlet/><SiteFooter/></>;
}

const router = createBrowserRouter(createRoutesFromElements(<Route element={<SiteLayout/>}>{Object.entries(PAGE_COMPONENTS).map(([path, Component]) => <Route key={path} path={path} element={<RoutedPage Component={Component} />} />)}<Route path="/glossary" element={<RoutedPage Component={DeferredGlossaryPage} />}/><Route path="/data" element={<RoutedPage Component={DeferredDataPage} />}/><Route path="/changes/:id" element={<RoutedPage Component={DeferredChangeDetail} />}/><Route path="/product" element={<RoutedPage Component={PAGE_COMPONENTS['/app']} />}/><Route path="/app/chapter/:code" element={<RoutedPage Component={PAGE_COMPONENTS['/app/record/:code']} />}/><Route path="*" element={<RoutedPage Component={NotFoundPage} />}/></Route>));

export function App() {
  return <LocaleProvider><RouterProvider router={router}/></LocaleProvider>;
}
