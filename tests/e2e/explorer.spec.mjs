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

  const card = page.getByTestId('result-card');
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
