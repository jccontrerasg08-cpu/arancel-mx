import { cp, mkdir, readFile, readdir, rename, stat, unlink, writeFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const source = path.join(root, 'frontend-dist');
const sourceAssets = path.join(source, 'assets');
// Single published copy: Vercel serves it (`outputDirectory`) and the wheel ships it.
const destination = path.join(root, 'src/arancel_mx/api/static/site');

await stat(source);
const assetNames = await readdir(sourceAssets);
const bundleName = assetNames.find((name) => /^index-[A-Za-z0-9_-]+\.js$/.test(name));
if (!bundleName) throw new Error('Vite did not emit an index JavaScript bundle');

const bundlePath = path.join(sourceAssets, bundleName);
const contentHash = createHash('sha256').update(await readFile(bundlePath)).digest('hex').slice(0, 12);
const stableBundleName = `index-${contentHash}.js`;
if (bundleName !== stableBundleName) {
  await rename(bundlePath, path.join(sourceAssets, stableBundleName));
}

for (const assetName of await readdir(sourceAssets)) {
  if (assetName === stableBundleName || !assetName.endsWith('.js')) continue;
  const assetPath = path.join(sourceAssets, assetName);
  const sourceCode = await readFile(assetPath, 'utf8');
  const publishedCode = sourceCode.replaceAll(`./${bundleName}`, `./${stableBundleName}`);
  if (publishedCode !== sourceCode) await writeFile(assetPath, publishedCode);
}

const sourceIndex = path.join(source, 'index.html');
const sourceFavicon = path.join(source, 'favicon.svg');
const index = await readFile(sourceIndex, 'utf8');
await writeFile(sourceIndex, index.replace(`/assets/${bundleName}`, `/assets/${stableBundleName}`));
const publishedAssetNames = new Set(await readdir(sourceAssets));
const generatedBundle = /^(?:index|glossary-page|data-page|dof-changes-page|dof-changes|dof-change-detail)-[A-Za-z0-9_-]{8,12}\.(?:js|css)$/;

await mkdir(destination, { recursive: true });
const destinationAssets = path.join(destination, 'assets');
await mkdir(destinationAssets, { recursive: true });
for (const existing of await readdir(destinationAssets)) {
  if (generatedBundle.test(existing) && !publishedAssetNames.has(existing)) {
    await unlink(path.join(destinationAssets, existing));
  }
}
await cp(sourceIndex, path.join(destination, 'index.html'));
await cp(sourceFavicon, path.join(destination, 'favicon.svg'));
await cp(sourceAssets, destinationAssets, {
  recursive: true,
  force: true,
});

// Standalone pages (trade desk, hub scripts) import the same static data client.
await cp(path.join(root, 'frontend/src/static-api.js'), path.join(destinationAssets, 'static-api.js'));

// `trade.html` and its dedicated assets are independently maintained.
await stat(path.join(destination, 'trade.html'));
