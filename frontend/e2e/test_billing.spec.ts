import { test, expect } from '@playwright/test';
import { loginAsAdmin } from './helpers.js';

const BASE_URL = process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:5173';

const tabPatterns = {
  doctors: /الأطباء|اطباء|Doctors/i,
  staff: /الموظفين|الموظفون|Staff/i,
  expenses: /المصروفات|المصاريف|Expenses/i,
  summary: /الملخص|Summary/i,
  payments: /الدفعات|المدفوعات|Payments/i,
};

async function openBilling(page) {
  await page.goto(`${BASE_URL}/billing`);
  await expect(page).toHaveURL(/.*billing/);
  await expect(page.locator('h1').first()).toBeVisible({ timeout: 15000 });
}

test.describe('Billing & Finance', () => {
  test.beforeEach(async ({ page }) => {
    await loginAsAdmin(page);
  });

  test('BILL-01: Finance workspace loads with its primary sections', async ({ page }) => {
    await openBilling(page);

    await expect(page.getByRole('button', { name: tabPatterns.doctors }).first()).toBeVisible();
    await expect(page.getByRole('button', { name: tabPatterns.staff }).first()).toBeVisible();
    await expect(page.getByRole('button', { name: tabPatterns.expenses }).first()).toBeVisible();
    await expect(page.getByRole('button', { name: tabPatterns.summary }).first()).toBeVisible();
    await expect(page.getByRole('button', { name: tabPatterns.payments }).first()).toBeVisible();
  });

  test('BILL-02: Admin can add a manual expense', async ({ page }) => {
    await openBilling(page);

    await page.getByRole('button', { name: tabPatterns.expenses }).first().click();

    const addExpense = page
      .getByRole('button')
      .filter({ hasText: /إضافة.*مصروف|مصروف.*جديد|Add.*Expense/i })
      .first();
    await expect(addExpense).toBeVisible({ timeout: 10000 });
    await addExpense.click();

    const itemInput = page.getByLabel(/البند|Item/i).first();
    const costInput = page.getByLabel(/التكلفة|Cost/i).first();
    await expect(itemInput).toBeVisible();
    await expect(costInput).toBeVisible();

    const expenseName = `E2E Expense ${Date.now()}`;
    await itemInput.fill(expenseName);
    await costInput.fill('125');

    await page.getByRole('button', { name: /حفظ|Save/i }).last().click();
    await expect(page.getByText(expenseName)).toBeVisible({ timeout: 15000 });
  });

  test('BILL-03: Payments section is reachable without page errors', async ({ page }) => {
    await openBilling(page);

    await page.getByRole('button', { name: tabPatterns.payments }).first().click();
    await expect(page.locator('body')).not.toContainText(/Application Error|Something went wrong/i);

    const tableOrEmptyState = page.locator('table, [class*="empty"], [class*="Empty"]').first();
    await expect(tableOrEmptyState).toBeVisible({ timeout: 10000 });
  });

  test('BILL-04: Summary section exposes date filtering', async ({ page }) => {
    await openBilling(page);

    await page.getByRole('button', { name: tabPatterns.summary }).first().click();
    const dateInputs = page.locator('input[type="date"]');
    await expect(dateInputs.first()).toBeVisible({ timeout: 10000 });
    expect(await dateInputs.count()).toBeGreaterThanOrEqual(2);
  });

  test('BILL-05: Payroll/salaries view is reachable from expenses', async ({ page }) => {
    await openBilling(page);

    await page.getByRole('button', { name: tabPatterns.expenses }).first().click();
    const salariesTab = page
      .getByRole('button')
      .filter({ hasText: /الرواتب|المرتبات|Salaries|Payroll/i })
      .first();
    await expect(salariesTab).toBeVisible({ timeout: 10000 });
    await salariesTab.click();

    const monthInput = page.locator('input[type="month"]');
    await expect(monthInput.first()).toBeVisible({ timeout: 10000 });
  });
});
