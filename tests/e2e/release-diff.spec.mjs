import { expect, test } from '@playwright/test';

const from = '2026.08.15';
const to = '2026.11.20';
const path = `diffs/${from}--${to}.json`;

test('filters published release changes and preserves the current record handoff', async ({ page }) => {
  await page.route('**/data/v1/diffs/index.json', (route) => route.fulfill({ json: {
    policy_version: 'release-diff-pages-v1',
    to,
    latest: path,
    diffs: [{ from, to, path, comparison_status: 'verified_snapshots', changes: 2 }],
  } }));
  await page.route(`**/data/v1/${path}`, (route) => route.fulfill({ json: {
    policy_version: 'release-diff-v1',
    comparison_status: 'verified_snapshots',
    from: { dataset_version: from, release_verified: true },
    to: { dataset_version: to, release_verified: true },
    counts: { changes: 2 },
    changes: [
      { code: '01012101', event: 'igi_changed', old_value: '0', new_value: null },
      { code: '85171301', event: 'row_removed', old_value: 'Teléfonos inteligentes', new_value: null },
    ],
    auxiliary: { nom: { status: 'not_compared', changes: [] } },
  } }));
  await page.goto('/data');
  const section = page.getByRole('region', { name: 'Cambios entre releases' });
  await expect(section.getByRole('link', { name: `data-${to}` })).toBeVisible();
  await expect(section.getByText('Comparación no disponible').first()).toBeVisible();
  await expect(section.getByRole('row', { name: /teléfonos inteligentes/i }).getByRole('link')).toHaveCount(0);
  await section.getByLabel('Tipo de cambio').selectOption('igi_changed');
  await expect(section.getByRole('row')).toHaveCount(2);
  await expect(section.getByRole('cell', { name: '0', exact: true })).toBeVisible();
  await expect(section.getByText('Sin valor registrado')).toBeVisible();
  await section.getByRole('link', { name: 'Ficha actual' }).click();
  await expect(page).toHaveURL(/[/]app[/]record[/]01012101$/);
});

test('shows availability without claiming zero changes when the index is unpublished', async ({ page }) => {
  await page.route('**/data/v1/diffs/index.json', (route) => route.fulfill({ status: 404 }));
  await page.goto('/data');
  const section = page.getByRole('region', { name: 'Cambios entre releases' });
  await expect(section.getByText('La comparación de releases aún no está publicada.')).toBeVisible();
  await expect(section.getByText(/no se encontraron cambios/i)).toHaveCount(0);
});
