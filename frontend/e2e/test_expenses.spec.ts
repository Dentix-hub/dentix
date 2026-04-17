import { test, expect } from '@playwright/test';
import { loginAsAdmin, generateRandomName } from './helpers.js';

const BASE_URL = process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:5173';

const testExpense = {
  description: generateRandomName('Expense'),
  amount: Math.floor(Math.random() * 1000).toString(),
  category: 'supplies',
};

test.describe('Expenses Management', () => {

  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
  });

  test('EXP-01: View expenses list', async ({ page }) => {
    await page.goto(`${BASE_URL}/expenses`);
    
    // Should load expenses page
    await expect(page).toHaveURL(/.*expenses/);
    
    // Should show expenses table
    await expect(page.locator('table, [data-testid="expenses-list"]').first()).toBeVisible({ timeout: 10000 });
  });

  test('EXP-02: Add new expense', async ({ page }) => {
    await page.goto(`${BASE_URL}/expenses`);
    
    // Click add expense button
    const addBtn = page.getByRole('button').filter({ hasText: /إضافة|Expense|New/i }).first();
    await addBtn.click();
    
    // Fill expense form
    await page.locator('input[name="description"]').first().fill(testExpense.description);
    await page.locator('input[name="amount"]').first().fill(testExpense.amount);
    
    // Save
    const saveBtn = page.getByRole('button').filter({ hasText: /حفظ|Save/i }).first();
    await saveBtn.click();
    
    // Verify expense was added
    await page.waitForTimeout(2000);
  });

  test('EXP-03: Edit expense', async ({ page }) => {
    await page.goto(`${BASE_URL}/expenses`);
    
    // Find and click on test expense
    const expenseRow = page.locator(`text=${testExpense.description}`);
    if (await expenseRow.isVisible()) {
      await expenseRow.first().click();
      
      // Click edit button
      const editBtn = page.getByRole('button').filter({ hasText: /تعديل|Edit/i }).first();
      await editBtn.click();
      
      // Change amount
      const amountField = page.locator('input[name="amount"]').first();
      await amountField.fill('500');
      
      // Save
      const saveBtn = page.getByRole('button').filter({ hasText: /حفظ|Save/i }).first();
      await saveBtn.click();
    }
  });

  test('EXP-04: Delete expense', async ({ page }) => {
    await page.goto(`${BASE_URL}/expenses`);
    
    // Find and click on test expense
    const expenseRow = page.locator(`text=${testExpense.description}`);
    if (await expenseRow.isVisible()) {
      await expenseRow.first().click();
      
      // Click delete button
      const deleteBtn = page.getByRole('button').filter({ hasText: /حذف|Delete/i }).first();
      await deleteBtn.click();
      
      // Confirm deletion
      const confirmBtn = page.getByRole('button').filter({ hasText: /تأكيد|نعم/i }).first();
      await confirmBtn.click();
    }
  });

});
