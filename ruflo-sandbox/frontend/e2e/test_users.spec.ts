import { test, expect } from '@playwright/test';
import { loginAsAdmin, generateRandomName } from './helpers.js';

const BASE_URL = process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:5173';

const testUser = {
  username: generateRandomName('user'),
  password: 'TestPass123!',
};

test.describe('Users Management', () => {

  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
  });

  test('USER-01: View users list', async ({ page }) => {
    await page.goto(`${BASE_URL}/users`);
    
    // Should load users page
    await expect(page).toHaveURL(/.*users/);
    
    // Should show users table
    await expect(page.locator('table, [data-testid="users-list"]').first()).toBeVisible({ timeout: 10000 });
  });

  test('USER-02: Add new user', async ({ page }) => {
    await page.goto(`${BASE_URL}/users`);
    
    // Click add user button
    const addBtn = page.getByRole('button').filter({ hasText: /إضافة|User|New/i }).first();
    await addBtn.click();
    
    // Fill user form
    await page.locator('input[name="username"]').first().fill(testUser.username);
    await page.locator('input[name="password"]').first().fill(testUser.password);
    
    // Select role
    const roleSelect = page.locator('select[name="role"]').first();
    if (await roleSelect.isVisible()) {
      await roleSelect.selectOption('doctor');
    }
    
    // Save
    const saveBtn = page.getByRole('button').filter({ hasText: /حفظ|Save/i }).first();
    await saveBtn.click();
    
    // Verify user was added
    await page.waitForTimeout(2000);
    await expect(page.locator(`text=${testUser.username}`)).toBeVisible();
  });

  test('USER-03: Edit user', async ({ page }) => {
    await page.goto(`${BASE_URL}/users`);
    
    // Find and click on test user
    const userRow = page.locator(`text=${testUser.username}`);
    if (await userRow.isVisible()) {
      await userRow.first().click();
      
      // Click edit button
      const editBtn = page.getByRole('button').filter({ hasText: /تعديل|Edit/i }).first();
      await editBtn.click();
      
      // Change role
      const roleSelect = page.locator('select[name="role"]').first();
      if (await roleSelect.isVisible()) {
        await roleSelect.selectOption('nurse');
      }
      
      // Save
      const saveBtn = page.getByRole('button').filter({ hasText: /حفظ|Save/i }).first();
      await saveBtn.click();
    }
  });

  test('USER-04: Deactivate user', async ({ page }) => {
    await page.goto(`${BASE_URL}/users`);
    
    // Find and click on test user
    const userRow = page.locator(`text=${testUser.username}`);
    if (await userRow.isVisible()) {
      await userRow.first().click();
      
      // Click deactivate button
      const deactivateBtn = page.getByRole('button').filter({ hasText: /تعطيل|Deactivate|Disable/i }).first();
      if (await deactivateBtn.isVisible()) {
        await deactivateBtn.click();
        
        // Confirm
        const confirmBtn = page.getByRole('button').filter({ hasText: /تأكيد|نعم/i }).first();
        await confirmBtn.click();
      }
    }
  });

});
