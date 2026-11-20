import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import path from 'node:path';
import { pathToFileURL } from 'node:url';
import test from 'node:test';

const root = path.resolve(import.meta.dirname, '../..');

test('every page in the navigation is reachable from a header group, a header action or the footer', async () => {
  const { NAV_GROUPS, NAVIGATION, HEADER_ACTIONS, FOOTER_ONLY, FOOTER_GROUPS } = await import(pathToFileURL(path.join(root, 'frontend/src/content.js')).href);
  const grouped = NAV_GROUPS.flatMap((group) => group.href ? [group.href] : group.items);

  assert.equal(NAV_GROUPS.length, 4);
  assert.equal(new Set(grouped).size, grouped.length, 'a page appears in two groups');
  for (const [, href] of NAVIGATION) {
    const reachable = grouped.includes(href) || HEADER_ACTIONS.includes(href) || FOOTER_ONLY.includes(href);
    assert.ok(reachable, `${href} is not reachable from the header or the footer`);
  }
  for (const href of FOOTER_ONLY) assert.ok(!grouped.includes(href) && !HEADER_ACTIONS.includes(href), `${href} is footer-only`);
});

test('the footer lists every navigation page exactly once and has a label for each in both languages', async () => {
  const [{ FOOTER_GROUPS, NAVIGATION }, locale] = await Promise.all([
    import(pathToFileURL(path.join(root, 'frontend/src/content.js')).href),
    readFile(path.join(root, 'frontend/src/locale.jsx'), 'utf8'),
  ]);
  const listed = FOOTER_GROUPS.flatMap((group) => group.items);
  assert.equal(new Set(listed).size, listed.length, 'a page appears twice in the footer');
  assert.deepEqual([...listed].sort(), NAVIGATION.map(([, href]) => href).sort(), 'the footer and NAVIGATION list the same pages');
  for (const href of listed) assert.equal(locale.split(`'${href}':`).length - 1 >= 2, true, `${href} has an es and an en label`);
  for (const group of FOOTER_GROUPS) assert.ok(locale.includes(`${group.id}: `), `the ${group.id} column has a title`);
});

test('every public route is linked from the header or the footer, except aliases and record pages', async () => {
  const [{ PUBLIC_ROUTES }, { NAVIGATION }] = await Promise.all([
    import(pathToFileURL(path.join(root, 'frontend/src/routes.js')).href),
    import(pathToFileURL(path.join(root, 'frontend/src/content.js')).href),
  ]);
  const linked = new Set(NAVIGATION.map(([, href]) => href));
  const exempt = new Set(['/', '/product', '/moa-guide']);
  for (const { path: route } of PUBLIC_ROUTES) {
    if (exempt.has(route) || route.includes(':')) continue;
    assert.ok(linked.has(route), `${route} is a public route but no navigation links to it`);
  }
});
