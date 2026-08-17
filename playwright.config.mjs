import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: !process.env.CI,
  forbidOnly: Boolean(process.env.CI),
  retries: process.env.CI ? 1 : 0,
  workers: process.env.CI ? 1 : undefined,
  expect: { timeout: 15_000 },
  reporter: process.env.CI
    ? [['github'], ['html', { open: 'never' }]]
    : [['list'], ['html', { open: 'never' }]],
  use: {
    baseURL: 'http://127.0.0.1:8000',
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  projects: [{ name: 'chromium', use: { ...devices['Desktop Chrome'] } }],
  webServer: {
    command: 'python -m uvicorn arancel_mx.api.app:app --host 127.0.0.1 --port 8000',
    url: 'http://127.0.0.1:8000/healthz',
    reuseExistingServer: !process.env.CI,
    timeout: 120_000,
    env: {
      ARANCEL_MX_API_DATASET: 'data-2026.08.15',
      ARANCEL_MX_API_CACHE_DIR: '/tmp/arancel-mx-playwright-cache',
    },
  },
});
