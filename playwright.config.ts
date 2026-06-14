import { defineConfig, devices } from '@playwright/test';

export default defineConfig({
  testDir: './tests/e2e',
  fullyParallel: false, // Django dev server is single-threaded
  reporter: 'list',
  use: {
    baseURL: 'http://localhost:8000',
    trace: 'on-first-retry',
  },
  projects: [
    {
      name: 'chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
  webServer: {
    command: 'uv run python manage.py runserver',
    url: 'http://localhost:8000/health/',
    reuseExistingServer: !process.env.CI,
    env: {
      SECRET_KEY: process.env.SECRET_KEY ?? 'django-insecure-e2e-only-not-for-production',
      DEBUG: 'True',
      ALLOWED_HOSTS: 'localhost,127.0.0.1',
    },
  },
});
