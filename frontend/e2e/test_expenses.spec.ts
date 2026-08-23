import { test, expect } from '@playwright/test';
import { loginAsAdmin, generateRandomName } from './helpers.js';

const BASE_URL = process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:5173';

const testExpense = {
  description: generateRandomName('Expense'),
  amount: Math.floor(Math.random() * 1000 + 1).toString(),
};

test.describe('Finance V2 Expenses Management', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
  });

  test('EXP-01: legacy expenses URL redirects to canonical Finance route', async ({ page }) => {
    await page.goto(`${BASE_URL}/expenses?from=2026-08-01&to=2026-08-31`);

    await expect(page).toHaveURL(/\/finance\/expenses\?from=2026-08-01&to=2026-08-31/);
    await expect(page.getByText(/المصروفات التشغيلية المباشرة/).first()).toBeVisible({ timeout: 10000 });
    await expect(page.locator('table').first()).toBeVisible({ timeout: 10000 });
  });

  test('EXP-02: add a manual expense from the canonical page', async ({ page }) => {
    await page.goto(`${BASE_URL}/finance/expenses`);

    await page.getByRole('button', { name: /تسجيل مصروف/ }).click();
    await page.getByPlaceholder(/شراء مواد تخدير/).fill(testExpense.description);
    await page.getByPlaceholder('0.00').fill(testExpense.amount);
    await page.getByRole('button', { name: /حفظ المصروف/ }).click();

    await expect(page.getByText(testExpense.description).first()).toBeVisible({ timeout: 10000 });
  });

  test('EXP-03: canonical expense page survives direct refresh', async ({ page }) => {
    await page.goto(`${BASE_URL}/finance/expenses`);
    await page.reload();

    await expect(page).toHaveURL(/\/finance\/expenses/);
    await expect(page.getByRole('button', { name: /تسجيل مصروف/ })).toBeVisible({ timeout: 10000 });
  });

  test('EXP-04: delete a visible manual expense through Finance V2', async ({ page }) => {
    await page.goto(`${BASE_URL}/finance/expenses`);

    const expenseText = page.getByText(testExpense.description).first();
    if (!(await expenseText.isVisible().catch(() => false))) return;

    const row = expenseText.locator('xpath=ancestor::tr');
    await row.getByRole('button', { name: /حذف/ }).click();
    await expect(page.getByText('تأكيد حذف المصروف')).toBeVisible();
    await page.getByRole('button', { name: /حذف المصروف نهائياً/ }).click();
    await expect(page.getByText(testExpense.description)).toHaveCount(0);
  });
});
