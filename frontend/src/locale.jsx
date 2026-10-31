import { createContext, useContext, useEffect, useMemo, useState } from 'react';

const LOCALES = {
  es: {
    navigation: { '/app': 'Explorar', '/chapters': 'Capítulos', '/changes': 'Cambios', '/moa': 'Guía MOA', '/wiki': 'Wiki', '/glossary': 'Glosario', '/trade-context': 'Contexto comercial', '/documentation': 'Documentación', '/trust': 'Confianza', '/records': 'Mis registros' },
    navGroups: { explore: 'Explorar', learn: 'Aprender', data: 'Datos', trust: 'Confianza' },
    header: { search: 'Búsqueda rápida', searchOpen: 'Abrir búsqueda rápida', skip: 'Saltar al contenido', open: 'Abrir menú de navegación', close: 'Cerrar menú de navegación', navigation: 'Navegación principal', language: 'Idioma de la interfaz', themeLight: 'Usar tema claro', themeDark: 'Usar tema oscuro' },
    footer: { description: 'Datos arancelarios mexicanos verificables con evidencia de release visible.' },
    home: { verified: 'verificada', title: 'Consulta el arancel de México, ', titleEmphasis: 'con su evidencia.', description: 'Busca por código o por nombre. Cada resultado muestra su release, su jerarquía y su fuente oficial.', searchLabel: 'Busca un código o descripción', searchPlaceholder: 'p. ej. 8517.13.01 o teléfonos', submit: 'Buscar', tryWith: 'Prueba con', metrics: [['8,183', 'Fracciones mexicanas'], ['11,507', 'Códigos NICO'], ['Diario', 'verificación de release'], ['Apache-2.0', 'núcleo abierto']], startTitle: 'Elige por dónde empezar', tiles: [['Busca un código y recorre su jerarquía.', '/app', 'explore'], ['Glosario, wiki y guía MOA, con índice A–Z.', '/glossary', 'learn'], ['Releases, cambios y documentación.', '/changes', 'data'], ['De dónde sale cada dato y cómo se verifica.', '/trust', 'trust']] },
  },
  en: {
    navigation: { '/app': 'Explorer', '/chapters': 'Chapters', '/changes': 'Changes', '/moa': 'MOA guide', '/wiki': 'Wiki', '/glossary': 'Glossary', '/trade-context': 'Trade context', '/documentation': 'Documentation', '/trust': 'Trust', '/records': 'My records' },
    navGroups: { explore: 'Explore', learn: 'Learn', data: 'Data', trust: 'Trust' },
    header: { search: 'Quick search', searchOpen: 'Open quick search', skip: 'Skip to content', open: 'Open navigation menu', close: 'Close navigation menu', navigation: 'Primary navigation', language: 'Interface language', themeLight: 'Use light theme', themeDark: 'Use dark theme' },
    footer: { description: 'Verified Mexican tariff data with visible release evidence.' },
    home: { verified: 'verified', title: 'Look up Mexico’s tariff, ', titleEmphasis: 'with its evidence.', description: 'Search by code or by name. Every result shows its release, hierarchy and official source.', searchLabel: 'Search a code or description', searchPlaceholder: 'e.g. 8517.13.01 or teléfonos', submit: 'Search', tryWith: 'Try', metrics: [['8,183', 'Mexican fractions'], ['11,507', 'NICO codes'], ['Daily', 'release checks'], ['Apache-2.0', 'open-source core']], startTitle: 'Choose where to start', tiles: [['Search a code and walk its hierarchy.', '/app', 'explore'], ['Glossary, wiki and MOA guide, with an A–Z index.', '/glossary', 'learn'], ['Releases, changes and documentation.', '/changes', 'data'], ['Where each datum comes from and how it is verified.', '/trust', 'trust']] },
  },
};

const LocaleContext = createContext(null);

export function LocaleProvider({ children }) {
  const [language, setLanguage] = useState(() => localStorage.getItem('arancel-mx-language') || 'es');
  useEffect(() => {
    localStorage.setItem('arancel-mx-language', language);
  }, [language]);
  const value = useMemo(() => ({ language, setLanguage, copy: LOCALES[language] }), [language]);
  return <LocaleContext.Provider value={value}>{children}</LocaleContext.Provider>;
}

export function useLocale() {
  const value = useContext(LocaleContext);
  if (!value) throw new Error('useLocale must be used inside LocaleProvider');
  return value;
}
