import { cp, mkdir, readFile, readdir, rename, stat, unlink, writeFile } from 'node:fs/promises';
import { createHash } from 'node:crypto';
import path from 'node:path';
import { fileURLToPath } from 'node:url';

const root = path.resolve(path.dirname(fileURLToPath(import.meta.url)), '..');
const source = path.join(root, 'frontend-dist');
const sourceAssets = path.join(source, 'assets');
const destinations = [
  path.join(root, 'website'),
  path.join(root, 'src/arancel_mx/api/static/site'),
];

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

const sourceIndex = path.join(source, 'index.html');
const index = await readFile(sourceIndex, 'utf8');
await writeFile(sourceIndex, index.replace(`/assets/${bundleName}`, `/assets/${stableBundleName}`));

for (const destination of destinations) {
  await mkdir(destination, { recursive: true });
  const destinationAssets = path.join(destination, 'assets');
  await mkdir(destinationAssets, { recursive: true });
  for (const existing of await readdir(destinationAssets)) {
    if (/^index-[A-Za-z0-9_-]+\.(?:js|css)$/.test(existing) && existing !== stableBundleName) {
      await unlink(path.join(destinationAssets, existing));
    }
  }
  await cp(sourceIndex, path.join(destination, 'index.html'));
  await cp(sourceAssets, destinationAssets, {
    recursive: true,
    force: true,
  });

  // `trade.html` and its dedicated assets are independently maintained.
  await stat(path.join(destination, 'trade.html'));
}
