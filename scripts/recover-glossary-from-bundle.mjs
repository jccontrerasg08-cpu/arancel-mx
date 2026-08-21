import { readFile, writeFile } from 'node:fs/promises';
import { resolve } from 'node:path';

const root = resolve(import.meta.dirname, '..');
const bundlePath = resolve(root, 'website/assets/index-ad6fbc25b68e.js');
const outputPath = resolve(root, 'frontend/src/glossary-data.js');
const bundle = await readFile(bundlePath, 'utf8');
const matcher = /\{category:"((?:\\.|[^"\\])*)",term:"((?:\\.|[^"\\])*)",definition:"((?:\\.|[^"\\])*)"\}/g;
const decode = (value) => JSON.parse(`"${value}"`);
const entries = Array.from(bundle.matchAll(matcher), (match) => ({
  category: decode(match[1]),
  term: decode(match[2]),
  definition: decode(match[3]),
}));

if (entries.length !== 189) {
  throw new Error(`Expected 189 glossary entries from legacy bundle, received ${entries.length}`);
}

await writeFile(
  outputPath,
  `// Recovered from the versioned public bundle; attribution remains ANAM.\nexport const GLOSSARY_ENTRIES = Object.freeze(${JSON.stringify(entries, null, 2)});\n`,
);
console.log(`Recovered ${entries.length} glossary entries to ${outputPath}`);
