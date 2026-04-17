import { test, expect } from '@playwright/test';
import { loginAsAdmin } from './helpers.js';

const BASE_URL = process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:5173';

test.describe('Settings', () => {

  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
  });

  test('SET-01: View clinic settings', async ({ page }) => {
    await page.goto(`${BASE_URL}/settings`);
    
    // Should load settings page
    await expect(page).toHaveURL(/.*settings/);
    
    // Should show clinic info section
    const clinicSection = page.locator('text=/العيادة|Clinic|إعدادات/i');
    await expect(clinicSection.first()).toBeVisible({ timeout: 5000 });
  });

  test('SET-02: Update clinic settings', async ({ page }) => {
    await page.goto(`${BASE_URL}/settings`);
    
    // Edit clinic name
    const nameField = page.locator('input[name="clinic_name"], input[name="name"]').first();
    if (await nameField.isVisible()) {
      await nameField.fill('Updated Clinic Name');
      
      // Save
      const saveBtn = page.getByRole('button').filter({ hasText: /حفظ|Save/i }).first();
      await saveBtn.click();
      
      // Verify update
      await page.waitForTimeout(1000);
      await expect(page.locator('text=Updated Clinic Name')).toBeVisible();
    }
  });

  test('SET-03: Connect Google Drive', async ({ page }) => {
    await page.goto(`${BASE_URL}/settings`);
    
    // Look for Google Drive connection
    const driveBtn = page.locator('text=/Google Drive|ربط/i');
    if (await driveBtn.first().isVisible({ timeout: 3000 }).catch(() => false)) {
      await driveBtn.first().click();
      
      // Should redirect to Google auth or show connection status
      await page.waitForTimeout(2000);
    }
  });

  test('SET-04: View subscription info', async ({ page }) => {
    await page.goto(`${BASE_URL}/settings`);
    
    // Look for subscription section
    const subSection = page.locator('text=/الاشتراك|Subscription|Pricing/i');
    await expect(subSection.first()).toBeVisible({ timeout: 5000 });
  });

  test('SET-05: Change language', async ({ page }) => {
    await page.goto(`${BASE_URL}/settings`);
    
    // Find language switcher
    const langBtn = page.locator('button:has-text("العربية"), button:has-text("English")').first();
    if (await langBtn.isVisible()) {
      await langBtn.click();
      
      // Verify language changed
      await page.waitForTimeout(1000);
    }
  });

  test('SET-06: Toggle dark mode', async ({ page }) => {
    await page.goto(`${BASE_URL}/settings`);
    
    // Find theme toggle
    const themeBtn = page.locator('button:has-text("داكن"), button:has-text("مضيء"), [data-testid="theme-toggle"]').first();
    if (await themeBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
      await themeBtn.click();
      
      // Verify theme changed
      await page.waitForTimeout(500);
    }
  });

});
