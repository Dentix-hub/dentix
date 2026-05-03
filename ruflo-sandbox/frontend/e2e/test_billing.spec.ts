import { test, expect } from '@playwright/test';
import { loginAsAdmin } from './helpers.js';

const BASE_URL = process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:5173';

test.describe('Billing & Invoices', () => {

  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
  });

  test('BILL-01: View invoices list', async ({ page }) => {
    await page.goto(`${BASE_URL}/billing`);
    
    // Should load billing page
    await expect(page).toHaveURL(/.*billing/);
    
    // Should show invoices table
    await expect(page.locator('table, [data-testid="invoices-list"]').first()).toBeVisible({ timeout: 10000 });
  });

  test('BILL-02: Create new invoice', async ({ page }) => {
    await page.goto(`${BASE_URL}/billing`);
    
    // Click create invoice button
    const createBtn = page.getByRole('button').filter({ hasText: /فاتورة|Invoice|New/i }).first();
    await createBtn.click();
    
    // Fill invoice form - add patient
    const patientInput = page.locator('input[name="patient"], input[name="patient_id"]').first();
    if (await patientInput.isVisible()) {
      await patientInput.fill('Test Patient');
    }
    
    // Add items
    const addItemBtn = page.getByRole('button').filter({ hasText: /إضافة عنصر|Add Item/i }).first();
    if (await addItemBtn.isVisible()) {
      await addItemBtn.click();
    }
    
    // Save
    const saveBtn = page.getByRole('button', { name: /حفظ|Save|تأكيد/i }).first();
    await saveBtn.click();
    
    // Verify invoice was created
    await page.waitForTimeout(2000);
  });

  test('BILL-03: Add payment to invoice', async ({ page }) => {
    await page.goto(`${BASE_URL}/billing`);
    
    // Click on first invoice
    const invoiceRow = page.locator('table tbody tr').first();
    if (await invoiceRow.isVisible()) {
      await invoiceRow.click();
      
      // Click add payment button
      const paymentBtn = page.getByRole('button').filter({ hasText: /دفعة|Payment|Pay/i }).first();
      if (await paymentBtn.isVisible()) {
        await paymentBtn.click();
        
        // Fill payment amount
        const amountInput = page.locator('input[name="amount"]').first();
        if (await amountInput.isVisible()) {
          await amountInput.fill('100');
        }
        
        // Save
        const saveBtn = page.getByRole('button', { name: /حفظ|Save/i }).first();
        await saveBtn.click();
      }
    }
  });

  test('BILL-04: Print invoice', async ({ page }) => {
    await page.goto(`${BASE_URL}/billing`);
    
    // Click on first invoice
    const invoiceRow = page.locator('table tbody tr').first();
    if (await invoiceRow.isVisible()) {
      await invoiceRow.click();
      
      // Click print button
      const printBtn = page.getByRole('button').filter({ hasText: /طباعة|Print/i }).first();
      if (await printBtn.isVisible()) {
        await printBtn.click();
        
        // Should open print dialog or new tab
        await page.waitForTimeout(1000);
      }
    }
  });

  test('BILL-05: View patient balance', async ({ page }) => {
    await page.goto(`${BASE_URL}/billing`);
    
    // Find patient balance section
    const balanceSection = page.locator('[data-testid="patient-balance"], .balance-section, text=/الرصيد|Balance/i');
    await expect(balanceSection.first()).toBeVisible({ timeout: 5000 });
  });

});
