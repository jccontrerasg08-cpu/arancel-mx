// Copy of the secondary pages and the tab title of every route that has no EDITORIAL_PAGES entry.
// Plain JavaScript on purpose: the static build (scripts/sync-frontend-static.mjs) reads it in Node to write the
// title, description and canonical of each route into its own HTML file.

export const MARKETING_COPY = {
  '/features': { eyebrow: ['SUPERFICIES DEL PRODUCTO', 'PRODUCT SURFACES'], title: ['Construye sobre datos arancelarios verificables.', 'Build on verifiable tariff data.'], description: ['Explora las superficies públicas del producto, sus límites documentados y los artefactos de cada release.', 'Explore the public product surfaces, documented limits and release artifacts.'], action: ['/documentation', 'Leer la documentación', 'Read documentation'] },
  '/releases': { eyebrow: ['RELEASES ABIERTOS', 'OPEN DATA RELEASES'], title: ['Releases públicos, artefactos inspeccionables.', 'Public releases, inspectable artifacts.'], description: ['Los datos centrales y los materiales de verificación se pueden revisar abiertamente.', 'The core data and verification materials remain openly inspectable.'], action: ['/trust', 'Leer el modelo de confianza', 'Read trust model'] },
  '/release-analytics': { eyebrow: ['CONTEXTO DEL RELEASE', 'RELEASE ANALYTICS'], title: ['Contexto del release sin puntajes opacos.', 'Release context without opaque scoring.'], description: ['Revisa un release a través de evidencia visible y del rol de cada fuente.', 'Inspect a release through visible evidence and source roles.'], action: ['/changes', 'Ver los cambios del DOF', 'Inspect release evidence'] },
  '/community': { eyebrow: ['COMUNIDAD ABIERTA', 'OPEN COMMUNITY'], title: ['Contribuye con evidencia visible.', 'Contribute through visible evidence.'], description: ['Usa el repositorio público para revisar, discutir y mejorar el contrato de datos abiertos.', 'Use the public repository to review, discuss and improve the open data contract.'], action: ['/documentation', 'Abrir la documentación', 'Open documentation'] },
};

// Tab title and description for the routes that have no EDITORIAL_PAGES entry: the explorer (same words as its hero)
// and the four secondary pages (same words as their hero, from MARKETING_COPY).
export const EXPLORER_META = { title: ['Explora una referencia arancelaria sin perder su camino.', 'Explore a tariff reference without losing its path.'], description: ['Revisa jerarquía, contexto de release y evidencia registrada sin tratar un resultado de búsqueda como una determinación legal.', 'Inspect hierarchy, release context and recorded evidence without treating a search result as a legal determination.'] };
export const ROUTE_META = { '/app': EXPLORER_META, '/product': EXPLORER_META };

export function routeMeta(path, language) {
  const entry = ROUTE_META[path] || MARKETING_COPY[path];
  const index = language === 'en' ? 1 : 0;
  return entry ? { title: entry.title[index], description: entry.description[index] } : undefined;
}
