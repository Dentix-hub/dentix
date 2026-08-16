/**
 * Test Helpers - Utility functions for E2E tests
 */

const BASE_URL = process.env.PLAYWRIGHT_BASE_URL || 'http://localhost:5173';

export const E2E_CREDENTIALS = {
  admin: { username: 'e2e_admin', password: 'Dentix-E2E_Admin!2026_X9' },
  doctor: { username: 'doctor1', password: 'Dentix-E2E_Doctor!2026_X9' },
  nurse: { username: 'nurse1', password: 'Dentix-E2E_Nurse!2026_X9' },
  receptionist: { username: 'reception1', password: 'Dentix-E2E_Reception!2026_X9' },
  accountant: { username: 'account1', password: 'Dentix-E2E_Account!2026_X9' },
};

export async function loginAs(page, username, password) {
  await page.goto(`${BASE_URL}/login`);
  await page.locator('input[type="text"]').fill(username);
  await page.locator('input[type="password"]').fill(password);
  await page.locator('button[type="submit"]').click();
  await page.waitForURL(`${BASE_URL}/`, { timeout: 15000 });
}

export async function loginAsAdmin(page) {
  return loginAs(page, E2E_CREDENTIALS.admin.username, E2E_CREDENTIALS.admin.password);
}

export async function loginAsDoctor(page) {
  return loginAs(page, E2E_CREDENTIALS.doctor.username, E2E_CREDENTIALS.doctor.password);
}

export async function loginAsNurse(page) {
  return loginAs(page, E2E_CREDENTIALS.nurse.username, E2E_CREDENTIALS.nurse.password);
}

export async function loginAsReceptionist(page) {
  return loginAs(
    page,
    E2E_CREDENTIALS.receptionist.username,
    E2E_CREDENTIALS.receptionist.password,
  );
}

export async function loginAsAccountant(page) {
  return loginAs(
    page,
    E2E_CREDENTIALS.accountant.username,
    E2E_CREDENTIALS.accountant.password,
  );
}

export async function logout(page) {
  const logoutBtn = page.getByRole('button').filter({ hasText: /خروج|Logout|تسجيل الخروج/i }).first();
  if (await logoutBtn.isVisible({ timeout: 3000 }).catch(() => false)) {
    await logoutBtn.click();
  } else {
    await page.locator('[data-testid="user-menu"], header button').first().click();
    await logoutBtn.click();
  }
  await page.waitForURL(`${BASE_URL}/login`);
}

export function generateRandomName(prefix = 'Test') {
  return `${prefix}_${Date.now()}_${Math.random().toString(36).substring(7)}`;
}

export function generateRandomPhone() {
  return '010' + Math.floor(Math.random() * 100000000).toString().padStart(8, '0');
}

export function generateRandomEmail() {
  return `test_${Date.now()}@example.com`;
}

export async function waitForPageLoad(page) {
  await page.waitForLoadState('networkidle');
  await page.waitForTimeout(500);
}

export async function navigateTo(page, route) {
  await page.goto(`${BASE_URL}${route}`);
  await waitForPageLoad(page);
}
