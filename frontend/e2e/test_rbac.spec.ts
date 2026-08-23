import { test, expect } from '@playwright/test';
import { loginAs, E2E_CREDENTIALS } from './helpers.js';

const BASE_URL = process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:5173';
const users = E2E_CREDENTIALS;

async function loginAsRole(page, role) {
  const credentials = users[role];
  await loginAs(page, credentials.username, credentials.password);
}

async function expectAdminRouteDenied(page, route) {
  await page.goto(`${BASE_URL}${route}`);
  await page.waitForURL(/\/unauthorized/, { timeout: 10000 });
  await expect(page).toHaveURL(/\/unauthorized/);
}

test.describe('RBAC - Role Based Access Control', () => {
  test('RBAC-01: Doctor legacy billing link reaches Finance but does not expose overview data', async ({ page }) => {
    await loginAsRole(page, 'doctor');
    await page.goto(`${BASE_URL}/billing`);
    await expect(page).toHaveURL(/\/finance\/overview/);
    await expect(page.getByText(/غير مصرح بالوصول إلى هذا القسم|not authorized/i)).toBeVisible({ timeout: 10000 });
  });

  test('RBAC-02: Doctor cannot access admin settings', async ({ page }) => {
    await loginAsRole(page, 'doctor');
    await expectAdminRouteDenied(page, '/settings');
  });

  test('RBAC-03: Accountant legacy billing link redirects to authorized Finance overview', async ({ page }) => {
    await loginAsRole(page, 'accountant');
    await page.goto(`${BASE_URL}/billing`);
    await expect(page).toHaveURL(/\/finance\/overview/);
    await expect(page).not.toHaveURL(/\/unauthorized/);
  });

  test('RBAC-04: Receptionist can access patients', async ({ page }) => {
    await loginAsRole(page, 'receptionist');
    await page.goto(`${BASE_URL}/patients`);
    await expect(page).toHaveURL(/.*patients/);
    await expect(page.locator('h1').first()).toBeVisible({ timeout: 10000 });
  });

  test('RBAC-05: Receptionist can access appointments', async ({ page }) => {
    await loginAsRole(page, 'receptionist');
    await page.goto(`${BASE_URL}/appointments`);
    await expect(page).toHaveURL(/.*appointments/);
    await expect(page.locator('h1').first()).toBeVisible({ timeout: 10000 });
  });

  test('RBAC-06: Admin legacy finance links resolve to canonical protected routes', async ({ page }) => {
    await loginAsRole(page, 'admin');

    const routes = [
      ['/billing', /\/finance\/overview/],
      ['/expenses', /\/finance\/expenses/],
      ['/labs', /\/labs/],
      ['/analytics', /\/analytics/],
      ['/users', /\/users/],
      ['/settings', /\/settings/],
    ];

    for (const [route, expectedUrl] of routes) {
      await page.goto(`${BASE_URL}${route}`);
      await expect(page).toHaveURL(expectedUrl);
      await expect(page).not.toHaveURL(/\/unauthorized/);
    }
  });

  test('RBAC-07: Non-super-admin cannot enter super-admin console', async ({ page }) => {
    await loginAsRole(page, 'admin');
    await page.goto(`${BASE_URL}/admin`);
    await page.waitForURL(/\/unauthorized/, { timeout: 10000 });
    await expect(page).toHaveURL(/\/unauthorized/);
  });
});
