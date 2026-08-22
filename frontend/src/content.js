export const NAVIGATION = [
  ['Explorer', '/app'],
  ['Chapters', '/chapters'],
  ['Changes', '/changes'],
  ['MOA guide', '/moa'],
  ['Wiki', '/wiki'],
  ['Glossary', '/glossary'],
  ['Trade context', '/trade-context'],
  ['Documentation', '/documentation'],
  ['Trust', '/trust'],
  ['My records', '/records'],
];

export const OFFICIAL_LINKS = {
  anamMoa: 'https://www.anam.gob.mx/manual-de-operacion-aduanera-moa/',
  anamMoaPdf: 'https://www.anam.gob.mx/wp-content/uploads/2022/05/Manual-de-Operacion-Aduanera-MOA-may2022.pdf',
  anamMoaNotice: 'https://www.anam.gob.mx/moa/',
  anamGlossary: 'https://www.anam.gob.mx/glosario-anam/',
  anamNormativity: 'https://www.anam.gob.mx/normatividad_2022/',
  dof: 'https://www.dof.gob.mx/',
  law: 'https://www.diputados.gob.mx/LeyesBiblio/pdf/LAdua.pdf',
  inegi: 'https://cuentame.inegi.org.mx/explora/economia/comercio_exterior/',
  github: 'https://github.com/jccontrerasg08-cpu/arancel-mx',
  releases: 'https://github.com/jccontrerasg08-cpu/arancel-mx/releases',
  pypi: 'https://pypi.org/project/arancel-mx/',
};

export const EDITORIAL_PAGES = {
  '/': {
    eyebrow: 'VERIFIED DATA RELEASES',
    title: 'Tariff intelligence without losing the evidence.',
    description: 'Explore a Mexican tariff reference while keeping its release, hierarchy, source and verification context visible.',
    disclaimer: 'Public data and documented evidence. This site does not classify merchandise or provide legal advice.',
  },
  '/moa': {
    eyebrow: 'Guía de fuente oficial · ANAM',
    title: 'Manual de Operación Aduanera, en contexto.',
    description: 'Un mapa de lectura para navegar la fuente oficial sin sustituirla.',
    disclaimer: 'No sustituye el MOA ni determina trámites, requisitos o resultados para una operación individual.',
  },
  '/wiki': {
    eyebrow: 'FUENTES PRIMARIAS ENLAZADAS',
    title: 'Normatividad, con su origen visible.',
    description: 'Instrumentos oficiales agrupados por su emisor y contexto de consulta.',
    disclaimer: 'Verifica vigencia, aplicación y texto íntegro directamente con el publicador oficial.',
  },
  '/glossary': {
    eyebrow: 'FUENTE ANAM · CONSULTA 2026-08-19',
    title: 'Definiciones, con atribución visible.',
    description: 'Consulta local de términos y siglas documentadas por ANAM.',
    disclaimer: 'Las definiciones se muestran como referencia documental y no determinan requisitos o resultados.',
  },
  '/trade-context': {
    eyebrow: 'INEGI · CONTEXTO HISTÓRICO',
    title: 'Comercio exterior: datos para entender el contexto.',
    description: 'Explicación y series oficiales para importaciones, exportaciones, balanza, entidades y socios.',
    disclaimer: 'El contexto histórico no determina una fracción ni una operación individual.',
  },
  '/documentation': {
    eyebrow: 'DOCUMENTATION HUB',
    title: 'Start with the contract, then write the integration.',
    description: 'Guías técnicas para consumir releases verificables, API y artefactos de verificación.',
    disclaimer: 'Cada integración debe usar una release inmutable y verificarla localmente.',
  },
  '/trust': {
    eyebrow: 'OPEN-SOURCE TRUST',
    title: 'When evidence is incomplete, the release stops.',
    description: 'El modelo de confianza conecta fuentes, reconciliación, build fail-closed y verificación independiente.',
    disclaimer: 'La publicación sólo continúa cuando los controles de evidencia necesarios están completos.',
  },
  '/records': {
    eyebrow: 'LOCAL RESEARCH RECORDS · THIS DEVICE ONLY',
    title: 'Save evidence you can return to.',
    description: 'Stored only in this browser. Prepare research records from verified codes without an account or server storage.',
    disclaimer: 'Los registros no son clasificación, opinión legal ni un pedimento; borrar datos del navegador elimina la lista.',
  },
  '/chapters': {
    eyebrow: 'Estructura verificada · versión vigente',
    title: 'Capítulos, familias y jerarquía.',
    description: 'Recorre la estructura publicada sin perder el nivel inmediato de evidencia.',
    disclaimer: 'Esta es una superficie de consulta, no una herramienta de clasificación.',
  },
  '/changes': {
    eyebrow: 'RELEASE SIGNALS · EVIDENCE FIRST',
    title: 'Find what a verified fraction shows now.',
    description: 'Inspecciona campos de release, jerarquía, vigencia y procedencia antes de interpretar una diferencia.',
    disclaimer: 'La evidencia documentada no afirma que una reforma legal aplique a una operación individual.',
  },
};

export const FALLBACK_SECTIONS = [
  { roman: 'Sección I', name: 'Animales vivos y productos del reino animal', chapter_from: 1, chapter_to: 5 },
];

export const FALLBACK_CHAPTERS = [
  { code: '01', description: 'Animales vivos', families: [{ code: '01.01', description: 'Caballos, asnos, mulos y burdéganos, vivos' }] },
];

export const MOA_GROUPS = [
  ['01', 'Actuaciones previas al despacho', 'Consulta las referencias del manual antes de la operación de despacho.', OFFICIAL_LINKS.anamMoa],
  ['02', 'Despacho aduanero', 'Navega el bloque oficial de actividades de despacho.', OFFICIAL_LINKS.anamMoa],
  ['03', 'Inspección, control y gestión', 'Revisa el contexto institucional publicado por ANAM.', OFFICIAL_LINKS.anamMoa],
  ['04', 'Actos y procedimientos legales', 'Abre el grupo de procedimientos y su fuente primaria.', OFFICIAL_LINKS.anamMoa],
  ['05', 'Compilación de beneficios', 'Consulta los beneficios y condiciones directamente en la fuente.', OFFICIAL_LINKS.anamMoa],
];

export const WIKI_REFERENCES = [
  ['Institución', 'Creación de la ANAM', 'Decreto de creación de la Agencia Nacional de Aduanas de México.', 'https://www.dof.gob.mx/nota_detalle.php?codigo=5623945&fecha=14/07/2021'],
  ['Institución', 'Reglamento de la ANAM', 'Reglamento publicado en el Diario Oficial de la Federación.', 'https://www.dof.gob.mx/nota_detalle.php?codigo=5639045&fecha=21/12/2021'],
  ['Marco aduanero', 'Ley Aduanera', 'Texto vigente disponible en la biblioteca legislativa.', OFFICIAL_LINKS.law],
  ['Marco aduanero', 'Manual de Operación Aduanera', 'Página institucional y documento enlazado por ANAM.', OFFICIAL_LINKS.anamMoa],
  ['Territorio', 'Circunscripción territorial de las aduanas', 'Acuerdo publicado en el DOF.', 'https://www.dof.gob.mx/nota_detalle.php?codigo=5644134&fecha=01/03/2022'],
  ['Territorio', 'Modificación de circunscripción territorial', 'Actualización publicada en el DOF.', 'https://www.dof.gob.mx/nota_detalle.php?codigo=5645887&fecha=17/03/2022'],
  ['Comercio exterior', 'Reglas Generales de Comercio Exterior', 'Acceso institucional a reglamentación y normatividad.', OFFICIAL_LINKS.anamNormativity],
  ['Consulta', 'Diario Oficial de la Federación', 'Publicador oficial para instrumentos normativos federales.', OFFICIAL_LINKS.dof],
  ['Consulta', 'Leyes federales', 'Biblioteca legislativa de la Cámara de Diputados.', 'https://www.diputados.gob.mx/LeyesBiblio/index.htm'],
];

export const DOCUMENTATION_LINKS = [
  ['Consumer quickstart', 'docs/consumer-quickstart.md'],
  ['External consumption', 'docs/external-consumption.md'],
  ['NICO/LIGIE guide', 'docs/nico-ligie-guide.md'],
  ['Official source roles', 'docs/official-source-roles.md'],
  ['Data model', 'docs/data-model.md'],
  ['CLI reference', 'docs/consumer-cli.md'],
  ['Production certification', 'docs/production-certification.md'],
  ['Public service observability', 'docs/operations/public-service-observability.md'],
];
