import { test, expect } from '@playwright/test';
import { loginAs, loginAsAdmin, logout } from './helpers.js';

const BASE_URL = process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:5173';
const API_URL = process.env.VITE_API_URL || 'http://localhost:8000/api/v1';

const users = {
  admin: { username: 'admin', password: 'admin123' },
  doctor: { username: 'doctor1', password: 'doc123' },
  nurse: { username: 'nurse1', password: 'nurse123' },
};

test.describe('Authentication Flow', () => {

  test('AUTH-01: Successful Login with admin credentials', async ({ page }) => {
    await page.goto(`${BASE_URL}/login`);
    
    // Check for login page elements
    await expect(page.locator('input[type="text"]')).toBeVisible();
    await expect(page.locator('input[type="password"]')).toBeVisible();
    
    // Fill credentials
    await page.locator('input[type="text"]').fill(users.admin.username);
    await page.locator('input[type="password"]').fill(users.admin.password);
    await page.locator('button[type="submit"]').click();
    
    // Verify redirection to dashboard
    await page.waitForURL(`${BASE_URL}/`, { timeout: 15000 });
    await expect(page.locator('nav')).toBeVisible();
  });

  test('AUTH-02: Failed Login with incorrect password', async ({ page }) => {
    await page.goto(`${BASE_URL}/login`);
    
    await page.locator('input[type="text"]').fill(users.admin.username);
    await page.locator('input[type="password"]').fill('wrongpassword');
    await page.locator('button[type="submit"]').click();
    
    // Expect error message
    const errorMsg = page.locator('text=/خطأ|Error|Invalid|Unauthorized/i');
    await expect(errorMsg).toBeVisible({ timeout: 10000 });
    
    // Should still be on login page
    await expect(page).toHaveURL(/login/);
  });

  test('AUTH-03: Failed Login with non-existent user', async ({ page }) => {
    await page.goto(`${BASE_URL}/login`);
    
    await page.locator('input[type="text"]').fill('nonexistent_user_12345');
    await page.locator('input[type="password"]').fill('anypassword');
    await page.locator('button[type="submit"]').click();
    
    // Expect error message
    const errorMsg = page.locator('text=/خطأ|Error|Invalid|Not Found/i');
    await expect(errorMsg).toBeVisible({ timeout: 10000 });
  });

  test('AUTH-04: Logout and redirect to login', async ({ page }) => {
    // Login first
    await loginAs(page, users.admin.username, users.admin.password);
    
    // Click logout
    await logout(page);
    
    // Verify redirect back to login
    await page.waitForURL(`${BASE_URL}/login`);
    await expect(page.locator('button[type="submit"]')).toBeVisible();
  });

  test('AUTH-05: Unauthenticated access redirects to login', async ({ page }) => {
    // Try to access protected route without login
    await page.goto(`${BASE_URL}/dashboard`);
    
    // Should redirect to login
    await expect(page).toHaveURL(/login/);
  });

  test('AUTH-06: Remember me functionality', async ({ page }) => {
    await page.goto(`${BASE_URL}/login`);
    
    // Check remember me checkbox
    const rememberMe = page.locator('input[type="checkbox"]');
    if (await rememberMe.isVisible()) {
      await rememberMe.check();
    }
    
    await page.locator('input[type="text"]').fill(users.admin.username);
    await page.locator('input[type="password"]').fill(users.admin.password);
    await page.locator('button[type="submit"]').click();
    
    // Verify token is stored in localStorage (not sessionStorage)
    await page.waitForURL(`${BASE_URL}/`);
    const token = await page.evaluate(() => localStorage.getItem('token'));
    expect(token).toBeTruthy();
  });

});
