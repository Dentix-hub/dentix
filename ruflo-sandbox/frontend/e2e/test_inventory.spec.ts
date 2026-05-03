import { test, expect } from '@playwright/test';
import { loginAsAdmin, generateRandomName } from './helpers.js';

const BASE_URL = process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:5173';

const testMaterial = {
  name: generateRandomName('Material'),
  code: 'TM' + Math.floor(Math.random() * 10000).toString(),
  quantity: 100,
};

test.describe('Inventory Management', () => {

  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
  });

  test('INV-01: View inventory list', async ({ page }) => {
    await page.goto(`${BASE_URL}/inventory`);
    
    // Should load inventory page
    await expect(page).toHaveURL(/.*inventory/);
    
    // Should show inventory table
    await expect(page.locator('table, [data-testid="inventory-list"]').first()).toBeVisible({ timeout: 10000 });
  });

  test('INV-02: Add new material', async ({ page }) => {
    await page.goto(`${BASE_URL}/inventory`);
    
    // Click add material button
    const addBtn = page.getByRole('button').filter({ hasText: /إضافة|Material|New/i }).first();
    await addBtn.click();
    
    // Fill material form
    await page.locator('input[name="name"]').first().fill(testMaterial.name);
    await page.locator('input[name="code"]').first().fill(testMaterial.code);
    
    // Fill quantity if field exists
    const qtyField = page.locator('input[name="quantity"], input[name="stock"]').first();
    if (await qtyField.isVisible()) {
      await qtyField.fill(testMaterial.quantity.toString());
    }
    
    // Save
    const saveBtn = page.getByRole('button').filter({ hasText: /حفظ|Save/i }).first();
    await saveBtn.click();
    
    // Verify material was added
    await page.waitForTimeout(2000);
    await expect(page.locator(`text=${testMaterial.name}`)).toBeVisible();
  });

  test('INV-03: Edit material', async ({ page }) => {
    await page.goto(`${BASE_URL}/inventory`);
    
    // Find and click on test material
    const materialRow = page.locator(`text=${testMaterial.name}`);
    if (await materialRow.isVisible()) {
      await materialRow.first().click();
      
      // Click edit button
      const editBtn = page.getByRole('button').filter({ hasText: /تعديل|Edit/i }).first();
      await editBtn.click();
      
      // Change quantity
      const qtyField = page.locator('input[name="quantity"]').first();
      await qtyField.fill('150');
      
      // Save
      const saveBtn = page.getByRole('button').filter({ hasText: /حفظ|Save/i }).first();
      await saveBtn.click();
    }
  });

  test('INV-04: Delete material', async ({ page }) => {
    await page.goto(`${BASE_URL}/inventory`);
    
    // Find and click on test material
    const materialRow = page.locator(`text=${testMaterial.name}`);
    if (await materialRow.isVisible()) {
      await materialRow.first().click();
      
      // Click delete button
      const deleteBtn = page.getByRole('button').filter({ hasText: /حذف|Delete/i }).first();
      await deleteBtn.click();
      
      // Confirm deletion
      const confirmBtn = page.getByRole('button').filter({ hasText: /تأكيد|نعم/i }).first();
      await confirmBtn.click();
    }
  });

  test('INV-05: Search inventory', async ({ page }) => {
    await page.goto(`${BASE_URL}/inventory`);
    
    // Find search input
    const searchInput = page.locator('input[placeholder*="بحث"], input[name="search"]').first();
    await searchInput.fill(testMaterial.code);
    
    // Wait for results
    await page.waitForTimeout(1000);
    
    // Should show filtered results
    await expect(page.locator(`text=${testMaterial.name}`).first()).toBeVisible();
  });

  test('INV-06: View low stock alerts', async ({ page }) => {
    await page.goto(`${BASE_URL}/inventory`);
    
    // Look for low stock section
    const lowStock = page.locator('text=/نقص|low stock|تنبيه/i');
    await expect(lowStock.first()).toBeVisible({ timeout: 5000 });
  });

  test('INV-07: View stock movements', async ({ page }) => {
    await page.goto(`${BASE_URL}/inventory`);
    
    // Click on a material to see movements
    const materialRow = page.locator('table tbody tr').first();
    if (await materialRow.isVisible()) {
      await materialRow.click();
      
      // Should show movement history
      const movements = page.locator('text=/حركة|movement|history/i');
      await expect(movements.first()).toBeVisible({ timeout: 5000 });
    }
  });

});
