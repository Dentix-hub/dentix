import { test, expect } from '@playwright/test';
import { loginAs, loginAsAdmin } from './helpers.js';

const BASE_URL = process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:5173';

const users = {
  admin: { username: 'admin', password: 'admin123' },
  doctor: { username: 'doctor1', password: 'doc123' },
  nurse: { username: 'nurse1', password: 'nurse123' },
  receptionist: { username: 'reception1', password: 'rec123' },
  accountant: { username: 'account1', password: 'acc123' },
};

test.describe('RBAC - Role Based Access Control', () => {

  test('RBAC-01: Doctor cannot access billing', async ({ page }) => {
    await login(page, users.doctor);
    
    // Try to access billing
    await page.goto(`${BASE_URL}/billing`);
    await page.waitForTimeout(2000);
    
    // Should either redirect or show 403
    const url = page.url();
    if (url.includes('billing')) {
      // Check for access denied message
      const deniedMsg = page.locator('text=/403|Access Denied|لا تملك|nauthorized/i');
      const hasAccessDenied = await deniedMsg.isVisible().catch(() => false);
      if (!hasAccessDenied) {
        // Check if content is hidden
        const billingTable = page.locator('table, [data-testid="billing"]');
        await expect(billingTable.first()).not.toBeVisible({ timeout: 3000 });
      }
    }
  });

  test('RBAC-02: Nurse cannot create patients', async ({ page }) => {
    await login(page, users.nurse);
    
    // Navigate to patients
    await page.goto(`${BASE_URL}/patients`);
    await page.waitForTimeout(1000);
    
    // Try to add patient
    const addBtn = page.getByRole('button').filter({ hasText: /إضافة|New Patient/i }).first();
    const isVisible = await addBtn.isVisible().catch(() => false);
    
    if (isVisible) {
      await addBtn.click();
      
      // Fill form
      await page.locator('input[name="name"]').fill('Test Patient');
      
      // Save and check response
      const saveBtn = page.getByRole('button').filter({ hasText: /حفظ|Save/i }).first();
      await saveBtn.click();
      await page.waitForTimeout(2000);
      
      // Should show error or not create
      const errorMsg = page.locator('text=/403|لا تملك|Permission/i');
      await expect(errorMsg.first()).toBeVisible({ timeout: 3000 });
    }
  });

  test('RBAC-03: Receptionist can view patients', async ({ page }) => {
    await login(page, users.receptionist);
    
    // Navigate to patients
    await page.goto(`${BASE_URL}/patients`);
    
    // Should be able to view
    await expect(page).toHaveURL(/.*patients/);
    await expect(page.locator('table, [data-testid="patients-list"]').first()).toBeVisible({ timeout: 10000 });
  });

  test('RBAC-04: Accountant can view billing', async ({ page }) => {
    await login(page, users.accountant);
    
    // Navigate to billing
    await page.goto(`${BASE_URL}/billing`);
    
    // Should be able to view billing
    await expect(page).toHaveURL(/.*billing/);
    await expect(page.locator('table, [data-testid="billing"]').first()).toBeVisible({ timeout: 10000 });
  });

  test('RBAC-05: Doctor cannot access settings', async ({ page }) => {
    await login(page, users.doctor);
    
    // Try to access settings
    await page.goto(`${BASE_URL}/settings`);
    await page.waitForTimeout(2000);
    
    // Should either redirect or show 403
    const url = page.url();
    if (url.includes('settings')) {
      const deniedMsg = page.locator('text=/403|Access Denied/i');
      const hasAccessDenied = await deniedMsg.isVisible().catch(() => false);
      if (!hasAccessDenied) {
        const content = page.locator('main, .settings-content');
        await expect(content.first()).not.toBeVisible({ timeout: 3000 });
      }
    }
  });

  test('RBAC-06: Receptionist can access appointments', async ({ page }) => {
    await login(page, users.receptionist);
    
    // Navigate to appointments
    await page.goto(`${BASE_URL}/appointments`);
    
    // Should be able to view
    await expect(page).toHaveURL(/.*appointments/);
  });

  test('RBAC-07: Manager can view analytics', async ({ page }) => {
    await login(page, users.admin);
    
    // Navigate to dashboard/analytics
    await page.goto(`${BASE_URL}/`);
    
    // Should be able to view dashboard
    await expect(page.locator('nav, [data-testid="dashboard"]').first()).toBeVisible({ timeout: 10000 });
  });

  test('RBAC-08: Admin has full access', async ({ page }) => {
    await login(page, users.admin);
    
    // Test all protected routes
    const routes = ['/patients', '/appointments', '/billing', '/settings', '/inventory'];
    
    for (const route of routes) {
      await page.goto(`${BASE_URL}${route}`);
      await page.waitForTimeout(1000);
      
      // Should not see access denied
      const deniedMsg = page.locator('text=/403|Access Denied|لا تملك/i');
      const hasAccessDenied = await deniedMsg.isVisible().catch(() => false);
      expect(hasAccessDenied).toBe(false);
    }
  });

});
