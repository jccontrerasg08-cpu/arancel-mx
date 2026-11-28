import { STANDALONE_ROUTES } from './routes.js';
import { normalizeText } from './static-api.js';

const COMMANDS = [
  { href: '/app', keywords: 'tarifa tigie arancel tariff explorador explorer' },
  { href: '/trade', keywords: 'simulador calculadora estimador simulator calculator import estimator' },
  { href: '/data', keywords: 'datos abiertos open data cifras figures estadísticas statistics' },
  { href: '/moa', keywords: 'moa manual operación aduanera customs operations' },
  { href: '/changes', keywords: 'dof decretos cambios cambios normativos' },
  { href: '/releases', keywords: 'releases versiones descargas downloads' },
  { href: '/documentation', keywords: 'api docs documentación documentation sdk' },
  { href: '/glossary', keywords: 'glosario glossary definiciones definitions' },
  { href: '/wiki', keywords: 'biblioteca leyes laws normatividad' },
  { href: '/learn', keywords: 'aprende aprender tutorial learn' },
  { href: '/trade-analytics', keywords: 'inegi bcmm balanza comercial trade balance analytics' },
];

export function findPaletteCommands(query, labels) {
  const normalized = normalizeText(query);
  const terms = normalized.split(' ');
  const matches = normalized ? COMMANDS.filter(({ href, keywords }) => {
    const searchable = normalizeText(`${href.slice(1)} ${labels[href]} ${keywords}`);
    return terms.every((term) => searchable.includes(term));
  }) : COMMANDS.slice(0, 4);

  return matches.map(({ href }) => ({ href, label: labels[href], standalone: STANDALONE_ROUTES.has(href) }));
}
