import { createContext, useContext, useEffect, useMemo, useState } from 'react';

const LOCALES = {
  es: {
    navigation: { '/app': 'Explorar', '/chapters': 'Capítulos', '/changes': 'Cambios', '/moa': 'Guía MOA', '/wiki': 'Wiki', '/glossary': 'Glosario', '/trade-context': 'Contexto comercial', '/documentation': 'Documentación', '/trust': 'Confianza', '/records': 'Mis registros' },
    header: { skip: 'Saltar al contenido', open: 'Abrir menú de navegación', close: 'Cerrar menú de navegación', navigation: 'Navegación principal', language: 'Idioma de la interfaz', themeLight: 'Usar tema claro', themeDark: 'Usar tema oscuro' },
    footer: { description: 'Datos arancelarios mexicanos verificables con evidencia de release visible.' },
    home: { eyebrow: 'RELEASES DE DATOS VERIFICADOS', kicker: 'Datos arancelarios mexicanos, inspeccionables', title: 'Inteligencia arancelaria ', titleEmphasis: 'sin perder la evidencia.', description: 'Explora datos arancelarios mexicanos sin perder de vista su release, jerarquía y contexto de fuente.', searchLabel: 'Busca un código o descripción', searchPlaceholder: 'p. ej. 8517.13.01 o teléfonos', submit: 'Abrir explorador', trust: 'Releases inmutables · Manifest + checksums · Verificación independiente', evidenceEyebrow: 'FICHA DE EVIDENCIA', evidenceTitle: 'Datos públicos verificados', evidenceDescription: 'Ejemplos registrados con su nivel y release visibles.', release: 'Release', level: 'Nivel', source: 'Evidencia', sourceValue: 'Release registrada', pause: 'Pausar fichas', resume: 'Continuar fichas', show: 'Mostrar', inspect: 'Inspeccionar ficha', officialDescription: 'Descripción oficial en español', metrics: [['8,183', 'Fracciones mexicanas'], ['11,507', 'Códigos NICO'], ['Diario', 'verificación de release'], ['Apache-2.0', 'núcleo abierto']], cards: [['Releases de datos', 'Lee manifests, checksums y archivos fuente.', 'Abrir releases'], ['Superficies para desarrollo', 'Usa API, CLI y paquete Python con un contrato documentado.', 'Abrir documentación'], ['Confianza independiente', 'Inspecciona roles de fuente y controles de publicación.', 'Leer modelo de confianza']] },
  },
  en: {
    navigation: { '/app': 'Explorer', '/chapters': 'Chapters', '/changes': 'Changes', '/moa': 'MOA guide', '/wiki': 'Wiki', '/glossary': 'Glossary', '/trade-context': 'Trade context', '/documentation': 'Documentation', '/trust': 'Trust', '/records': 'My records' },
    header: { skip: 'Skip to content', open: 'Open navigation menu', close: 'Close navigation menu', navigation: 'Primary navigation', language: 'Interface language', themeLight: 'Use light theme', themeDark: 'Use dark theme' },
    footer: { description: 'Verified Mexican tariff data with visible release evidence.' },
    home: { eyebrow: 'VERIFIED DATA RELEASES', kicker: 'Mexican tariff data, made inspectable', title: 'Tariff intelligence ', titleEmphasis: 'without losing the evidence.', description: 'Explore Mexican tariff data while keeping its release, hierarchy and source context visible.', searchLabel: 'Search a code or description', searchPlaceholder: 'e.g. 8517.13.01 or teléfonos', submit: 'Open explorer', trust: 'Immutable releases · Manifest + checksums · Independent verification', evidenceEyebrow: 'EVIDENCE CARD', evidenceTitle: 'Verified public data', evidenceDescription: 'Recorded examples with their level and release visible.', release: 'Release', level: 'Level', source: 'Evidence', sourceValue: 'Recorded release', pause: 'Pause cards', resume: 'Resume cards', show: 'Show', inspect: 'Inspect record', officialDescription: 'Official description in Spanish', metrics: [['8,183', 'Mexican fractions'], ['11,507', 'NICO codes'], ['Daily', 'release checks'], ['Apache-2.0', 'open-source core']], cards: [['Data releases', 'Read manifests, checksums and source archives.', 'Open releases'], ['Developer surfaces', 'Use the API, CLI and Python package against a documented contract.', 'Open documentation'], ['Independent trust', 'Inspect source roles and fail-closed publication controls.', 'Read trust model']] },
  },
};

const LocaleContext = createContext(null);

export function LocaleProvider({ children }) {
  const [language, setLanguage] = useState(() => localStorage.getItem('arancel-mx-language') || 'es');
  useEffect(() => {
    localStorage.setItem('arancel-mx-language', language);
    document.documentElement.lang = language === 'es' ? 'es-MX' : 'en';
  }, [language]);
  const value = useMemo(() => ({ language, setLanguage, copy: LOCALES[language] }), [language]);
  return <LocaleContext.Provider value={value}>{children}</LocaleContext.Provider>;
}

export function useLocale() {
  const value = useContext(LocaleContext);
  if (!value) throw new Error('useLocale must be used inside LocaleProvider');
  return value;
}
