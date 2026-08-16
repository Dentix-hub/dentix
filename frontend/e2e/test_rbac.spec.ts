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
  test('RBAC-01: Doctor cannot access admin billing workspace', async ({ page }) => {
    await loginAsRole(page, 'doctor');
    await expectAdminRouteDenied(page, '/billing');
  });

  test('RBAC-02: Doctor cannot access admin settings', async ({ page }) => {
    await loginAsRole(page, 'doctor');
    await expectAdminRouteDenied(page, '/settings');
  });

  test('RBAC-03: Accountant is denied billing by the current frontend route guard', async ({ page }) => {
    await loginAsRole(page, 'accountant');
    await expectAdminRouteDenied(page, '/billing');
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

  test('RBAC-06: Admin can access all admin-protected clinic routes', async ({ page }) => {
    await loginAsRole(page, 'admin');

    const routes = ['/billing', '/expenses', '/labs', '/analytics', '/users', '/settings'];
    for (const route of routes) {
      await page.goto(`${BASE_URL}${route}`);
      await expect(page).toHaveURL(new RegExp(route.replace('/', '\\/')));
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
