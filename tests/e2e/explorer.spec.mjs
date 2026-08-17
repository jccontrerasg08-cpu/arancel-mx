import { expect, test } from '@playwright/test';

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
  await expect(page.getByRole('status')).toHaveText(/ficha exacta recuperada/i);
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
  await page.getByTestId('result-card').first().getByRole('button', { name: /explorar jerarquía verificada/i }).click();
  await expect(page.getByTestId('hierarchy-card')).toContainText('85171301');
});
