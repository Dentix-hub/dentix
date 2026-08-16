import { test, expect } from '@playwright/test';
import { loginAs, logout, E2E_CREDENTIALS } from './helpers.js';

const BASE_URL = process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:5173';

const users = {
  admin: E2E_CREDENTIALS.admin,
  doctor: E2E_CREDENTIALS.doctor,
  nurse: E2E_CREDENTIALS.nurse,
};

test.describe('Authentication Flow', () => {
  test('AUTH-01: Successful Login with admin credentials', async ({ page }) => {
    await page.goto(`${BASE_URL}/login`);

    await expect(page.locator('input[type="text"]')).toBeVisible();
    await expect(page.locator('input[type="password"]')).toBeVisible();

    await page.locator('input[type="text"]').fill(users.admin.username);
    await page.locator('input[type="password"]').fill(users.admin.password);
    await page.locator('button[type="submit"]').click();

    await page.waitForURL(`${BASE_URL}/`, { timeout: 15000 });
    await expect(page.locator('nav')).toBeVisible();
  });

  test('AUTH-02: Failed Login with incorrect password', async ({ page }) => {
    await page.goto(`${BASE_URL}/login`);

    await page.locator('input[type="text"]').fill(users.admin.username);
    await page.locator('input[type="password"]').fill('wrongpassword');
    await page.locator('button[type="submit"]').click();

    const errorMsg = page.locator('text=/خطأ|Error|Invalid|Unauthorized|غير صحيحة/i');
    await expect(errorMsg).toBeVisible({ timeout: 10000 });
    await expect(page).toHaveURL(/login/);
  });

  test('AUTH-03: Failed Login with non-existent user', async ({ page }) => {
    await page.goto(`${BASE_URL}/login`);

    await page.locator('input[type="text"]').fill('nonexistent_user_12345');
    await page.locator('input[type="password"]').fill('NotAReal!Password2026');
    await page.locator('button[type="submit"]').click();

    const errorMsg = page.locator('text=/خطأ|Error|Invalid|Not Found|غير صحيحة/i');
    await expect(errorMsg).toBeVisible({ timeout: 10000 });
  });

  test('AUTH-04: Logout and redirect to login', async ({ page }) => {
    await loginAs(page, users.admin.username, users.admin.password);
    await logout(page);
    await page.waitForURL(/\/login|\/$/, { timeout: 15000 });
    await expect(page.locator('button[type="submit"]')).toBeVisible();
  });

  test('AUTH-05: Unauthenticated access is denied', async ({ page }) => {
    await page.goto(`${BASE_URL}/dashboard`);
    await expect(page).toHaveURL(/\/login|\/$/, { timeout: 15000 });
    await expect(page.locator('button[type="submit"]')).toBeVisible();
  });

  test('AUTH-06: Authenticated cookie session survives reload', async ({ page }) => {
    await loginAs(page, users.admin.username, users.admin.password);

    const cookies = await page.context().cookies();
    expect(cookies.some((cookie) => cookie.name === 'access_token')).toBeTruthy();

    await page.reload();
    await page.waitForURL(`${BASE_URL}/`, { timeout: 15000 });
    await expect(page.locator('nav')).toBeVisible({ timeout: 10000 });
  });
});
