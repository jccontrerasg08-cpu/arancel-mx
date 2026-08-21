import { useEffect, useRef, useState } from 'react';
import { BrowserRouter, Link, Route, Routes, useLocation } from 'react-router-dom';

import { EDITORIAL_PAGES, NAVIGATION, OFFICIAL_LINKS } from './content.js';
import { PAGE_COMPONENTS } from './pages.jsx';

function ThemeToggle() {
  const [theme, setTheme] = useState(() => localStorage.getItem('theme') || 'light');
  useEffect(() => {
    document.documentElement.dataset.theme = theme;
    localStorage.setItem('theme', theme);
  }, [theme]);
  return <button className="icon-button" type="button" onClick={() => setTheme((current) => current === 'light' ? 'dark' : 'light')} aria-label={`Use ${theme === 'light' ? 'dark' : 'light'} theme`}>{theme === 'light' ? '◐' : '◑'}</button>;
}

function SiteHeader() {
  const [open, setOpen] = useState(false);
  const toggleRef = useRef(null);
  const location = useLocation();
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
  return <><a className="skip-link" href="#main-content">Skip to content</a><header className="site-header"><div className="site-header__inner"><Link className="brand" to="/">arancel<span>.mx</span></Link><button ref={toggleRef} className="nav-toggle" type="button" aria-expanded={open} aria-controls="site-navigation" onClick={() => setOpen((current) => !current)}>{open ? 'Close navigation menu' : 'Open navigation menu'}</button><nav id="site-navigation" className={open ? 'site-nav is-open' : 'site-nav'} aria-label="Primary navigation">{NAVIGATION.map(([label, href]) => <Link key={href} className={location.pathname === href ? 'is-active' : ''} to={href}>{label}</Link>)}</nav><div className="site-header__actions"><ThemeToggle/><a className="github-link" href={OFFICIAL_LINKS.github} target="_blank" rel="noreferrer">GitHub <span aria-label="open issues">0</span></a></div></div></header></>;
}

function SiteFooter() {
  return <footer className="site-footer"><div><strong>arancel.mx</strong><p>Verified Mexican tariff data with visible release evidence.</p></div><nav aria-label="Footer navigation">{NAVIGATION.slice(0, 8).map(([label, href]) => <Link key={href} to={href}>{label}</Link>)}</nav><div><a href={OFFICIAL_LINKS.github} target="_blank" rel="noreferrer">GitHub</a><a href={OFFICIAL_LINKS.pypi} target="_blank" rel="noreferrer">PyPI 0.3.5</a><p>© 2026 arancel-mx · Apache-2.0</p></div></footer>;
}

function RoutedPage({ Component }) {
  const location = useLocation();
  useEffect(() => {
    const page = EDITORIAL_PAGES[location.pathname];
    document.title = `arancel-mx — ${page?.title || 'Verified Mexican tariff data'}`;
    const description = document.querySelector('meta[name="description"]');
    if (description) description.setAttribute('content', page?.description || 'Datos arancelarios mexicanos verificables.');
  }, [location.pathname]);
  return <main id="main-content" tabIndex="-1"><Component /></main>;
}

export function App() {
  return <BrowserRouter><SiteHeader/><Routes>{Object.entries(PAGE_COMPONENTS).map(([path, Component]) => <Route key={path} path={path} element={<RoutedPage Component={Component} />} />)}<Route path="/product" element={<RoutedPage Component={PAGE_COMPONENTS['/app']} />}/><Route path="/app/chapter/:code" element={<RoutedPage Component={PAGE_COMPONENTS['/app/record/:code']} />}/></Routes><SiteFooter/></BrowserRouter>;
}
