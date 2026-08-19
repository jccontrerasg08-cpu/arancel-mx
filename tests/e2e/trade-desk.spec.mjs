import { expect, test } from '@playwright/test';

test('serves a trade desk with an itemized import orientation', async ({ page }) => {
  await page.goto('/trade');

  await expect(page.getByRole('heading', { name: /mesa de comercio exterior/i })).toBeVisible();
  await page.getByTestId('customs-value').fill('1000');
  await page.getByTestId('igi-rate').fill('10');
  await page.getByTestId('dta-rate').fill('0.8');
  await page.getByTestId('iva-rate').fill('16');
  await page.getByTestId('calculate-import').click();

  await expect(page.getByTestId('import-result')).toContainText('IGI estimado');
  await expect(page.getByTestId('import-result')).toContainText('$285.28');
  await expect(page.getByTestId('import-result')).toContainText(/orientativo/i);
});

test('keeps source-cited T-MEC, RRNA and pedimento guidance accessible', async ({ page }) => {
  await page.goto('/trade');

  await page.getByRole('tab', { name: /origen t-mec/i }).click();
  await page.locator('#tmec-code').fill('85171301');
  await page.locator('#tmec-origin').selectOption('MX');
  await expect(page.getByTestId('tmec-result')).toContainText(/declaraciones de proveedor/i);
  await expect(page.getByTestId('tmec-source')).toHaveAttribute('href', /gob\.mx\/t-mec/);

  await page.getByRole('tab', { name: /rrna y despacho/i }).click();
  await expect(page.getByTestId('rrna-source')).toHaveAttribute('href', /snice\.gob\.mx/);
  await expect(page.getByTestId('pedimento-checklist')).toContainText(/no genera ni transmite/i);
});

test('derives an orientative customs-value base from declared Incoterm components', async ({ page }) => {
  await page.goto('/trade');

  await page.getByLabel(/incoterm declarado/i).selectOption('CIF');
  await page.getByTestId('product-value').fill('1000');
  await page.getByTestId('freight-value').fill('120');
  await page.getByTestId('insurance-value').fill('30');
  await page.getByTestId('incrementables-value').fill('50');
  await page.getByTestId('calculate-import').click();

  await expect(page.getByTestId('import-result')).toContainText('Valor en aduana declarado');
  await expect(page.getByTestId('import-result')).toContainText('$1,200.00');
});
