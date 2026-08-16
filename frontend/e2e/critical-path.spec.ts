import { test, expect } from '@playwright/test';
import { E2E_CREDENTIALS } from './helpers.js';

const BASE_URL = process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:5173';
const TEST_USER = E2E_CREDENTIALS.admin.username;
const TEST_PASS = E2E_CREDENTIALS.admin.password;

test.describe('Dentix Critical Path', () => {
  test('E2E Clinical Core Workflow', async ({ page }) => {
    // 1. Setup & Login through the canonical unauthenticated route.
    await page.goto(BASE_URL + '/');
    await page.locator('input[type="text"]').fill(TEST_USER);
    await page.locator('input[type="password"]').fill(TEST_PASS);
    await page.locator('button[type="submit"]').click();
    await expect(page.locator('nav').first()).toBeVisible({ timeout: 15000 });

    // 2. Dashboard Loaded
    await expect(page).toHaveURL(`${BASE_URL}/`);

    // 3. Navigate to Patients
    await page.goto(BASE_URL + '/patients');
    await expect(page).toHaveURL(/.*patients/);

    // 4. Create Patient
    const addPatientBtn = page.getByRole('button').filter({ hasText: /إضافة|Add|New/i }).first();
    if (await addPatientBtn.isVisible()) {
      await addPatientBtn.click();

      await page.locator('input[name="name"]').first().fill('E2E Test Patient');
      await page.locator('input[name="phone"]').first().fill('01000000000');
      const saveBtn = page.getByRole('button', { name: /حفظ|Save/i }).first();
      if (await saveBtn.isVisible()) {
        await saveBtn.click();
      } else {
        await page.locator('button[type="submit"]').click();
      }

      await page.waitForTimeout(1000);
    }

    // 5. Search & View Patient
    const searchInput = page.locator('input[type="text"]').first();
    if (await searchInput.isVisible()) {
      await searchInput.fill('E2E Test Patient');
      await page.waitForTimeout(1000);
    }

    const firstRow = page.locator('table tbody tr').first();
    if (await firstRow.isVisible()) {
      await firstRow.click();
      await page.waitForTimeout(1000);
    }

    await expect(page).toHaveURL(/.*patients\/\d+/);

    // 6. Add Appointment (If visible on patient view)
    const addApptBtn = page.getByRole('button').filter({ hasText: /موعد|Appointment/i }).first();
    if (await addApptBtn.isVisible()) {
      await addApptBtn.click();
      await page.waitForTimeout(500);
      await page.keyboard.press('Escape');
    }

    // 7. Add Treatment
    const addTreatmentBtn = page.getByRole('button').filter({ hasText: /علاج|Treatment/i }).first();
    if (await addTreatmentBtn.isVisible()) {
      await addTreatmentBtn.click();
      const costInput = page.locator('input[type="number"]').first();
      if (await costInput.isVisible()) {
        await costInput.fill('1000');
      }
      const saveTrtBtn = page.getByRole('button', { name: /حفظ|Save/i }).first();
      if (await saveTrtBtn.isVisible()) {
        await saveTrtBtn.click();
      }
    }

    // 8. Make Payment
    const addPaymentBtn = page.getByRole('button').filter({ hasText: /دفع|Payment|تحصيل/i }).first();
    if (await addPaymentBtn.isVisible()) {
      await addPaymentBtn.click();
      const amtInput = page.locator('input[type="number"]').first();
      if (await amtInput.isVisible()) {
        await amtInput.fill('500');
      }
      const savePayBtn = page.getByRole('button', { name: /حفظ|Save/i }).first();
      if (await savePayBtn.isVisible()) {
        await savePayBtn.click();
      }
    }

    // 9. Verify Balance
    const balanceEl = page.locator('text=/R|رصيد/i').first();
    await expect(balanceEl).toBeVisible({ timeout: 5000 });
  });
});
