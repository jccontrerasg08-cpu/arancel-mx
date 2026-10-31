import assert from 'node:assert/strict';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import test from 'node:test';

const root = path.resolve(import.meta.dirname, '../..');

test('every page in the navigation belongs to exactly one header group, except My records', async () => {
  const { NAV_GROUPS, NAVIGATION } = await import(pathToFileURL(path.join(root, 'frontend/src/content.js')).href);
  const grouped = NAV_GROUPS.flatMap((group) => group.href ? [group.href] : group.items);

  assert.equal(NAV_GROUPS.length, 4);
  assert.equal(new Set(grouped).size, grouped.length, 'a page appears in two groups');
  for (const [, href] of NAVIGATION) {
    if (href === '/records') continue;
    assert.ok(grouped.includes(href), `${href} is not reachable from the header groups`);
  }
});