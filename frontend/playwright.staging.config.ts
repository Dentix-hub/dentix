import { defineConfig, devices } from '@playwright/test';

const baseURL = process.env.STAGING_BASE_URL;
if (!baseURL) {
  throw new Error('STAGING_BASE_URL is required for staging deployment smoke tests');
}

export default defineConfig({
  testDir: './e2e',
  testMatch: /staging-deployment-smoke\.spec\.ts/,
  timeout: 90_000,
  expect: { timeout: 15_000 },
  fullyParallel: false,
  forbidOnly: true,
  retries: 0,
  workers: 1,
  reporter: 'github',
  use: {
    baseURL,
    trace: 'retain-on-failure',
    screenshot: 'only-on-failure',
    video: 'retain-on-failure',
  },
  projects: [
    {
      name: 'staging-chromium',
      use: { ...devices['Desktop Chrome'] },
    },
  ],
});
