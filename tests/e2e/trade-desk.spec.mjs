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

test('uses a direct customs-value base without requiring Incoterm components', async ({ page }) => {
  await page.goto('/trade');

  await page.getByTestId('product-value').fill('');
  await page.getByTestId('customs-value').fill('1000');
  await page.getByTestId('igi-rate').fill('10');
  await page.getByTestId('dta-rate').fill('0.8');
  await page.getByTestId('iva-rate').fill('16');
  await page.getByTestId('calculate-import').click();

  await expect(page.getByTestId('import-result')).toContainText('Base directa declarada');
  await expect(page.getByTestId('import-result')).toContainText('$285.28');
});

test('renders untrusted tariff-search fields as text rather than HTML', async ({ page }) => {
  await page.goto('/trade');
  await page.route('**/v1/search?**', async (route) => {
    await route.fulfill({
      contentType: 'application/json',
      body: JSON.stringify([
        {
          record: {
            code: '85171301',
            description: '<img data-testid="injected-search-markup" src="x">Teléfono',
            igi: { value: 0, text: '<b>0%</b>' },
            dataset_version: '<em>release</em>',
          },
        },
      ]),
    });
  });

  await page.locator('#classification-query').fill('teléfono');
  await page.getByRole('button', { name: /buscar/i }).click();

  await expect(page.getByTestId('injected-search-markup')).toHaveCount(0);
  await expect(page.locator('#classification-results')).toContainText('<img data-testid="injected-search-markup" src="x">Teléfono');
});

test('distinguishes an unmet declared T-MEC VCR threshold', async ({ page }) => {
  await page.goto('/trade');

  await page.getByRole('tab', { name: /origen t-mec/i }).click();
  await page.locator('#tmec-code').fill('85171301');
  await page.locator('#tmec-origin').selectOption('MX');
  await page.locator('#tmec-suppliers').check();
  await page.locator('#tmec-bom').check();
  await page.locator('#tmec-vcr').fill('45');
  await page.locator('#tmec-vcr-required').fill('75');
  await page.locator('#tmec-vcr-required').press('Tab');

  await expect(page.getByTestId('tmec-result')).toContainText(/umbral declarado no alcanzado/i);
  await expect(page.getByTestId('tmec-result')).toContainText('VCR declarado: 45% · umbral declarado: 75%');
  await expect(page.getByTestId('tmec-result')).toContainText(/no determina.*origen/i);
});

test('makes the RRNA review explicit in the dispatch checklist', async ({ page }) => {
  await page.goto('/trade');

  await page.getByRole('tab', { name: /rrna y despacho/i }).click();
  await page.locator('#pedimento-code').fill('85171301');
  await page.locator('#pedimento-regime').selectOption('definitive_import');
  await page.locator('#pedimento-origin').fill('CN');
  await page.locator('#pedimento-value').fill('1000');
  await page.locator('#pedimento-invoice').check();
  await page.locator('#pedimento-transport').check();
  await page.locator('#pedimento-origin-evidence').check();

  await expect(page.getByTestId('pedimento-checklist')).toContainText('Pendientes de revisión documental');
  await expect(page.getByTestId('pedimento-checklist')).toContainText('Revisión documental de RRNA y programas aplicables');
  await page.getByLabel(/revisé rRNA y programas aplicables/i).check();
  await expect(page.getByTestId('pedimento-checklist')).toContainText('Revisión documental final requerida');
});

test('supports keyboard navigation across trade-desk tabs', async ({ page }) => {
  await page.goto('/trade');

  await page.locator('#costs-tab').focus();
  await page.keyboard.press('ArrowRight');

  await expect(page.locator('#tmec-tab')).toBeFocused();
  await expect(page.locator('#tmec-tab')).toHaveAttribute('aria-selected', 'true');
  await expect(page.locator('#tmec-panel')).not.toHaveAttribute('hidden', '');
});

test('shows release validity and provenance access for a classification hypothesis', async ({ page }) => {
  await page.goto('/trade');
  await page.route('**/v1/search?**', async (route) => {
    await route.fulfill({
      contentType: 'application/json',
      body: JSON.stringify([
        {
          record: {
            code: '85171301',
            description: 'Teléfono inteligente',
            igi: { value: 0, text: '0%' },
            ige: { text: 'Ex.' },
            dataset_version: 'data-2026.08.15',
            effective_from: '2026-04-20',
            effective_to: null,
            is_current: true,
            ligie_version: 'SA 2022',
            validity_basis: 'Release verificada',
          },
        },
      ]),
    });
  });

  await page.locator('#classification-query').fill('teléfono');
  await page.getByRole('button', { name: /buscar/i }).click();

  await expect(page.locator('#classification-results')).toContainText('IGE publicado: Ex.');
  await expect(page.locator('#classification-results')).toContainText('Vigencia de release: 2026-04-20 · vigente');
  await page.getByRole('tab', { name: /clasificación asistida/i }).click();
  await expect(page.getByRole('link', { name: /ver procedencia registrada/i })).toHaveAttribute('href', '/v1/codes/85171301/provenance');
});

test('gives keyboard focus a visible custom indicator', async ({ page }) => {
  await page.goto('/trade');

  await page.locator('#costs-tab').focus();
  await expect(page.locator('#costs-tab')).toHaveCSS('outline-style', 'solid');
  await expect(page.locator('#costs-tab')).toHaveCSS('outline-width', '3px');
});

test('renders calculation exception text without interpreting HTML', async ({ page }) => {
  await page.addInitScript(() => {
    const nativeNumber = window.Number;
    const poisonedNumber = (value) => {
      if (value === '1000') throw new Error('<img data-testid="injected-error-markup" src="x">Error controlado');
      return nativeNumber(value);
    };
    Object.setPrototypeOf(poisonedNumber, nativeNumber);
    window.Number = poisonedNumber;
  });
  await page.goto('/trade');

  await expect(page.getByTestId('injected-error-markup')).toHaveCount(0);
  await expect(page.getByTestId('import-result')).toContainText('<img data-testid="injected-error-markup" src="x">Error controlado');
});
