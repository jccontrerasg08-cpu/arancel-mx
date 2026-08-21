const formatCode = (code) => {
  const clean = code.replace(/\D/g, '');
  if (clean.length === 2) return clean;
  if (clean.length === 4) return `${clean.slice(0, 2)}.${clean.slice(2)}`;
  if (clean.length === 6) return `${clean.slice(0, 2)}.${clean.slice(2, 4)}.${clean.slice(4)}`;
  if (clean.length === 8) return `${clean.slice(0, 2)}.${clean.slice(2, 4)}.${clean.slice(4, 6)}.${clean.slice(6)}`;
  if (clean.length === 10) return `${clean.slice(0, 2)}.${clean.slice(2, 4)}.${clean.slice(4, 6)}.${clean.slice(6, 8)}.${clean.slice(8)}`;
  return clean;
};

const EXAMPLES = [
  { code: '85', description: 'Máquinas, aparatos y material eléctrico; sus partes', level: 'hs2', dataset_version: '2026.08.15', igi: null, ige: null, unit_name: null, hierarchy: ['85'] },
  { code: '85171301', description: 'Teléfonos inteligentes', level: 'fraccion8', dataset_version: '2026.08.15', igi: 'Consult release', ige: 'Consult release', unit_name: 'Pza', hierarchy: ['85', '8517', '851713', '85171301'] },
  { code: '01012101', description: 'Caballos reproductores de raza pura', level: 'fraccion8', dataset_version: '2026.08.15', igi: 'Consult release', ige: 'Consult release', unit_name: 'Cbza', hierarchy: ['01', '0101', '010121', '01012101'] },
  { code: '0101210100', description: 'Caballos reproductores de raza pura', level: 'nico10', dataset_version: '2026.08.15', igi: null, ige: null, unit_name: 'Cbza', hierarchy: ['01', '0101', '010121', '01012101', '0101210100'] },
];

export const exampleRecordFor = (input) => {
  const clean = String(input || '').replace(/\D/g, '');
  const direct = EXAMPLES.find((record) => record.code === clean);
  if (direct) return direct;
  const descendant = EXAMPLES.find((record) => record.code.startsWith(clean) && [2, 4, 6].includes(clean.length));
  if (!descendant) return null;
  const level = { 2: 'hs2', 4: 'hs4', 6: 'hs6' }[clean.length];
  return {
    code: clean,
    description: 'Verified hierarchy level',
    level,
    dataset_version: descendant.dataset_version,
    igi: null,
    ige: null,
    unit_name: null,
    hierarchy: descendant.hierarchy.filter((code) => code.length <= clean.length),
  };
};

export const searchExampleRecords = (input) => {
  const query = String(input || '').trim().toLocaleLowerCase('es-MX');
  const numeric = query.replace(/\D/g, '');
  if (!query) return [];
  return EXAMPLES.filter((record) => (numeric ? record.code.includes(numeric) : false) || record.description.toLocaleLowerCase('es-MX').includes(query));
};

export const asExampleFicha = (record) => ({
  record: { ...record, formatted_code: formatCode(record.code), is_current: true },
  formatted_code: formatCode(record.code),
  hierarchy: record.hierarchy.map((code) => ({ code, description: code === record.code ? record.description : 'Verified hierarchy level' })),
  children: [],
});

export { formatCode };
