import { readFile } from 'node:fs/promises';

import { expect, test } from '@playwright/test';

test('serves the public marketing root and preserves the explorer handoff', async ({ page }) => {
  await page.goto('/');
  await expect(page.getByRole('heading', { name: /inteligencia arancelaria/i })).toBeVisible();
  await expect(page.getByText(/Apache-2\.0/i).first()).toBeVisible();
  await expect(page.getByRole('button', { name: /abrir explorador/i })).toBeVisible();
});

test('serves the canonical favicon and renders one lockup in the public header', async ({ page }) => {
  await page.goto('/');
  await expect(page.locator('link[rel="icon"][href="/favicon.svg"]')).toHaveCount(1);
  await expect(page.locator('header .brand-lockup img')).toHaveCount(1);
  const favicon = await page.request.get('/favicon.svg');
  expect(favicon.ok()).toBe(true);
  expect(favicon.headers()['content-type']).toContain('image/svg+xml');
});

test('defaults the public hero to Spanish and keeps English as an explicit option', async ({ page }) => {
  await page.goto('/');
  const language = page.getByLabel(/idioma de la interfaz/i);
  await expect(language).toHaveValue('es');
  await language.selectOption('en');
  await expect(page.getByRole('heading', { name: /tariff intelligence/i })).toBeVisible();
  await expect(page.getByRole('button', { name: /open explorer/i })).toBeVisible();
});

test('keeps Spanish document semantics on routes that are not yet localized', async ({ page }) => {
  await page.goto('/');
  await page.getByLabel(/idioma de la interfaz/i).selectOption('en');
  await page.goto('/chapters');
  await expect(page.locator('html')).toHaveAttribute('lang', 'es-MX');
});

test('keeps English document semantics on the verified-record compatibility alias', async ({ page }) => {
  await page.goto('/');
  await page.getByLabel(/idioma de la interfaz/i).selectOption('en');
  await page.goto('/app/chapter/85');
  await expect(page.locator('html')).toHaveAttribute('lang', 'en');
});

test('keeps suggestions dismissed when Escape is pressed during their debounce', async ({ page }) => {
  await page.goto('/app');
  const query = page.getByTestId('search-input');
  await query.fill('85');
  await query.press('Escape');
  await page.waitForTimeout(250);
  await expect(page.getByTestId('live-suggestions')).toHaveCount(0);
});

test('keeps the mobile header controls inside a 320 pixel viewport', async ({ page }) => {
  await page.setViewportSize({ width: 320, height: 720 });
  await page.goto('/');
  expect(await page.evaluate(() => document.documentElement.scrollWidth <= window.innerWidth)).toBe(true);
  await expect(page.getByRole('button', { name: /abrir menú de navegación/i })).toBeVisible();
});

test('keeps evidence cards controllable and backed by a loaded topical visual', async ({ page }) => {
  await page.goto('/');
  const evidence = page.getByTestId('example-rotator');
  await expect(evidence.getByRole('button', { name: /pausar fichas/i })).toHaveAttribute('aria-pressed', 'false');
  await evidence.getByRole('button', { name: /pausar fichas/i }).click();
  await expect(evidence.getByRole('button', { name: /continuar fichas/i })).toHaveAttribute('aria-pressed', 'true');
  expect(await evidence.locator('.evidence-card__image').evaluate((image) => image.complete && image.naturalWidth > 0)).toBe(true);
});

test('uses the public metadata release in the evidence card when it is available', async ({ page }) => {
  await page.route('**/v1/meta', (route) => route.fulfill({ json: { dataset_version: '2026.08.24' } }));
  await page.goto('/');
  await expect(page.getByTestId('example-rotator')).toContainText('2026.08.24');
});

test('does not rotate evidence cards when reduced motion is requested', async ({ page }) => {
  await page.emulateMedia({ reducedMotion: 'reduce' });
  await page.goto('/');
  const evidence = page.getByTestId('example-rotator');
  const initial = await evidence.locator('.evidence-card__record strong').textContent();
  await page.waitForTimeout(5800);
  await expect(evidence.locator('.evidence-card__record strong')).toHaveText(initial || '');
});

test('keeps the global navigation state and skip link accessible', async ({ page }) => {
  await page.goto('/');
  const skipLink = page.getByRole('link', { name: /saltar al contenido/i });
  await expect(skipLink).toHaveCSS('width', '1px');
  await expect(skipLink).toHaveCSS('height', '1px');
  await page.keyboard.press('Tab');
  await expect(skipLink).toBeFocused();
  await expect(skipLink).toBeVisible();
  await expect(skipLink).toHaveAttribute('href', '#main-content');

  await page.setViewportSize({ width: 390, height: 844 });
  await page.reload();
  const toggle = page.getByRole('button', { name: /abrir menú de navegación/i });
  await toggle.click();
  await expect(page.getByRole('button', { name: /cerrar menú de navegación/i })).toBeFocused();
  await page.keyboard.press('Escape');
  await expect(page.getByRole('button', { name: /abrir menú de navegación/i })).toBeFocused();
});

test('keeps all established public destinations visible in desktop navigation', async ({ page }) => {
  await page.goto('/');
  const navigation = page.getByLabel('Navegación principal');
  await expect(navigation.getByRole('link', { name: /^explorar$/i })).toBeVisible();
  await expect(navigation.getByRole('link', { name: /^contexto comercial$/i })).toHaveAttribute('href', '/trade-context');
  await expect(navigation.getByRole('link', { name: /^mis registros$/i })).toBeVisible();
  await navigation.getByRole('link', { name: /^mis registros$/i }).click();
  await expect(page).toHaveURL(/\/records$/);
});

test('rotates verified examples and lets the visitor choose a concrete path', async ({ page }) => {
  await page.goto('/');
  const examples = page.getByTestId('example-rotator');
  await expect(examples).toContainText(/85/);
  await examples.getByRole('button', { name: /mostrar 01\.01\.21\.01\.00/i }).click();
  await expect(examples).toContainText(/01\.01\.21\.01\.00/);
  await examples.getByRole('button', { name: /inspeccionar ficha/i }).click();
  await expect(page).toHaveURL(/\/app\?q=01.01.21.01.00/);
});

test('updates editorial metadata when the route changes', async ({ page }) => {
  await page.goto('/documentation');
  await expect(page).toHaveTitle(/start with the contract, then write the integration/i);
  await expect(page.locator('meta[name="description"]')).toHaveAttribute('content', /guías técnicas/i);
  await page.goto('/trust');
  await expect(page).toHaveTitle(/when evidence is incomplete, the release stops/i);
  await expect(page.locator('meta[name="description"]')).toHaveAttribute('content', /modelo de confianza/i);
});

test('recovers from an unknown route with a clear Explorer destination', async ({ page }) => {
  await page.goto('/');
  await page.evaluate(() => {
    window.history.pushState({}, '', '/ruta-inexistente');
    window.dispatchEvent(new PopStateEvent('popstate'));
  });
  await expect(page.getByRole('heading', { name: /page not found/i })).toBeVisible();
  await expect(page.getByRole('link', { name: /open explorer/i })).toHaveAttribute('href', '/app');
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

test('shows a bounded history of immutable data releases', async ({ page }) => {
  await page.route('**/v1/repository', (route) => route.fulfill({
    contentType: 'application/json',
    body: JSON.stringify({
      releases: [
        {
          tag: 'data-2026.08.22',
          publishedAt: '2026-08-22T11:17:00Z',
          url: 'https://github.com/jccontrerasg08-cpu/arancel-mx/releases/tag/data-2026.08.22',
        },
      ],
    }),
  }));
  await page.goto('/changes');

  await expect(page.getByRole('heading', { name: /verified release history/i })).toBeVisible();
  await expect(page.getByRole('link', { name: /data-2026\.08\.22/i })).toHaveAttribute(
    'href',
    'https://github.com/jccontrerasg08-cpu/arancel-mx/releases/tag/data-2026.08.22',
  );
});


test('identifies the chapter fallback when verified indexes are unavailable', async ({ page }) => {
  await page.route('**/v1/sections', (route) => route.fulfill({ status: 503, contentType: 'application/json', body: '{}' }));
  await page.route('**/v1/chapters', (route) => route.fulfill({ status: 503, contentType: 'application/json', body: '{}' }));
  await page.goto('/chapters');
  await expect(page.getByRole('status')).toContainText(/index unavailable.*packaged navigation/i);
  await expect(page.getByRole('button', { name: /^sección I /i })).toBeVisible();
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

test('opens matching chapter paths while a person filters the visual tree', async ({ page }) => {
  await page.goto('/chapters');
  await page.getByRole('searchbox', { name: /buscar capítulo/i }).fill('01');
  await expect(page.getByRole('status')).toContainText(/matching chapters expanded/i);
  await expect(page.getByRole('button', { name: /capítulo 01/i })).toBeVisible();
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
  await expect(page.getByRole('heading', { name: /explora una referencia arancelaria/i })).toBeVisible();
  await expect(page.getByTestId('search-input')).toBeVisible();
  await expect(page.getByTestId('example-fraction')).toContainText(/IGI/i);
  await expect(page.getByRole('link', { name: /explorar árbol visual/i })).toHaveAttribute('href', '/chapters');
});

test('shows possible verified paths while a person types without requiring a submit', async ({ page }) => {
  await page.route('**/v1/search?**', async (route) => {
    const query = new URL(route.request().url()).searchParams.get('q');
    if (query !== 'teléfonos') return route.continue();
    return route.fulfill({ contentType: 'application/json', body: JSON.stringify([{ code: '85171301', description: 'Teléfonos inteligentes', level: 'fraccion8', dataset_version: '2026.08.15' }]) });
  });
  await page.goto('/app');
  await page.getByTestId('search-input').fill('teléfonos');
  const suggestions = page.getByTestId('live-suggestions');
  await expect(suggestions).toContainText(/rutas verificadas posibles/i);
  await expect(suggestions.getByRole('option', { name: /85\.17\.13\.01/i })).toBeVisible();
  await suggestions.getByRole('option', { name: /85\.17\.13\.01/i }).click();
  await expect(page).toHaveURL(/\/app\/record\/85171301$/);
});

test('looks up a complete tariff fraction with evidence and a decision tree', async ({ page }) => {
  await page.goto('/app');
  await page.getByTestId('search-input').fill('8517.13.01');
  await page.getByTestId('search-submit').click();
  const card = page.getByTestId('result-card').first();
  await expect(card).toContainText('85.17.13.01');
  await expect(card).toContainText(/teléfonos inteligentes/i);
  await expect(page.getByTestId('hierarchy-card')).toContainText(/árbol de decisión progresivo/i);
  await expect(page.getByTestId('tree-filter-status')).toContainText('85.17.13.01');
  await expect(page.getByRole('status')).toHaveText(/registro verificado listo/i);
  await expect(page.getByRole('link', { name: /API JSON/i })).toHaveAttribute('href', /\/v1\/ficha\/85171301$/);
});

test('retries a direct record request without leaving the record route', async ({ page }) => {
  let attempts = 0;
  await page.route('**/v1/ficha/99999999', async (route) => {
    attempts += 1;
    await route.fulfill({ status: 503, contentType: 'application/json', body: '{}' });
  });
  await page.goto('/app/record/99999999');
  await expect(page.getByRole('heading', { name: /no está disponible temporalmente/i })).toBeVisible();
  await page.getByRole('button', { name: /reintentar/i }).click();
  await expect.poll(() => attempts).toBeGreaterThan(1);
  await expect(page).toHaveURL(/\/app\/record\/99999999$/);
});

test('exposes rates only on fraction cards', async ({ page }) => {
  await page.goto('/app/record/01012101');
  const fractionCard = page.getByTestId('result-card');
  await expect(fractionCard).toContainText('01.01.21.01');
  await expect(fractionCard).toContainText('IGI');
  await expect(fractionCard).toContainText('IGE');
  await expect(fractionCard.getByTestId('open-estimate')).toHaveAttribute('href', '/trade?code=01012101');

  await page.goto('/app/record/0101210100');
  const nicoCard = page.getByTestId('result-card');
  await expect(nicoCard).toContainText('01.01.21.01.00');
  await expect(nicoCard).not.toContainText('IGI');
  await expect(nicoCard).not.toContainText('IGE');
  await expect(nicoCard.getByTestId('open-estimate')).toHaveAttribute('href', '/trade?code=0101210100');

  await page.goto('/app/record/01');
  await expect(page.getByTestId('result-card').getByTestId('open-estimate')).toHaveCount(0);
  await expect(page.getByTestId('estimate-guidance')).toContainText(/fracción de 8 dígitos o un NICO de 10 dígitos/i);
  await expect(page.getByTestId('estimate-guidance').getByRole('link', { name: /buscar una fracción compatible/i })).toHaveAttribute('href', '/app?q=01');
});

test('renders every non-fraction direct record without rate fields or a page error', async ({ page }) => {
  await page.route('**/v1/ficha/0101210100', async (route) => {
    await route.fulfill({
      contentType: 'application/json',
      body: JSON.stringify({
        record: {
          code: '0101210100',
          level: 'nico10',
          description: 'Reproductores de raza pura.',
          unit_name: 'Cbza',
          igi: null,
          ige: null,
          parent_code: '01012101',
          dataset_version: '2026.08.15',
          schema_version: '2',
          effective_from: null,
          effective_to: null,
          is_current: true,
          hierarchy: {
            hs2: '01', hs4: '0101', hs6: '010121', fraccion8: '01012101', nico2: '00', nico10: '0101210100',
          },
          ligie_version: 'LIGIE-2022',
          validity_basis: 'observed_snapshot',
        },
        formatted_code: '0101.21.01 00',
        section: { roman: 'I', name: 'Animales vivos y productos del reino animal' },
        hierarchy: [],
        children: [],
      }),
    });
  });

  for (const { code, formatted } of [
    { code: '01', formatted: '01' },
    { code: '0101', formatted: '01.01' },
    { code: '010121', formatted: '01.01.21' },
    { code: '0101210100', formatted: '01.01.21.01.00' },
  ]) {
    await page.goto(`/app/record/${code}`);
    await expect(page.getByText(/an unexpected error occurred/i)).toHaveCount(0);
    const card = page.getByTestId('result-card');
    await expect(card).toContainText(formatted);
    await expect(card).not.toContainText('IGI');
    await expect(card).not.toContainText('IGE');
  }
});


test('narrows the visible decision-tree path from an entered fraction prefix', async ({ page }) => {
  await page.goto('/app/record/85171301');
  await expect(page.getByTestId('hierarchy-card')).toBeVisible();
  await expect(page.getByRole('searchbox', { name: /filtrar esta jerarquía por un código padre/i })).toBeVisible();
  await page.getByTestId('search-input').fill('8517');
  await expect(page.getByTestId('tree-filter-status')).toContainText('85.17');
  await expect(page.getByRole('button', { name: /apply filter/i })).toHaveCount(0);
  await expect(page.getByTestId('hierarchy-card')).toContainText(/capítulo HS2/i);
});

test('searches verified descriptions from input and quick action', async ({ page }) => {
  await page.goto('/app');
  await page.getByTestId('search-input').fill('teléfonos');
  await page.getByTestId('search-submit').click();
  await expect(page.getByTestId('result-card').first()).toContainText(/teléfonos/i);
  await expect(page.getByRole('status')).toContainText(/resultados verificados encontrados/i);
  await page.goto('/app');
  await page.getByRole('button', { name: /probar teléfonos/i }).click();
  await expect(page).toHaveURL(/\/app\?q=tel%C3%A9fonos$/);
  await expect(page.getByTestId('search-input')).toHaveValue('teléfonos');
  await expect(page.getByTestId('result-card').first()).toContainText(/teléfonos/i);
});

test('explains when a query is required without changing the workspace', async ({ page }) => {
  await page.goto('/app');
  await page.getByTestId('search-submit').click();
  await expect(page.getByRole('status')).toContainText(/ingresa un código arancelario/i);
  await expect(page.getByRole('heading', { name: /ingresa un código completo o una descripción/i })).toBeVisible();
});

test('opens shared and durable explorer URLs', async ({ page }) => {
  await page.goto('/app?q=85171301');
  await expect(page.getByTestId('search-input')).toHaveValue('85171301');
  await expect(page.getByTestId('result-card')).toContainText(/teléfonos inteligentes/i);
  await page.goto('/app/record/85171301');
  await expect(page.getByTestId('result-card')).toContainText(/teléfonos inteligentes/i);
  await expect(page.getByRole('heading', { name: /contexto de release, no asesoría/i })).toBeVisible();
  await page.goto('/app/chapter/85');
  await expect(page.getByTestId('result-card')).toContainText('85');
  await expect(page.getByRole('status')).toHaveText(/registro verificado listo/i);
});

test('opens the visual tree from the explorer and keeps its selected hierarchy inspectable', async ({ page }) => {
  await page.goto('/app');
  await page.getByRole('link', { name: /explorar árbol visual/i }).click();
  await expect(page).toHaveURL(/\/chapters$/);
  await expect(page.getByRole('button', { name: /^sección I /i })).toBeVisible();
  await page.goto('/app/record/85171301');
  await expect(page.getByTestId('hierarchy-card')).toContainText('85.17.13.01');
});

test('saves and exports a browser-local research snapshot', async ({ page }) => {
  await page.goto('/app/record/85171301');
  await page.getByRole('button', { name: /guardar localmente/i }).click();
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
  await expect(page.getByRole('button', { name: /guardar localmente/i })).toBeVisible();
  await expect(page.getByRole('status')).toHaveAttribute('aria-live', 'polite');
  await expect(page.getByTestId('snapshot-list')).toHaveAttribute('aria-live', 'polite');
  await page.getByTestId('search-input').focus();
  await expect(page.getByTestId('search-input')).toBeFocused();
  await expect(page.getByRole('button', { name: /apply filter/i })).toHaveCount(0);
});
