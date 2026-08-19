import { readFile } from 'node:fs/promises';

import { expect, test } from '@playwright/test';

test('serves the public marketing root and preserves the explorer handoff', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('heading', { name: /tariff intelligence/i })).toBeVisible();
  await expect(page.getByText(/Apache-2\.0/i).first()).toBeVisible();
  await expect(page.getByRole('link', { name: /open explorer/i })).toHaveAttribute('href', 'https://arancel-mx.vercel.app/app');
});

test('serves the local research records page without an account boundary', async ({ page }) => {
  await page.goto('/records');
  await expect(page.getByRole('heading', { name: /save evidence you can return to/i })).toBeVisible();
  await expect(page.getByText(/stored only in this browser/i)).toBeVisible();
  await expect(page.getByRole('button', { name: /check verified record/i })).toBeVisible();
});

test('serves verified chapter and fraction-change discovery routes', async ({ page }) => {
  await page.goto('/chapters');
  await expect(page.getByRole('heading', { name: /capítulos, familias y jerarquía/i })).toBeVisible();
  await page.goto('/changes');
  await expect(page.getByRole('heading', { name: /find what a verified fraction shows now/i })).toBeVisible();
  await expect(page.getByRole('button', { name: /inspect release/i })).toBeVisible();
});

test('opens a verified chapter section and family hierarchy from the keyboard', async ({ page }) => {
  await page.goto('/chapters');
  const section = page.getByRole('button', { name: /^sección I /i });
  await section.focus();
  await page.keyboard.press('Enter');
  const chapter = page.getByRole('button', { name: /capítulo 01/i });
  await expect(chapter).toBeVisible();
  await chapter.focus();
  await page.keyboard.press('Enter');
  await expect(page.getByRole('button', { name: /partida · familia HS4.*01\.01/i })).toBeVisible();
});

test('serves the source-cited trade-context and ANAM MOA routes', async ({ page }) => {
  await page.goto('/trade-context');
  await expect(page.getByRole('heading', { name: /comercio exterior: datos para entender el contexto/i })).toBeVisible();
  await expect(page.getByRole('link', { name: /abrir explicación completa de INEGI/i })).toHaveAttribute('href', 'https://cuentame.inegi.org.mx/explora/economia/comercio_exterior/');
  await page.goto('/moa');
  await expect(page.getByRole('heading', { name: /manual de operación aduanera, en contexto/i })).toBeVisible();
  await expect(page.getByRole('link', { name: /abrir manual de ANAM/i })).toHaveAttribute('href', 'https://www.anam.gob.mx/manual-de-operacion-aduanera-moa/');
});

test('serves ANAM source-indexed wiki and searchable glossary routes', async ({ page }) => {
  await page.goto('/wiki');
  await expect(page.getByRole('heading', { name: /normatividad, con su origen visible/i })).toBeVisible();
  await expect(page.getByRole('link', { name: /abrir normatividad ANAM/i })).toHaveAttribute('href', 'https://www.anam.gob.mx/normatividad_2022/');
  await page.goto('/glossary');
  await expect(page.getByRole('heading', { name: /definiciones, con atribución visible/i })).toBeVisible();
  await page.getByRole('textbox', { name: /buscar en el glosario ANAM/i }).fill('Aduana');
  await expect(page.getByTestId('anam-glossary-results')).toContainText('Aduana');
  await expect(page.getByRole('link', { name: /abrir glosario ANAM/i })).toHaveAttribute('href', 'https://www.anam.gob.mx/glosario-anam/');
});

test('serves the homepage-aligned verified explorer', async ({ page }) => {
  await page.goto('/app');
  await expect(page.getByRole('heading', { name: /explore a tariff reference/i })).toBeVisible();
  await expect(page.getByTestId('search-input')).toBeVisible();
  await expect(page.getByTestId('example-fraction')).toContainText(/IGI/i);
  await expect(page.getByRole('link', { name: /browse visual tree/i })).toHaveAttribute('href', '/chapters');
});

test('looks up a complete tariff fraction with evidence and a decision tree', async ({ page }) => {
  await page.goto('/app');
  await page.getByTestId('search-input').fill('8517.13.01');
  await page.getByTestId('search-submit').click();
  const card = page.getByTestId('result-card').first();
  await expect(card).toContainText('85.17.13.01');
  await expect(card).toContainText(/teléfonos inteligentes/i);
  await expect(page.getByTestId('hierarchy-card')).toContainText(/progressive decision tree/i);
  await expect(page.getByTestId('tree-filter-status')).toContainText('85.17.13.01');
  await expect(page.getByRole('status')).toHaveText(/verified record ready/i);
  await expect(page.getByRole('link', { name: /API JSON/i })).toHaveAttribute('href', /\/v1\/ficha\/85171301$/);
});

test('exposes rates only on fraction cards', async ({ page }) => {
  await page.goto('/app/record/01012101');
  const fractionCard = page.getByTestId('result-card');
  await expect(fractionCard).toContainText('01.01.21.01');
  await expect(fractionCard).toContainText('IGI');
  await expect(fractionCard).toContainText('IGE');

  await page.goto('/app/record/0101210100');
  const nicoCard = page.getByTestId('result-card');
  await expect(nicoCard).toContainText('01.01.21.01.00');
  await expect(nicoCard).not.toContainText('IGI');
  await expect(nicoCard).not.toContainText('IGE');
});

test('narrows the visible decision-tree path from an entered fraction prefix', async ({ page }) => {
  await page.goto('/app/record/85171301');
  await expect(page.getByTestId('hierarchy-card')).toBeVisible();
  await page.getByTestId('search-input').fill('8517');
  await expect(page.getByTestId('tree-filter-status')).toContainText('85.17');
  await expect(page.getByTestId('hierarchy-card')).toContainText(/capítulo HS2/i);
});

test('searches verified descriptions from input and quick action', async ({ page }) => {
  await page.goto('/app');
  await page.getByTestId('search-input').fill('teléfonos');
  await page.getByTestId('search-submit').click();
  await expect(page.getByTestId('result-card').first()).toContainText(/teléfonos/i);
  await expect(page.getByRole('status')).toContainText(/verified results found/i);
  await page.goto('/app');
  await page.getByRole('button', { name: /try teléfonos/i }).click();
  await expect(page.getByTestId('result-card').first()).toContainText(/teléfonos/i);
});

test('explains when a query is required without changing the workspace', async ({ page }) => {
  await page.goto('/app');
  await page.getByTestId('search-submit').click();
  await expect(page.getByRole('status')).toContainText(/enter a tariff code/i);
  await expect(page.getByRole('heading', { name: /enter a complete code or a description/i })).toBeVisible();
});

test('opens shared and durable explorer URLs', async ({ page }) => {
  await page.goto('/app?q=85171301');
  await expect(page.getByTestId('search-input')).toHaveValue('85171301');
  await expect(page.getByTestId('result-card')).toContainText(/teléfonos inteligentes/i);
  await page.goto('/app/record/85171301');
  await expect(page.getByTestId('result-card')).toContainText(/teléfonos inteligentes/i);
  await expect(page.getByRole('heading', { name: /release context, not advice/i })).toBeVisible();
  await page.goto('/app/chapter/85');
  await expect(page.getByTestId('result-card')).toContainText('85');
  await expect(page.getByRole('status')).toHaveText(/verified record ready/i);
});

test('opens the visual tree from the explorer and keeps its selected hierarchy inspectable', async ({ page }) => {
  await page.goto('/app');
  await page.getByRole('link', { name: /browse visual tree/i }).click();
  await expect(page).toHaveURL(/\/chapters$/);
  await expect(page.getByRole('button', { name: /^sección I /i })).toBeVisible();
  await page.goto('/app/record/85171301');
  await expect(page.getByTestId('hierarchy-card')).toContainText('85.17.13.01');
});

test('saves and exports a browser-local research snapshot', async ({ page }) => {
  await page.goto('/app/record/85171301');
  await page.getByRole('button', { name: /save locally/i }).click();
  await expect(page.getByTestId('snapshot-list')).toContainText('85.17.13.01');
  const download = page.waitForEvent('download');
  await page.getByTestId('export-snapshots').click();
  const backup = await download;
  await expect(backup.suggestedFilename()).toBe('arancel-mx-fichas-locales.json');
  const payload = JSON.parse(await readFile(await backup.path(), 'utf-8'));
  expect(payload.schema_version).toBe(1);
  expect(payload.snapshots).toEqual(expect.arrayContaining([expect.objectContaining({ code: '85171301', dataset_version: '2026.08.15' })]));
});

test('keeps integrated research controls keyboard-reachable and announced', async ({ page }) => {
  await page.goto('/app/record/85171301');
  await expect(page.getByRole('button', { name: /save locally/i })).toBeVisible();
  await expect(page.getByRole('status')).toHaveAttribute('aria-live', 'polite');
  await expect(page.getByTestId('snapshot-list')).toHaveAttribute('aria-live', 'polite');
  await page.getByTestId('search-input').focus();
  await page.keyboard.press('Tab');
  await expect(page.getByTestId('search-submit')).toBeFocused();
});
