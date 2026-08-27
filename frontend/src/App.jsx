import { lazy, Suspense, useEffect, useRef, useState } from 'react';
import { BrowserRouter, Link, Route, Routes, useLocation } from 'react-router-dom';

import { EDITORIAL_PAGES, NAVIGATION, OFFICIAL_LINKS } from './content.js';
import { LocaleProvider, useLocale } from './locale.jsx';
import { PAGE_COMPONENTS } from './pages.jsx';
import brandLogo from '../../website/assets/arancel-mx-logo.svg';

const GlossaryPage = lazy(() => import('./glossary-page.jsx'));

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

function SiteHeader() {
  const [open, setOpen] = useState(false);
  const toggleRef = useRef(null);
  const location = useLocation();
  const { copy } = useLocale();
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
  return <><a className="skip-link" href="#main-content">{copy.header.skip}</a><header className="site-header"><div className="site-header__inner"><Link className="brand-lockup" to="/" aria-label="arancel.mx"><img src={brandLogo} alt=""/></Link><button ref={toggleRef} className="nav-toggle" type="button" aria-label={open ? copy.header.close : copy.header.open} aria-expanded={open} aria-controls="site-navigation" onClick={() => setOpen((current) => !current)}><span aria-hidden="true">{open ? '×' : '☰'}</span></button><nav id="site-navigation" className={open ? 'site-nav is-open' : 'site-nav'} aria-label={copy.header.navigation}>{NAVIGATION.map(([, href]) => <Link key={href} className={location.pathname === href ? 'is-active' : ''} to={href}>{copy.navigation[href] || href}</Link>)}</nav><div className="site-header__actions"><LanguageToggle/><ThemeToggle/><a className="github-link" href={OFFICIAL_LINKS.github} target="_blank" rel="noreferrer">GitHub <span aria-label="open issues">0</span></a></div></div></header></>;
}

function SiteFooter() {
  const { copy } = useLocale();
  return <footer className="site-footer"><div><strong>arancel.mx</strong><p>{copy.footer.description}</p></div><nav aria-label="Footer navigation">{NAVIGATION.slice(0, 8).map(([, href]) => <Link key={href} to={href}>{copy.navigation[href] || href}</Link>)}</nav><div><a href={OFFICIAL_LINKS.github} target="_blank" rel="noreferrer">GitHub</a><a href={OFFICIAL_LINKS.pypi} target="_blank" rel="noreferrer">PyPI · latest</a><p>© 2026 arancel-mx · Apache-2.0</p></div></footer>;
}

function NotFoundPage() {
  return <section className="empty-state"><h1>Page not found</h1><p>The requested public route is not available in this release.</p><Link className="button primary" to="/app">Open explorer</Link></section>;
}

function DeferredGlossaryPage() {
  return <Suspense fallback={<p className="status" role="status">Loading glossary…</p>}><GlossaryPage /></Suspense>;
}

function RoutedPage({ Component }) {
  const location = useLocation();
  const { language, copy } = useLocale();
  useEffect(() => {
    const localizedRoute = ['/', '/app', '/product', '/documentation'].includes(location.pathname) || location.pathname.startsWith('/app/record/') || location.pathname.startsWith('/app/chapter/');
    document.documentElement.lang = localizedRoute && language === 'en' ? 'en' : 'es-MX';
    const page = EDITORIAL_PAGES[location.pathname];
    document.title = `arancel-mx — ${location.pathname === '/' ? `${copy.home.title}${copy.home.titleEmphasis}` : page?.title || 'Datos arancelarios mexicanos verificables.'}`;
    const description = document.querySelector('meta[name="description"]');
    if (description) description.setAttribute('content', page?.description || 'Datos arancelarios mexicanos verificables.');
  }, [copy.home, language, location.pathname]);
  return <main id="main-content" tabIndex="-1"><Component /></main>;
}

export function App() {
  return <LocaleProvider><BrowserRouter><SiteHeader/><Routes>{Object.entries(PAGE_COMPONENTS).map(([path, Component]) => <Route key={path} path={path} element={<RoutedPage Component={Component} />} />)}<Route path="/glossary" element={<RoutedPage Component={DeferredGlossaryPage} />}/><Route path="/product" element={<RoutedPage Component={PAGE_COMPONENTS['/app']} />}/><Route path="/app/chapter/:code" element={<RoutedPage Component={PAGE_COMPONENTS['/app/record/:code']} />}/><Route path="*" element={<RoutedPage Component={NotFoundPage} />}/></Routes><SiteFooter/></BrowserRouter></LocaleProvider>;
}
