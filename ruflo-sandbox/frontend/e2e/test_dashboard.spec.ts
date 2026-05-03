import { test, expect } from '@playwright/test';
import { loginAsAdmin } from './helpers.js';

const BASE_URL = process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:5173';

test.describe('Dashboard', () => {

  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
  });

  test('DASH-01: View main statistics', async ({ page }) => {
    await page.goto(`${BASE_URL}/`);
    
    // Should show dashboard with stats
    await expect(page.locator('nav').first()).toBeVisible({ timeout: 10000 });
    
    // Should show some statistics cards
    const statsCards = page.locator('.stat-card, [data-testid="stat"], .stats-grid');
    await expect(statsCards.first()).toBeVisible({ timeout: 5000 });
  });

  test('DASH-02: View today appointments', async ({ page }) => {
    await page.goto(`${BASE_URL}/`);
    
    // Should show today's appointments section
    const todayAppts = page.locator('text=/اليوم|today|مواعيد اليوم/i');
    await expect(todayAppts.first()).toBeVisible({ timeout: 5000 });
  });

  test('DASH-03: View recent patients', async ({ page }) => {
    await page.goto(`${BASE_URL}/`);
    
    // Should show recent patients section
    const recentPatients = page.locator('text=/المرضى|patients|الأخيرة/i');
    await expect(recentPatients.first()).toBeVisible({ timeout: 5000 });
  });

  test('DASH-04: View notifications', async ({ page }) => {
    await page.goto(`${BASE_URL}/`);
    
    // Should show notifications bell or section
    const notifBtn = page.locator('[data-testid="notifications"], .notifications, button:has-text("الإشعارات")');
    await expect(notifBtn.first()).toBeVisible({ timeout: 5000 });
  });

});
