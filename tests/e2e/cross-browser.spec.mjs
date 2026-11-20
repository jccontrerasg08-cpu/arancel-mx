import { expect, test } from '@playwright/test';

// Smoke tests that also run in Firefox and WebKit (the engine behind Safari), through the "firefox" and "webkit"
// projects of playwright.config.mjs. They cover the newer CSS and JavaScript the site leans on: theme switching,
// view transitions, scroll-driven motion, and the live trade-balance computation.

test('renders the home page and remembers the dark theme', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('heading', { name: /consulta el arancel de méxico/i })).toBeVisible();
  await page.getByRole('button', { name: /usar tema oscuro/i }).click();
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');
  expect(await page.evaluate(() => localStorage.getItem('theme'))).toBe('dark');
  await page.reload();
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');
});

test('reads a code level by level in the Learn guide', async ({ page }) => {
  await page.goto('/learn');
  await expect(page.getByRole('heading', { level: 1 })).toHaveText(/aprende a leer el arancel de méxico/i);
  await page.getByRole('button', { name: /^13[ ]*subpartida$/i }).click();
  await expect(page.getByRole('status').filter({ hasText: 'Subpartida' })).toContainText(/sistema armonizado/i);
});

test('lists the DOF publications that changed the tariff', async ({ page }) => {
  await page.goto('/changes');
  await expect(page.getByRole('heading', { name: /cambios del dof a los códigos arancelarios/i })).toBeVisible();
  // The list loads in a lazy chunk, so wait for it instead of counting once.
  const items = page.getByTestId('dof-timeline').locator(':scope > li');
  await expect.poll(() => items.count()).toBeGreaterThan(10);
});

test('computes the trade balance from the live series and falls back to the saved copy', async ({ page }) => {
  const observation = (year, month, value) => ({ TIME_PERIOD: `${year}/${String(month).padStart(2, '0')}`, OBS_VALUE: String(value) });
  const series = (id, value) => ({ INDICADOR: id, OBSERVATIONS: [...Array(12 * 12)].map((_, index) => observation(2014 + Math.floor(index / 12), (index % 12) + 1, value)) });
  await page.route('**/api/trade_balance', (route) => route.fulfill({ json: { Series: [series('33860', 100), series('33861', 90), series('33229', 10)] } }));
  await page.goto('/trade-context');
  const balance = page.getByTestId('trade-balance');
  await expect(balance).toHaveAttribute('data-live', 'true');
  await expect(balance.getByRole('row', { name: /^2025/ })).toContainText('1,200.0');

  await page.unroute('**/api/trade_balance');
  await page.route('**/api/trade_balance', (route) => route.fulfill({ status: 502, json: { status: 'upstream_unavailable' } }));
  await page.reload();
  await expect(page.getByTestId('trade-balance')).toHaveAttribute('data-live', 'false');
  await expect(page.getByTestId('trade-balance').getByRole('row', { name: /^2025/ })).toContainText('+209.4');
});

test('shows the trade desk in the dark theme chosen on the site', async ({ page }) => {
  await page.addInitScript(() => localStorage.setItem('theme', 'dark'));
  await page.goto('/trade');
  await expect(page.locator('html')).toHaveAttribute('data-theme', 'dark');
  await expect(page.locator('body')).toHaveCSS('background-color', 'rgb(11, 27, 38)');
});

test('fits a phone screen without sideways scrolling', async ({ page }) => {
  await page.setViewportSize({ width: 375, height: 812 });
  for (const route of ['/', '/learn', '/changes', '/trade-context', '/trade']) {
    await page.goto(route);
    expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth), `${route} scrolls sideways`).toBe(true);
  }
});
