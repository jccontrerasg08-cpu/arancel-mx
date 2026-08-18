import { readFile } from 'node:fs/promises';

import { expect, test } from '@playwright/test';

test('serves the public marketing root and preserves the explorer handoff', async ({ page }) => {
  await page.goto('/');

  await expect(page.getByRole('heading', { name: /tariff intelligence/i })).toBeVisible();
  await expect(page.getByText(/Apache-2\.0/i).first()).toBeVisible();
  await expect(page.getByRole('link', { name: /open explorer/i })).toHaveAttribute('href', 'https://arancel-mx.vercel.app/app');
});

test('serves the verified tariff explorer', async ({ page }) => {
  await page.goto('/app');

  await expect(page.getByRole('heading', { name: /consulta arancelaria/i })).toBeVisible();
  await expect(page.getByTestId('search-input')).toBeVisible();
  await expect(page.getByText(/release verificada/i).first()).toBeVisible();
});

test('looks up a complete tariff fraction', async ({ page }) => {
  await page.goto('/app');
  await page.getByTestId('search-input').fill('8517.13.01');
  await page.getByTestId('search-submit').click();

  const card = page.getByTestId('result-card').first();
  await expect(card).toContainText('85171301');
  await expect(card).toContainText(/teléfonos inteligentes/i);
  await expect(page.getByRole('status')).toHaveText(/ficha durable verificada recuperada/i);
});

test('searches verified descriptions', async ({ page }) => {
  await page.goto('/app');
  await page.getByTestId('search-input').fill('teléfonos');
  await page.getByTestId('search-submit').click();

  await expect(page.getByTestId('result-card').first()).toContainText(/teléfonos/i);
  await expect(page.getByRole('status')).toContainText(/coincidencia/i);
});

test('explains when a query is required', async ({ page }) => {
  await page.goto('/app');
  await page.getByTestId('search-submit').click();

  await expect(page.getByRole('alert')).toContainText(/ingresa un código arancelario/i);
});


test('shows the unified verified data hub', async ({ page }) => {
  await page.goto('/app');

  await expect(page.getByTestId('hub-status')).toContainText(/release data-2026\.08\.15/i);
  await expect(page.getByRole('heading', { name: /del HS6 a la identificación comercial mexicana/i })).toBeVisible();
  await expect(page.getByRole('link', { name: /ver paquete en PyPI/i })).toBeVisible();
});

test('opens a shared lookup URL', async ({ page }) => {
  await page.goto('/app?q=85171301');

  await expect(page.getByTestId('search-input')).toHaveValue('85171301');
  await expect(page.getByTestId('result-card')).toContainText(/teléfonos inteligentes/i);
});


test('filters verified results while typing', async ({ page }) => {
  await page.goto('/app');
  await page.getByTestId('search-input').fill('teléfonos');

  await expect(page.getByTestId('result-card').first()).toContainText(/teléfonos/i);
  await expect(page.getByRole('status')).toContainText(/coincidencia/i);
});

test('browses the verified hierarchy from chapters and a result', async ({ page }) => {
  await page.goto('/app');
  await page.getByTestId('browse-chapters').click();
  await expect(page.getByTestId('chapter-browser')).toBeVisible();

  await page.locator('[data-hierarchy-code="85"]').first().click();
  await expect(page.getByTestId('hierarchy-card')).toContainText(/jerarquía verificada/i);

  await page.getByTestId('search-input').fill('85171301');
  await page.getByTestId('search-submit').click();
  await expect(page.getByTestId('hierarchy-card')).toContainText('85171301');
});

test('serves a durable verified record URL with evidence and next steps', async ({ page }) => {
  await page.goto('/app/record/85171301');

  await expect(page.getByTestId('result-card')).toContainText(/teléfonos inteligentes/i);
  await expect(page.getByRole('heading', { name: /vigencia y evidencia registrada/i })).toBeVisible();
  await expect(page.getByRole('heading', { name: /siguientes pasos con la misma evidencia/i })).toBeVisible();
  await expect(page.getByRole('link', { name: /API JSON/i })).toHaveAttribute('href', /\/v1\/ficha\/85171301$/);
});

test('serves a durable verified chapter URL', async ({ page }) => {
  await page.goto('/app/chapter/85');

  await expect(page.getByTestId('result-card')).toContainText('85');
  await expect(page.getByRole('status')).toHaveText(/capítulo durable verificado recuperado/i);
});

test('saves and exports a browser-local research snapshot', async ({ page }) => {
  await page.goto('/app/record/85171301');
  await page.getByRole('button', { name: /guardar ficha local/i }).click();

  await expect(page.getByTestId('snapshot-list')).toContainText('85171301');
  const download = page.waitForEvent('download');
  await page.getByTestId('export-snapshots').click();
  const backup = await download;
  await expect(backup.suggestedFilename()).toBe('arancel-mx-fichas-locales.json');
  const payload = JSON.parse(await readFile(await backup.path(), 'utf-8'));
  expect(payload.schema_version).toBe(1);
  expect(payload.snapshots).toEqual(expect.arrayContaining([
    expect.objectContaining({ code: '85171301', dataset_version: '2026.08.15' }),
  ]));
});


test('keeps durable research controls keyboard-reachable and announced', async ({ page }) => {
  await page.goto('/app/record/85171301');

  await expect(page.getByRole('status')).toHaveAttribute('aria-live', 'polite');
  await expect(page.getByTestId('snapshot-list')).toHaveAttribute('aria-live', 'polite');
  await page.getByTestId('search-input').focus();
  await page.keyboard.press('Tab');
  await expect(page.getByTestId('search-submit')).toBeFocused();
  await expect(page.getByRole('button', { name: /guardar ficha local/i })).toBeVisible();
});
