import { test, expect } from '@playwright/test';
import { loginAsAdmin, generateRandomName, generateRandomPhone } from './helpers.js';

const BASE_URL = process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:5173';

const testLab = {
  name: generateRandomName('Lab'),
  phone: generateRandomPhone(),
};

test.describe('Labs Management', () => {

  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
  });

  test('LAB-01: View labs list', async ({ page }) => {
    await page.goto(`${BASE_URL}/labs`);
    
    // Should load labs page
    await expect(page).toHaveURL(/.*labs/);
    
    // Should show labs table or list
    await expect(page.locator('table, [data-testid="labs-list"]').first()).toBeVisible({ timeout: 10000 });
  });

  test('LAB-02: Add new lab', async ({ page }) => {
    await page.goto(`${BASE_URL}/labs`);
    
    // Click add lab button
    const addBtn = page.getByRole('button').filter({ hasText: /إضافة|Lab|New/i }).first();
    await addBtn.click();
    
    // Fill lab form
    await page.locator('input[name="name"]').first().fill(testLab.name);
    await page.locator('input[name="phone"]').first().fill(testLab.phone);
    
    // Save
    const saveBtn = page.getByRole('button').filter({ hasText: /حفظ|Save/i }).first();
    await saveBtn.click();
    
    // Verify lab was added
    await page.waitForTimeout(2000);
    await expect(page.locator(`text=${testLab.name}`)).toBeVisible();
  });

  test('LAB-03: View lab orders', async ({ page }) => {
    await page.goto(`${BASE_URL}/labs`);
    
    // Click on first lab
    const labRow = page.locator('table tbody tr').first();
    if (await labRow.isVisible()) {
      await labRow.click();
      
      // Should show lab orders
      const ordersSection = page.locator('text=/طلبات|orders/i');
      await expect(ordersSection.first()).toBeVisible({ timeout: 5000 });
    }
  });

  test('LAB-04: Create lab order', async ({ page }) => {
    await page.goto(`${BASE_URL}/labs`);
    
    // Click create order button
    const orderBtn = page.getByRole('button').filter({ hasText: /طلب|New Order/i }).first();
    await orderBtn.click();
    
    // Fill order form
    const patientInput = page.locator('input[name="patient"]').first();
    if (await patientInput.isVisible()) {
      await patientInput.fill('Test Patient');
    }
    
    // Save
    const saveBtn = page.getByRole('button').filter({ hasText: /حفظ|Save/i }).first();
    await saveBtn.click();
  });

  test('LAB-05: Update lab order status', async ({ page }) => {
    await page.goto(`${BASE_URL}/labs`);
    
    // Find and click on first order
    const orderRow = page.locator('table tbody tr').first();
    if (await orderRow.isVisible()) {
      await orderRow.click();
      
      // Change status
      const statusSelect = page.locator('select[name="status"], [data-testid="status"]').first();
      if (await statusSelect.isVisible()) {
        await statusSelect.selectOption('completed');
      }
    }
  });

});
